import time

from kevlar_agent import dedupe


def test_second_identical_call_is_suppressed():
    calls = []

    @dedupe(window_seconds=5)
    def launch(device_id: str) -> str:
        calls.append(device_id)
        return f"launched {device_id}"

    launch("phone-1")
    launch("phone-1")  # duplicate, within window
    assert calls == ["phone-1"]


def test_different_args_are_not_deduped():
    calls = []

    @dedupe(window_seconds=5)
    def launch(device_id: str) -> str:
        calls.append(device_id)
        return device_id

    launch("phone-1")
    launch("phone-2")
    assert calls == ["phone-1", "phone-2"]


def test_call_after_window_expires_is_not_suppressed():
    calls = []

    @dedupe(window_seconds=0.05)
    def launch(device_id: str) -> str:
        calls.append(device_id)
        return device_id

    launch("phone-1")
    time.sleep(0.1)
    launch("phone-1")
    assert calls == ["phone-1", "phone-1"]


def test_on_duplicate_value_is_returned():
    @dedupe(window_seconds=5, on_duplicate="already running")
    def launch(device_id: str) -> str:
        return f"launched {device_id}"

    assert launch("phone-9") == "launched phone-9"
    assert launch("phone-9") == "already running"
