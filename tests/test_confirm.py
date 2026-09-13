import pytest

from kevlar_agent import ConfirmationRequired, require_confirmation


def test_call_without_confirmed_raises():
    @require_confirmation("do the risky thing")
    def risky() -> str:
        return "done"

    with pytest.raises(ConfirmationRequired):
        risky()


def test_call_with_confirmed_true_runs():
    @require_confirmation("do the risky thing")
    def risky() -> str:
        return "done"

    assert risky(confirmed=True) == "done"


def test_confirmed_false_still_blocks():
    @require_confirmation("do the risky thing")
    def risky() -> str:
        return "done"

    with pytest.raises(ConfirmationRequired):
        risky(confirmed=False)


def test_summary_can_be_built_from_args():
    seen = {}

    @require_confirmation(lambda amount: f"transfer ${amount}")
    def transfer(amount: float) -> str:
        return f"transferred ${amount}"

    try:
        transfer(50)
    except ConfirmationRequired as e:
        seen["summary"] = e.summary
    assert seen["summary"] == "transfer $50"
    assert transfer(50, confirmed=True) == "transferred $50"


def test_confirmed_kwarg_not_forwarded_to_wrapped_function():
    @require_confirmation("x")
    def action(**kwargs) -> dict:
        return kwargs

    assert action(confirmed=True, foo="bar") == {"foo": "bar"}
