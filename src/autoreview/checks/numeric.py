"""The numeric / logic reviewer's engine.

A check is a small declarative spec (plain JSON). Some are generic invariants
that hold for any analysis (proportions sum to 1, counts are non-negative, the
same quantity reported by two analyses must agree); others are authored by the
numeric-reviewer agent for the specific task (a dimensional identity such as
``count == fraction * total``, an expected ordering control < disease, ...).
Either way the spec is evaluated here deterministically.

A spec looks like:

    {
      "id": "frac-sum",
      "kind": "sum",                 # sum | equal | bounds | monotonic | approx | expr
      "description": "cell-type fractions sum to 1",
      "severity": "error",           # error (default) | warn
      ... kind-specific fields ...
    }

Values are referenced through "refs", each of which is one of:
    3.14                              # a literal number
    "mac_pct.huamo"                   # dotted key into the host claim's numbers
    {"value": 3.14}                   # an explicit literal
    {"claim": "other-id", "key": "n"} # a number from ANOTHER claim (cross-analysis)
"""
from .expr import safe_eval, ExprError

__all__ = ["run_check", "run_checks", "CheckError"]

_MISSING = object()


class CheckError(ValueError):
    """Raised when a spec is malformed (as opposed to a check simply failing)."""


def _dig(mapping, dotted):
    cur = mapping
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return _MISSING
    return cur


def _resolve(ref, numbers, get_claim_numbers):
    """Resolve a single ref to a number (see module docstring)."""
    if isinstance(ref, (int, float)) and not isinstance(ref, bool):
        return ref
    if isinstance(ref, str):
        val = _dig(numbers, ref)
        if val is _MISSING:
            raise CheckError(f"key {ref!r} not found in claim numbers")
        return val
    if isinstance(ref, dict):
        if "value" in ref:
            return ref["value"]
        if "claim" in ref:
            other = get_claim_numbers(ref["claim"])
            if other is None:
                raise CheckError(f"referenced claim {ref['claim']!r} has no numbers")
            val = _dig(other, ref["key"])
            if val is _MISSING:
                raise CheckError(f"key {ref['key']!r} not in claim {ref['claim']!r}")
            return val
    raise CheckError(f"cannot resolve ref {ref!r}")


def _resolve_list(refs, numbers, get):
    return [_resolve(r, numbers, get) for r in refs]


def _close(a, b, tol, rel):
    if rel:
        denom = max(abs(a), abs(b), 1e-12)
        return abs(a - b) / denom <= tol
    return abs(a - b) <= tol


def run_check(spec, numbers=None, get_claim_numbers=None):
    """Evaluate one check spec. Returns
    {id, kind, severity, passed, detail, observed}.

    A malformed spec is reported as a failed check (passed=False) with the
    parse error in ``detail`` rather than raising, so one bad spec cannot abort
    a whole review batch.
    """
    numbers = numbers or {}
    get = get_claim_numbers or (lambda _id: None)
    kind = spec.get("kind")
    severity = spec.get("severity", "error")
    cid = spec.get("id", kind or "check")
    tol = spec.get("tol", 1e-6)
    rel = spec.get("rel", False)

    def result(passed, detail, observed=None):
        return {"id": cid, "kind": kind, "severity": severity,
                "passed": bool(passed), "detail": detail, "observed": observed}

    try:
        if kind == "sum":
            vals = _resolve_list(spec["values"], numbers, get)
            target = _resolve(spec.get("target", 1.0), numbers, get)
            total = sum(vals)
            ok = _close(total, target, tol, rel)
            return result(ok, f"sum={total:.6g} vs target {target:.6g} "
                              f"(tol {tol}{' rel' if rel else ''})", total)

        if kind == "equal":
            vals = _resolve_list(spec["values"], numbers, get)
            if len(vals) < 2:
                raise CheckError("'equal' needs at least 2 values")
            ref = vals[0]
            ok = all(_close(v, ref, tol, rel) for v in vals[1:])
            spread = max(vals) - min(vals)
            return result(ok, f"values={[round(v, 6) for v in vals]} "
                              f"spread={spread:.6g} (tol {tol}{' rel' if rel else ''})", vals)

        if kind == "bounds":
            vals = _resolve_list(spec["values"], numbers, get)
            lo = spec.get("lo", float("-inf"))
            hi = spec.get("hi", float("inf"))
            bad = [v for v in vals if v < lo or v > hi]
            return result(not bad, f"range requested [{lo}, {hi}]; "
                                   f"out of range: {[round(v, 6) for v in bad]}", vals)

        if kind == "monotonic":
            vals = _resolve_list(spec["values"], numbers, get)
            direction = spec.get("direction", "increasing")
            pairs = list(zip(vals, vals[1:]))
            cmp = {
                "increasing": lambda a, b: b > a,
                "decreasing": lambda a, b: b < a,
                "nondecreasing": lambda a, b: b >= a,
                "nonincreasing": lambda a, b: b <= a,
            }.get(direction)
            if cmp is None:
                raise CheckError(f"unknown direction {direction!r}")
            ok = all(cmp(a, b) for a, b in pairs)
            return result(ok, f"sequence={[round(v, 6) for v in vals]} "
                              f"expected {direction}", vals)

        if kind == "approx":
            a = _resolve(spec["a"], numbers, get)
            b = _resolve(spec["b"], numbers, get)
            max_decades = spec.get("max_decades")
            if max_decades is not None:
                if a == 0 or b == 0:
                    ok = a == b
                    detail = f"a={a}, b={b} (zero handling)"
                else:
                    import math
                    decades = abs(math.log10(abs(a) / abs(b)))
                    ok = decades <= max_decades
                    detail = f"a={a:.6g}, b={b:.6g} differ by {decades:.3g} decades " \
                             f"(max {max_decades})"
            else:
                max_rel = spec.get("max_rel", 0.05)
                ok = _close(a, b, max_rel, rel=True)
                detail = f"a={a:.6g}, b={b:.6g} (max rel {max_rel})"
            return result(ok, detail, [a, b])

        if kind == "expr":
            variables = dict(numbers if all(isinstance(k, str) and k.isidentifier()
                                            for k in numbers) else {})
            for name, ref in (spec.get("vars") or {}).items():
                variables[name] = _resolve(ref, numbers, get)
            lhs = safe_eval(spec["lhs"], variables)
            rhs = safe_eval(str(spec.get("rhs", 0)), variables)
            ok = _close(lhs, rhs, tol, rel)
            return result(ok, f"lhs={lhs:.6g} vs rhs={rhs:.6g} "
                              f"(tol {tol}{' rel' if rel else ''})", [lhs, rhs])

        raise CheckError(f"unknown check kind {kind!r}")

    except (CheckError, ExprError, KeyError, TypeError, ZeroDivisionError) as e:
        return result(False, f"SPEC ERROR: {e}")


def run_checks(specs, numbers=None, get_claim_numbers=None):
    """Run a list of specs; return (all_errors_passed, results).

    ``all_errors_passed`` ignores warn-severity checks, so a warning never turns
    a verdict into a violation - it is surfaced but not blocking.
    """
    results = [run_check(s, numbers, get_claim_numbers) for s in specs]
    ok = all(r["passed"] for r in results if r["severity"] == "error")
    return ok, results
