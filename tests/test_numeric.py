from autoreview.checks.numeric import run_check, run_checks


def test_sum_to_one_pass_and_fail():
    nums = {"frac": {"a": 0.2, "b": 0.3, "c": 0.5}}
    ok = run_check({"id": "s", "kind": "sum",
                    "values": ["frac.a", "frac.b", "frac.c"],
                    "target": 1.0, "tol": 1e-9}, nums)
    assert ok["passed"]
    bad = run_check({"id": "s", "kind": "sum",
                     "values": ["frac.a", "frac.b"], "target": 1.0, "tol": 1e-9}, nums)
    assert not bad["passed"]


def test_dimensional_identity_count_equals_fraction_times_total():
    nums = {"count": 14544, "fraction": 0.41, "total": 35473}
    # count should equal fraction * total within rounding
    r = run_check({"id": "dim", "kind": "expr",
                   "lhs": "count", "rhs": "fraction * total",
                   "tol": 0.02, "rel": True}, nums)
    assert r["passed"]


def test_cross_analysis_consistency():
    # the same N reported by two different claims must agree
    def get(cid):
        return {"analysis_a": {"n_cells": 1925}, "analysis_b": {"n_cells": 1925}}[cid]

    r = run_check({"id": "consist", "kind": "equal",
                   "values": [{"claim": "analysis_a", "key": "n_cells"},
                              {"claim": "analysis_b", "key": "n_cells"}],
                   "tol": 0}, {}, get)
    assert r["passed"]


def test_bounds_catches_impossible_proportion():
    r = run_check({"id": "b", "kind": "bounds",
                   "values": ["p"], "lo": 0.0, "hi": 1.0}, {"p": 1.4})
    assert not r["passed"]


def test_monotonic_disease_ordering():
    nums = {"ctrl": 7.1, "disease": 41.4, "treated": 11.9}
    inc = run_check({"id": "m", "kind": "monotonic",
                     "values": ["ctrl", "disease"], "direction": "increasing"}, nums)
    assert inc["passed"]
    # full sequence ctrl < disease < treated is NOT monotonic (treatment lowers it)
    seq = run_check({"id": "m", "kind": "monotonic",
                     "values": ["ctrl", "disease", "treated"],
                     "direction": "increasing"}, nums)
    assert not seq["passed"]


def test_approx_order_of_magnitude():
    ok = run_check({"id": "a", "kind": "approx", "a": 14544, "b": 14000,
                    "max_decades": 1}, {})
    assert ok["passed"]
    off = run_check({"id": "a", "kind": "approx", "a": 14544, "b": 14,
                     "max_decades": 1}, {})
    assert not off["passed"]


def test_malformed_spec_is_failed_not_raised():
    r = run_check({"id": "x", "kind": "sum", "values": ["does.not.exist"]}, {})
    assert not r["passed"]
    assert "SPEC ERROR" in r["detail"]


def test_run_checks_warns_do_not_block():
    nums = {"p": 1.4}
    ok, results = run_checks([
        {"id": "hard", "kind": "bounds", "values": ["p"], "lo": 0, "hi": 2},
        {"id": "soft", "kind": "bounds", "values": ["p"], "lo": 0, "hi": 1,
         "severity": "warn"},
    ], nums)
    assert ok  # the warn failure does not block
    assert not [r for r in results if r["id"] == "soft"][0]["passed"]
