"""
Confirmation enforced as code, not as a prompt.

Real failure this fixes: a system prompt politely asked the model to
"confirm before doing anything irreversible." The model occasionally
skipped that step anyway — not maliciously, just a misread of intent.
A polite instruction is a suggestion; it is not a gate.

The fix: wrap the risky function itself. It refuses to run unless the
caller passes ``confirmed=True`` explicitly. There is no code path that
reaches the real side effect without that flag being true — the model
(or any caller) cannot talk its way past it.
"""

from __future__ import annotations

import functools
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


class ConfirmationRequired(Exception):
    """Raised when a guarded action is called without confirmed=True."""

    def __init__(self, summary: str):
        self.summary = summary
        super().__init__(f"confirmation required: {summary}")


def require_confirmation(summary: str | Callable[..., str]) -> Callable[[F], F]:
    """Refuse to run the wrapped function unless called with ``confirmed=True``.

    Args:
        summary: a human-readable description of what's about to happen, or a
            callable that builds one from the call's ``(*args, **kwargs)``.
            Surfaced on :class:`ConfirmationRequired` so the caller (e.g. an
            agent loop) can relay it back to a human and ask for real consent.

    The ``confirmed`` kwarg is consumed by this decorator and never forwarded
    to the wrapped function.

    Example:
        >>> @require_confirmation(lambda amount: f"transfer ${amount}")
        ... def transfer(amount: float, confirmed: bool = False) -> str:
        ...     return f"transferred ${amount}"
        >>> transfer(50)
        Traceback (most recent call last):
            ...
        kevlar_agent.confirm.ConfirmationRequired: confirmation required: transfer $50
        >>> transfer(50, confirmed=True)
        'transferred $50'
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            confirmed = kwargs.pop("confirmed", False)
            if not confirmed:
                text = summary(*args, **kwargs) if callable(summary) else summary
                raise ConfirmationRequired(text)
            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
