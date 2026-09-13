import pytest

from kevlar_agent import BudgetExceeded, budget_guard


def test_calls_within_budget_succeed(tmp_path):
    storage = tmp_path / "budget.json"

    @budget_guard("image_gen", monthly_limit_usd=1.0, cost_usd=0.25, storage_path=storage)
    def generate(prompt: str) -> str:
        return f"generated: {prompt}"

    for _ in range(4):
        generate("a cat")


def test_call_over_budget_raises_and_does_not_run(tmp_path):
    storage = tmp_path / "budget.json"
    calls = []

    @budget_guard("image_gen", monthly_limit_usd=1.0, cost_usd=0.25, storage_path=storage)
    def generate(prompt: str) -> str:
        calls.append(prompt)
        return prompt

    for _ in range(4):
        generate("ok")
    with pytest.raises(BudgetExceeded):
        generate("one too many")
    assert calls == ["ok", "ok", "ok", "ok"]  # the 5th call never ran


def test_features_have_independent_budgets(tmp_path):
    storage = tmp_path / "budget.json"

    @budget_guard("feature_a", monthly_limit_usd=0.10, cost_usd=0.10, storage_path=storage)
    def call_a() -> str:
        return "a"

    @budget_guard("feature_b", monthly_limit_usd=0.10, cost_usd=0.10, storage_path=storage)
    def call_b() -> str:
        return "b"

    call_a()  # exhausts feature_a's budget
    call_b()  # feature_b is untouched, should still succeed
    with pytest.raises(BudgetExceeded):
        call_a()


def test_variable_cost_callable(tmp_path):
    storage = tmp_path / "budget.json"

    @budget_guard(
        "tokens",
        monthly_limit_usd=1.0,
        cost_usd=lambda text: len(text) * 0.01,
        storage_path=storage,
    )
    def summarize(text: str) -> str:
        return text[:10]

    summarize("short")  # cheap
    with pytest.raises(BudgetExceeded):
        summarize("x" * 200)  # expensive enough to exceed on its own
