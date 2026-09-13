import time

import pytest

from kevlar_agent import SilentTimeout, silent


def test_fast_call_returns_normally():
    def quick(x: int) -> int:
        return x * 2

    assert silent(quick, 21, timeout_seconds=5) == 42


def test_slow_call_raises_silent_timeout_instead_of_hanging():
    def slow_forever() -> None:
        time.sleep(60)

    start = time.monotonic()
    with pytest.raises(SilentTimeout):
        silent(slow_forever, timeout_seconds=0.2)
    elapsed = time.monotonic() - start
    assert elapsed < 5  # caller got control back fast, did not wait 60s


def test_kwargs_are_passed_through():
    def greet(name: str, greeting: str = "hi") -> str:
        return f"{greeting}, {name}"

    assert silent(greet, "Sir", greeting="hello", timeout_seconds=5) == "hello, Sir"
