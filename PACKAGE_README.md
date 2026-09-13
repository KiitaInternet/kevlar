# kevlar-agent

Reliability primitives for AI agents that have to survive real use — extracted
from a voice AI assistant that has run continuously, unattended, in production.
Zero dependencies (an optional one for the watchdog). MIT licensed.

**[Why this exists / the full case study →](https://kiitainternet.github.io/kevlar/)**

```bash
pip install kevlar-agent
```

## The six primitives

```python
from kevlar_agent import dedupe, budget_guard, require_confirmation, silent, AuditLog, Watchdog
```

### `dedupe` — suppress duplicate calls

```python
@dedupe(window_seconds=5)
def launch_session(device_id: str) -> str:
    return f"launched {device_id}"
```

An identical call within the window is skipped instead of running the side
effect twice — fixes the "model emitted the same tool call twice" class of bug.

### `budget_guard` — independent per-feature spend ceilings

```python
@budget_guard("image_gen", monthly_limit_usd=3.0, cost_usd=0.04)
def generate_clip(prompt: str) -> str:
    ...
```

Raises `BudgetExceeded` before the call runs if this *specific feature* would
go over its own monthly ceiling — even if ten other features share the same
underlying API key.

### `require_confirmation` — code-enforced consent for irreversible actions

```python
@require_confirmation(lambda amount: f"transfer ${amount}")
def transfer(amount: float) -> str:
    ...

transfer(50)                    # raises ConfirmationRequired
transfer(50, confirmed=True)    # runs
```

A prompt-only guardrail is a suggestion the model can miss. This one is a gate.

### `silent` — call anything with a hard timeout, from any thread

```python
try:
    token = silent(refresh_oauth_token, timeout_seconds=15)
except SilentTimeout:
    token = None  # fail fast instead of hanging forever
```

Fixes the "OAuth helper opened a browser and waited for a click that never
came, because nobody was watching" class of bug.

### `AuditLog` — structured, append-only call log

```python
log = AuditLog("logs/audit")
log.record("send_email", {"to": "x@example.com"}, result="sent", source="voice")
log.tail(limit=20)
```

One JSON object per line, one file per day. Never raises.

### `Watchdog` — restart what dies

```python
from kevlar_agent.watchdog import Watched

wd = Watchdog([
    Watched("telegram_bot.py", start=["python", "telegram_bot.py"]),
    Watched("mobile_relay.py", start=["python", "mobile_relay.py"]),
])
wd.run_forever(interval_seconds=300)
```

Liveness checking uses `psutil` by default (`pip install kevlar-agent[watchdog]`),
or pass your own `is_alive` callable.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
