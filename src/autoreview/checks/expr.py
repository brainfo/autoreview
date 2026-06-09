"""A small, safe arithmetic expression evaluator.

The numeric reviewer authors task-specific invariants as expressions over named
variables (e.g. "count == fraction * total", "sum(fractions) == 1"). Those
expressions are evaluated here deterministically, so the agent contributes the
*logic* of the check while the *arithmetic* is never trusted to an LLM.

Only a whitelisted subset of Python is allowed: numeric literals, named
variables, the standard arithmetic operators, list/tuple literals, and a fixed
set of math functions. Anything else (attribute access, calls to other names,
comprehensions, dunder tricks) raises ExprError, so a check spec can never read
the filesystem, import a module, or otherwise escape the sandbox.
"""
import ast
import math

__all__ = ["safe_eval", "ExprError", "ALLOWED_FUNCS"]


class ExprError(ValueError):
    """Raised for a malformed or disallowed expression."""


ALLOWED_FUNCS = {
    "abs": abs, "min": min, "max": max, "sum": sum, "len": len,
    "round": round, "sqrt": math.sqrt, "exp": math.exp,
    "log": math.log, "log2": math.log2, "log10": math.log10,
    "floor": math.floor, "ceil": math.ceil,
}

_BINOPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.FloorDiv: lambda a, b: a // b,
    ast.Mod: lambda a, b: a % b,
    ast.Pow: lambda a, b: a ** b,
}
_UNARYOPS = {ast.UAdd: lambda a: +a, ast.USub: lambda a: -a}


def safe_eval(expr, variables):
    """Evaluate ``expr`` (a string) over the ``variables`` mapping.

    Returns the resulting number (or list, for a list/tuple literal). Raises
    ExprError for anything outside the whitelisted grammar or for an unknown
    name / function.
    """
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise ExprError(f"cannot parse expression {expr!r}: {e}") from None
    return _eval(tree.body, variables)


def _eval(node, variables):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        raise ExprError(f"only numeric constants allowed, got {node.value!r}")
    if isinstance(node, ast.Name):
        if node.id in variables:
            return variables[node.id]
        raise ExprError(f"unknown variable {node.id!r}")
    if isinstance(node, ast.BinOp):
        op = _BINOPS.get(type(node.op))
        if op is None:
            raise ExprError(f"operator {type(node.op).__name__} not allowed")
        return op(_eval(node.left, variables), _eval(node.right, variables))
    if isinstance(node, ast.UnaryOp):
        op = _UNARYOPS.get(type(node.op))
        if op is None:
            raise ExprError(f"unary operator {type(node.op).__name__} not allowed")
        return op(_eval(node.operand, variables))
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_eval(e, variables) for e in node.elts]
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in ALLOWED_FUNCS:
            name = getattr(node.func, "id", type(node.func).__name__)
            raise ExprError(f"call to {name!r} not allowed")
        if node.keywords:
            raise ExprError("keyword arguments not allowed in expressions")
        args = [_eval(a, variables) for a in node.args]
        return ALLOWED_FUNCS[node.func.id](*args)
    raise ExprError(f"syntax element {type(node).__name__} not allowed")
