"""
Duplicate-call suppression.

Real failure this fixes: an LLM emitted the same tool call twice in one
turn (an eager first pass, then a retry). Both calls launched a live
session on the same device — two overlapping audio streams, one user.

The fix is deliberately dumb: hash the function name + its arguments,
remember the last time that exact call happened, and skip the real work
if it happened again inside the window. The *caller* still gets a
return value (so the agent loop doesn't see an error) — it's just a
cached "already done" response instead of doing the side effect twice.
"""

from __future__ import annotations

import functools
import json
import time
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

_last_seen: dict[str, float] = {}


def _call_key(func: Callable, args: tuple, kwargs: dict) -> str:
    try:
        payload = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    except TypeError:
        payload = repr((args, kwargs))
    return f"{func.__module__}.{func.__qualname__}:{payload}"


def dedupe(window_seconds: float = 5.0, *, on_duplicate: Any = None) -> Callable[[F], F]:
    """Suppress a second call with identical args within ``window_seconds``.

    Args:
        window_seconds: how long an identical call is considered a duplicate.
        on_duplicate: value to return when a duplicate is caught. If it's
            callable, it's invoked with the same ``(*args, **kwargs)`` the
            original call received; otherwise it's returned as-is. Defaults
            to ``None``.

    Example:
        >>> @dedupe(window_seconds=5)
        ... def launch_session(device_id: str) -> str:
        ...     return f"launched {device_id}"
        >>> launch_session("phone-1")
        'launched phone-1'
        >>> launch_session("phone-1")  # within 5s: skipped, no second launch
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = _call_key(func, args, kwargs)
            now = time.monotonic()
            last = _last_seen.get(key)
            if last is not None and (now - last) < window_seconds:
                if callable(on_duplicate):
                    return on_duplicate(*args, **kwargs)
                return on_duplicate
            _last_seen[key] = now
            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
