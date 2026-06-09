import pytest

from autoreview.checks.expr import safe_eval, ExprError


def test_arithmetic():
    assert safe_eval("1 + 2 * 3", {}) == 7
    assert safe_eval("(a + b) / 2", {"a": 4, "b": 6}) == 5
    assert safe_eval("2 ** 10", {}) == 1024


def test_functions_and_lists():
    assert safe_eval("sum([a, b, c])", {"a": 0.2, "b": 0.3, "c": 0.5}) == pytest.approx(1.0)
    assert safe_eval("abs(-3)", {}) == 3
    assert safe_eval("max(xs)", {"xs": [1, 9, 4]}) == 9
    assert safe_eval("log2(n)", {"n": 8}) == pytest.approx(3.0)


def test_unknown_variable_rejected():
    with pytest.raises(ExprError):
        safe_eval("a + missing", {"a": 1})


@pytest.mark.parametrize("evil", [
    "__import__('os').system('echo hi')",
    "().__class__",
    "open('/etc/passwd')",
    "a if a else b",
    "[x for x in range(3)]",
])
def test_sandbox_rejects_dangerous_input(evil):
    with pytest.raises(ExprError):
        safe_eval(evil, {"a": 1, "b": 2})
