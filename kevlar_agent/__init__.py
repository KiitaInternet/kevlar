"""
KEVLAR — reliability primitives for AI agents that have to survive real use.

Six small, dependency-free utilities, each extracted from a real production
failure in an always-on voice AI assistant:

    dedupe               suppress duplicate calls within a time window
    budget_guard         per-feature monthly spend ceiling
    require_confirmation enforce an explicit confirm flag for risky actions
    silent(...)          run a blocking/interactive call with a hard timeout
    AuditLog             structured, append-only call log (JSONL)
    Watchdog             supervise external processes, restart what dies

None of this is clever. All of it is necessary once something runs
unattended long enough for the boring failure modes to show up.
"""

from .dedupe import dedupe
from .budget import BudgetExceeded, budget_guard
from .confirm import ConfirmationRequired, require_confirmation
from .silent import SilentTimeout, silent
from .audit import AuditLog
from .watchdog import Watchdog

__all__ = [
    "dedupe",
    "budget_guard",
    "BudgetExceeded",
    "require_confirmation",
    "ConfirmationRequired",
    "silent",
    "SilentTimeout",
    "AuditLog",
    "Watchdog",
]

__version__ = "0.1.0"
