"""
Self-supervising watchdog: restart what dies, from outside itself.

Real failure this fixes: a process that only knows how to restart *itself*
can't restart itself after it's actually dead. Reliability has to come
from something external and independent of the thing it's watching — the
watchdog must be simpler and more boring than every process it supervises,
so it's less likely to be the thing that breaks.

This is intentionally minimal: a name, a way to check if it's alive, and
a way to start it. No process groups, no supervision trees — for anything
past "a handful of long-running scripts on one machine," reach for a real
process manager (systemd, supervisord, pm2) instead.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from typing import Callable, Sequence

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None


@dataclass
class Watched:
    """One process to keep alive.

    Args:
        name: a label used in reports (and, by default, to spot it running).
        start: how to launch it — a full argv list, e.g. ["python", "bot.py"].
        is_alive: optional custom liveness check. Defaults to scanning
            running processes for one whose command line contains ``name``
            (requires the optional ``psutil`` dependency).
    """

    name: str
    start: Sequence[str]
    is_alive: Callable[[], bool] | None = None

    def check_alive(self) -> bool:
        if self.is_alive is not None:
            return self.is_alive()
        if psutil is None:
            raise RuntimeError(
                "no is_alive given and psutil isn't installed — "
                "install psutil or pass an explicit is_alive callable"
            )
        for proc in psutil.process_iter(["cmdline"]):
            try:
                cmdline = " ".join(proc.info["cmdline"] or [])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            if self.name in cmdline:
                return True
        return False


class Watchdog:
    """Check a list of :class:`Watched` processes and restart whichever died.

    Example:
        >>> wd = Watchdog([
        ...     Watched("telegram_bot.py", start=["python", "telegram_bot.py"]),
        ...     Watched("mobile_relay.py", start=["python", "mobile_relay.py"]),
        ... ])
        >>> restarted = wd.check_and_restart()
        >>> restarted
        []
    """

    def __init__(self, watched: Sequence[Watched]):
        self.watched = list(watched)

    def check_and_restart(self) -> list[str]:
        """Restart anything that isn't alive. Returns the names restarted."""
        restarted = []
        for item in self.watched:
            try:
                if not item.check_alive():
                    subprocess.Popen(list(item.start))
                    restarted.append(item.name)
            except Exception as e:
                restarted.append(f"{item.name} (restart attempt failed: {e})")
        return restarted

    def run_forever(self, interval_seconds: float = 300.0, on_restart: Callable[[list[str]], None] | None = None) -> None:
        """Loop :meth:`check_and_restart` every ``interval_seconds``, forever.

        ``on_restart`` is called with the list of restarted names whenever
        that list is non-empty — wire it to a notification channel to hear
        about restarts as they happen, instead of finding out later.
        """
        while True:
            restarted = self.check_and_restart()
            if restarted and on_restart is not None:
                on_restart(restarted)
            time.sleep(interval_seconds)
