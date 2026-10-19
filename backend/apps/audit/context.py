"""The user responsible for the current request, for audit attribution.

A ContextVar rather than thread-locals so an async view or middleware cannot
leak an actor between tasks.
"""

from contextvars import ContextVar, Token
from typing import Any

_current_user: ContextVar[Any] = ContextVar("audit_current_user", default=None)


def set_current_user(user: Any) -> Token:
    return _current_user.set(user)


def reset_current_user(token: Token) -> None:
    _current_user.reset(token)


def get_current_user():
    """The signed-in user for this request, or None for background work."""
    user = _current_user.get()
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    return user
