"""
Full-fidelity audit trail for tool/agent calls.

Real failure this fixes: without a record of what was actually called,
with what arguments, from where, and whether it errored, "it worked when
I tested it" is the only signal available — and that signal lies. The
audit log is what revealed, after the fact, that a background scheduler
was silently calling the same five "safe" tools every day while a dozen
others had never been exercised outside manual testing.

Deliberately boring: append-only JSONL, one file per day, no external
dependencies. Never raises — a logging failure must not take down the
call it's trying to record.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class AuditLog:
    """Append-only, structured call log — one JSON object per line, per day.

    Example:
        >>> log = AuditLog("logs/audit")
        >>> log.record("send_email", {"to": "x@example.com"}, result="sent", source="voice")
        >>> recent = log.tail(limit=10)
    """

    def __init__(self, directory: str | Path):
        self.directory = Path(directory)

    def _file_for_today(self) -> Path:
        return self.directory / f"{time.strftime('%Y-%m-%d')}.jsonl"

    def record(
        self,
        tool: str,
        args: Any = None,
        *,
        result: Any = None,
        error: str | None = None,
        duration_ms: float | None = None,
        source: str = "default",
    ) -> None:
        """Append one call record. Never raises, even if the write itself fails."""
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            row = {
                "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                "source": source,
                "tool": tool,
                "args": _safe_str(args),
                "result": _safe_str(result),
                "error": error,
                "duration_ms": round(duration_ms, 1) if duration_ms is not None else None,
            }
            with open(self._file_for_today(), "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        except Exception:
            pass  # a logging failure must never break the caller

    def tail(self, limit: int = 50, tool: str | None = None) -> list[dict]:
        """Return the most recent records, newest first, optionally filtered by tool name."""
        if not self.directory.exists():
            return []
        out: list[dict] = []
        for path in sorted(self.directory.glob("*.jsonl"), reverse=True):
            for line in reversed(path.read_text(encoding="utf-8").splitlines()):
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                if tool and row.get("tool") != tool:
                    continue
                out.append(row)
                if len(out) >= limit:
                    return out
        return out


def _safe_str(value: Any, max_chars: int = 2000) -> str | None:
    if value is None:
        return None
    try:
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return "<unserializable>"
    if len(text) > max_chars:
        return text[:max_chars] + f"...(truncated {len(text) - max_chars} chars)"
    return text
