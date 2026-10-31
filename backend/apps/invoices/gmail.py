"""Email delivery for invoices: Gmail API with OAuth 2.0, with a dev fallback.

The Gmail path is the real sender. It uses an OAuth 2.0 refresh token (the
``gmail.send`` scope) and the Gmail API's ``users.messages.send`` endpoint, so no
SMTP password is stored and the mail is actually sent from the authorized Google
account. When Gmail is not configured and ``INVOICE_EMAIL_FALLBACK`` is enabled
(development and tests), the same message is sent through Django's configured
email backend instead.
"""

import base64
import logging
from email.message import EmailMessage
from typing import Iterable

from django.conf import settings
from django.core.mail import EmailMessage as DjangoEmailMessage

logger = logging.getLogger(__name__)

GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
GMAIL_SCOPES = [GMAIL_SEND_SCOPE]
GMAIL_TOKEN_URI = "https://oauth2.googleapis.com/token"

Attachment = tuple[str, bytes, str]


class EmailDeliveryError(Exception):
    """A user-facing failure to deliver an invoice email."""


def _setting(name: str, default: str = "") -> str:
    return str(getattr(settings, name, default) or "").strip()


def gmail_configured() -> bool:
    """Whether all OAuth 2.0 values needed to send through Gmail are present."""
    return all(
        _setting(name)
        for name in (
            "GMAIL_CLIENT_ID",
            "GMAIL_CLIENT_SECRET",
            "GMAIL_REFRESH_TOKEN",
            "GMAIL_SENDER_EMAIL",
        )
    )


def _sender() -> tuple[str, str]:
    """The From address and display name for a Gmail send."""
    email = _setting("GMAIL_SENDER_EMAIL")
    name = _setting("GMAIL_SENDER_NAME") or _setting("PAYROLL_COMPANY_NAME", "HRMS")
    return email, name


def _message(
    *,
    to: str,
    subject: str,
    body: str,
    from_email: str,
    from_name: str,
    attachments: Iterable[Attachment] | None = None,
) -> EmailMessage:
    message = EmailMessage()
    message["To"] = to
    message["From"] = f"{from_name} <{from_email}>" if from_name else from_email
    message["Subject"] = subject
    message.set_content(body)
    for filename, content, content_type in attachments or []:
        maintype, _, subtype = (content_type or "application/octet-stream").partition(
            "/"
        )
        message.add_attachment(
            content,
            maintype=maintype or "application",
            subtype=subtype or "octet-stream",
            filename=filename,
        )
    return message


def send_via_gmail(
    *,
    to: str,
    subject: str,
    body: str,
    attachments: Iterable[Attachment] | None = None,
) -> dict:
    """Send an email through the Gmail API using the stored refresh token."""
    # Imported lazily so development installs without the Google libraries can
    # still run the console-email fallback.
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise EmailDeliveryError(
            "Gmail libraries are not installed. Run pip install -r requirements.txt."
        ) from exc

    sender, sender_name = _sender()
    message = _message(
        to=to,
        subject=subject,
        body=body,
        from_email=sender,
        from_name=sender_name,
        attachments=attachments,
    )
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")

    credentials = Credentials(
        token=None,
        refresh_token=_setting("GMAIL_REFRESH_TOKEN"),
        token_uri=_setting("GMAIL_TOKEN_URI", GMAIL_TOKEN_URI) or GMAIL_TOKEN_URI,
        client_id=_setting("GMAIL_CLIENT_ID"),
        client_secret=_setting("GMAIL_CLIENT_SECRET"),
        scopes=GMAIL_SCOPES,
    )

    try:
        service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
        sent = (
            service.users()
            .messages()
            .send(userId="me", body={"raw": raw})
            .execute(num_retries=2)
        )
    except Exception as exc:  # noqa: BLE001 - Google raises several error types
        logger.warning("Gmail API send failed", exc_info=True)
        raise EmailDeliveryError(
            "Gmail could not send the email. Check the OAuth 2.0 credentials "
            "and that the account can send mail."
        ) from exc

    return {"provider": "gmail", "message_id": str(sent.get("id", ""))}


def deliver_email(
    *,
    to: str,
    subject: str,
    body: str,
    attachments: Iterable[Attachment] | None = None,
) -> dict:
    """Send an email through Gmail, or the fallback backend in development."""
    recipient = (to or "").strip()
    if not recipient:
        raise EmailDeliveryError("A recipient email address is required.")

    if gmail_configured():
        return send_via_gmail(
            to=recipient,
            subject=subject,
            body=body,
            attachments=attachments,
        )

    if not getattr(settings, "INVOICE_EMAIL_FALLBACK", False):
        raise EmailDeliveryError(
            "Email delivery is not configured. Set GMAIL_CLIENT_ID, "
            "GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN and GMAIL_SENDER_EMAIL, "
            "or enable INVOICE_EMAIL_FALLBACK for development."
        )

    sender = _setting("DEFAULT_FROM_EMAIL", "hrms@localhost")
    sender_name = _setting("GMAIL_SENDER_NAME") or _setting(
        "PAYROLL_COMPANY_NAME", "HRMS"
    )
    message = DjangoEmailMessage(
        subject=subject,
        body=body,
        from_email=f"{sender_name} <{sender}>" if sender_name else sender,
        to=[recipient],
    )
    for filename, content, content_type in attachments or []:
        message.attach(filename, content, content_type)

    try:
        message.send(fail_silently=False)
    except Exception as exc:  # noqa: BLE001 - surface a usable API error
        logger.warning("Fallback email send failed", exc_info=True)
        raise EmailDeliveryError(
            "The email could not be sent. Check the configured email backend."
        ) from exc
    return {"provider": "django", "message_id": ""}
