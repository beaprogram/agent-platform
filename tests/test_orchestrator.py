"""Unit tests for the agent orchestrator's pure functions (no AWS calls)."""


def test_calculator_basic(orch):
    assert orch._tool_calculate({"expression": "23 * 19 + 4"}) == "441"


def test_calculator_rejects_code_injection(orch):
    out = orch._tool_calculate({"expression": "__import__('os').system('echo hi')"})
    assert out.startswith("Error")


def test_calculator_rejects_names(orch):
    assert orch._tool_calculate({"expression": "open"}).startswith("Error")


def test_cosine_identical_vectors(orch):
    assert abs(orch._cosine([1.0, 0.0, 0.0], [1.0, 0.0, 0.0]) - 1.0) < 1e-9


def test_cosine_orthogonal_vectors(orch):
    assert abs(orch._cosine([1.0, 0.0, 0.0], [0.0, 1.0, 0.0])) < 1e-9


def test_cosine_handles_zero_vector(orch):
    assert orch._cosine([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_search_tool_registered(orch):
    assert "search_corpus" in orch.TOOL_IMPLS
