"""Obtain a Gmail OAuth 2.0 refresh token for server-side invoice sending.

This is a one-time setup command. It runs the OAuth 2.0 installed-app flow with
the ``gmail.send`` scope and prints the refresh token. Put that token (and the
OAuth client id/secret and sender address) in the backend environment; the app
never stores the token in the database.

Google Cloud setup:
  1. Create an OAuth 2.0 Client ID of type "Desktop app" (or a web client with
     http://localhost:8080/ as an allowed redirect URI).
  2. Enable the Gmail API for the project.
  3. Run this command and record the refresh token:
       python manage.py gmail_oauth_setup --client-id ... --client-secret ...
     or set GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET first.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.invoices.gmail import GMAIL_SCOPES


class Command(BaseCommand):
    help = "Run the Gmail OAuth 2.0 flow and print a refresh token."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--client-id", default="")
        parser.add_argument("--client-secret", default="")
        parser.add_argument("--port", type=int, default=8080)
        parser.add_argument(
            "--manual",
            action="store_true",
            help=(
                "Print the consent URL and paste the code back instead of "
                "opening a browser."
            ),
        )

    def handle(self, *args, **options) -> None:
        client_id = options["client_id"] or getattr(settings, "GMAIL_CLIENT_ID", "")
        client_secret = options["client_secret"] or getattr(
            settings, "GMAIL_CLIENT_SECRET", ""
        )
        if not client_id or not client_secret:
            raise CommandError(
                "Provide --client-id and --client-secret, or set GMAIL_CLIENT_ID "
                "and GMAIL_CLIENT_SECRET in the environment."
            )

        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise CommandError(
                "Install the Google libraries first: "
                "pip install -r requirements.txt"
            ) from exc

        port = options["port"]
        redirect_uri = f"http://localhost:{port}/"
        client_config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": getattr(
                    settings, "GMAIL_TOKEN_URI", "https://oauth2.googleapis.com/token"
                ),
                "redirect_uris": [redirect_uri],
            }
        }
        flow = InstalledAppFlow.from_client_config(client_config, scopes=GMAIL_SCOPES)
        flow.redirect_uri = redirect_uri

        self.stdout.write(
            "Opening the Google consent screen. Use the Google account that should "
            "send invoices."
        )
        try:
            if options["manual"]:
                auth_url, _state = flow.authorization_url(
                    access_type="offline",
                    prompt="consent",
                    include_granted_scopes="true",
                )
                self.stdout.write("")
                self.stdout.write("Open this URL and approve the gmail.send scope:")
                self.stdout.write(auth_url)
                self.stdout.write("")
                self.stdout.write(
                    "The browser will redirect to localhost and may show an error. "
                    "Copy the 'code' value from the redirected URL."
                )
                code = input("Authorization code: ").strip()
                if not code:
                    raise CommandError("No authorization code was entered.")
                flow.fetch_token(code=code)
                credentials = flow.credentials
            else:
                credentials = flow.run_local_server(
                    port=port,
                    access_type="offline",
                    prompt="consent",
                    include_granted_scopes="true",
                )
        except CommandError:
            raise
        except Exception as exc:  # noqa: BLE001 - the flow raises several errors
            raise CommandError(f"OAuth 2.0 setup failed: {exc}") from exc

        refresh_token = credentials.refresh_token
        if not refresh_token:
            raise CommandError(
                "Google did not return a refresh token. Revoke the app's access and "
                "run the command again; the flow must use access_type=offline and "
                "prompt=consent."
            )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Gmail OAuth 2.0 setup complete."))
        self.stdout.write("Add these to backend/.env (or the production environment):")
        self.stdout.write(f"GMAIL_CLIENT_ID={client_id}")
        self.stdout.write(f"GMAIL_CLIENT_SECRET={client_secret}")
        self.stdout.write(f"GMAIL_REFRESH_TOKEN={refresh_token}")
        self.stdout.write(
            "GMAIL_SENDER_EMAIL=<the Google account you just authorized>"
        )
        self.stdout.write("GMAIL_SENDER_NAME=<your company name>")
        self.stdout.write(
            "Keep INVOICE_EMAIL_FALLBACK=false in production; the Gmail API path "
            "will be used automatically."
        )
