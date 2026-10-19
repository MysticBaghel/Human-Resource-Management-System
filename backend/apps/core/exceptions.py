"""One error shape for the whole API: {"detail", "code", "fields"}."""

from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions
from rest_framework.views import exception_handler as drf_exception_handler

FALLBACK_CODE = "error"


def _flatten_first_message(detail: Any) -> str:
    """DRF error details nest lists/dicts; surface one readable sentence."""
    if isinstance(detail, dict):
        for key, value in detail.items():
            message = _flatten_first_message(value)
            if message:
                return message
        return ""
    if isinstance(detail, (list, tuple)):
        for item in detail:
            message = _flatten_first_message(item)
            if message:
                return message
        return ""
    return str(detail)


def api_exception_handler(exc, context):
    """Return every error as {"detail", "code", "fields"}."""
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()

    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    detail = getattr(exc, "detail", None)
    code = getattr(exc, "default_code", None) or FALLBACK_CODE

    fields: dict[str, Any] = {}
    if isinstance(exc, exceptions.ValidationError) and isinstance(detail, dict):
        for field, messages in detail.items():
            if isinstance(messages, (list, tuple)):
                fields[field] = [str(message) for message in messages]
            else:
                fields[field] = [str(messages)]

    message = _flatten_first_message(detail) or "Request failed."

    response.data = {"detail": message, "code": str(code), "fields": fields}
    return response
