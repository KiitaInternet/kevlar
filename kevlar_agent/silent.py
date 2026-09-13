"""
Run a potentially-blocking call with a hard timeout, from any thread.

Real failure this fixes: an OAuth helper called ``run_local_server()``,
which opens a browser and blocks until a human clicks through it. Called
from an unattended background thread with an expired token, there was no
human anywhere near it — it hung for hours instead of failing fast.

Python has no cross-platform ``SIGALRM``-based way to time out an
arbitrary blocking call from *any* thread (signals only work on the main
thread on POSIX, and don't exist for this on Windows at all). So this
runs the call in a worker thread via a small pool and simply stops
waiting on it after ``timeout_seconds`` — the caller gets control back
either way, even though the worker thread technically keeps running in
the background if the underlying call truly can't be cancelled.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as _FutureTimeoutError
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class SilentTimeout(Exception):
    """Raised when a wrapped call doesn't return within its timeout."""

    def __init__(self, timeout_seconds: float):
        self.timeout_seconds = timeout_seconds
        super().__init__(f"call did not return within {timeout_seconds}s")


def silent(func: Callable[..., T], *args: Any, timeout_seconds: float = 15.0, **kwargs: Any) -> T:
    """Call ``func(*args, **kwargs)`` but never block past ``timeout_seconds``.

    Raises:
        SilentTimeout: if the call hasn't returned in time. Whatever
            ``func`` raised internally (if anything) is *not* what you see
            here — you see ``SilentTimeout``, meaning "we stopped waiting,"
            which is the signal a caller running unattended actually needs.

    Example:
        >>> def maybe_opens_a_browser():
        ...     ...  # some SDK call that can hang waiting on a human
        >>> try:
        ...     result = silent(maybe_opens_a_browser, timeout_seconds=10)
        ... except SilentTimeout:
        ...     result = None  # fail fast, log it, move on
    """
    # Deliberately NOT `with ThreadPoolExecutor(...) as pool:` — that context
    # manager calls shutdown(wait=True) on exit, which blocks until the worker
    # thread finishes on its own. If func is genuinely stuck, that defeats the
    # entire point: the caller would still wait the full duration of the hang,
    # just with an extra layer between them and it. shutdown(wait=False) lets
    # this function return the moment the timeout fires; the abandoned worker
    # thread keeps running in the background (Python cannot forcibly kill a
    # thread) but the caller is no longer blocked on it.
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        future = pool.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout_seconds)
        except _FutureTimeoutError:
            raise SilentTimeout(timeout_seconds) from None
    finally:
        pool.shutdown(wait=False)
