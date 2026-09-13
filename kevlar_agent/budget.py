"""
Per-feature budget guards.

Real failure this fixes: two features shared one provider API key with
no spend isolation. A usage spike in one feature silently starved the
other of quota mid-conversation — nobody could tell which feature was
actually responsible until the audit log was cross-referenced by hand.

The fix: every paid call declares which "feature" it belongs to and how
much it costs, and gets checked against that feature's own monthly
ceiling — independent of every other feature, even if they share the
same underlying API key.
"""

from __future__ import annotations

import functools
import json
import time
from pathlib import Path
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


class BudgetExceeded(Exception):
    """Raised when a feature's monthly spend ceiling would be exceeded."""

    def __init__(self, feature: str, spent: float, limit: float):
        self.feature = feature
        self.spent = spent
        self.limit = limit
        super().__init__(
            f"'{feature}' has spent ${spent:.2f} of its ${limit:.2f}/month budget"
        )


class _Ledger:
    """Tracks spend per feature per calendar month, persisted to a small JSON file."""

    def __init__(self, storage_path: str | Path):
        self.path = Path(storage_path)

    def _month_key(self) -> str:
        return time.strftime("%Y-%m")

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def spent(self, feature: str) -> float:
        return self._load().get(feature, {}).get(self._month_key(), 0.0)

    def add(self, feature: str, amount: float) -> float:
        data = self._load()
        month = self._month_key()
        data.setdefault(feature, {})
        data[feature][month] = data[feature].get(month, 0.0) + amount
        self._save(data)
        return data[feature][month]


def budget_guard(
    feature: str,
    *,
    monthly_limit_usd: float,
    cost_usd: float | Callable[..., float],
    storage_path: str | Path = ".kevlar_budget.json",
) -> Callable[[F], F]:
    """Enforce an independent monthly spend ceiling for one named feature.

    Args:
        feature: a stable name for the thing being metered (e.g. "image_gen").
            Two decorators with different ``feature`` names never share a budget,
            even if they hit the same paid API underneath.
        monthly_limit_usd: the ceiling for this feature, this calendar month.
        cost_usd: either a fixed cost per call, or a callable that receives the
            same ``(*args, **kwargs)`` as the wrapped function and returns the
            cost for that specific call (use this when cost varies by input,
            e.g. token count or output length).
        storage_path: where running spend is persisted between calls/restarts.

    Raises:
        BudgetExceeded: if this call would push the feature over its ceiling.
            The wrapped function is never invoked in that case.

    Example:
        >>> @budget_guard("image_gen", monthly_limit_usd=3.0, cost_usd=0.04)
        ... def generate_clip(prompt: str) -> str:
        ...     return f"generated: {prompt}"
    """
    ledger = _Ledger(storage_path)

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            call_cost = cost_usd(*args, **kwargs) if callable(cost_usd) else cost_usd
            spent = ledger.spent(feature)
            if spent + call_cost > monthly_limit_usd:
                raise BudgetExceeded(feature, spent, monthly_limit_usd)
            result = func(*args, **kwargs)
            ledger.add(feature, call_cost)
            return result

        return wrapper  # type: ignore[return-value]

    return decorator
