"""Executor stand-in for the cohort-divergence example.

This is the deterministic counterpart of what the *executor* agent would do, for
a question that deliberately evokes a **contract deviation**:

    "Across cohortA.csv and cohortB.csv, does disease raise macrophage
     infiltration consistently? Pool the cohorts and compare disease vs control."

cohortA holds raw counts (rows sum to ~300); cohortB holds fractions (rows sum to
~1). The planned step-3 pools the two as if both were counts. A faithful executor
cannot honestly do that, so in pass 1 it:
  * records what it *can* honestly establish (the scale of each cohort), and
  * records a `contract` deviation against the pooled claim instead of fabricating
    a number - it skips claim-pooled-mac and names it in the deviation.

After the gate accepts the deviation and the planner re-plans, pass 2 does the
honest within-cohort comparison, and discovers the disease effect is NOT
consistent across cohorts (it rises in A, falls in B).

Stdlib only, so the example runs anywhere.

    python analyze.py 1 claims       # pass-1 claims  (scale detection)
    python analyze.py 1 deviations   # pass-1 deviation(s)
    python analyze.py 2 claims       # pass-2 claims  (stratified comparison)
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
CELL_TYPES = ["Mac", "Fb", "T", "Other"]
COHORTS = {"A": HERE / "data" / "cohortA.csv", "B": HERE / "data" / "cohortB.csv"}


def load(path):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            for ct in CELL_TYPES:
                r[ct] = float(r[ct])
            rows.append(r)
    return rows


def row_total(r):
    return sum(r[ct] for ct in CELL_TYPES)


def group_mean_mac_fraction(rows, group):
    fr = [r["Mac"] / row_total(r) for r in rows if r["group"] == group]
    return round(sum(fr) / len(fr), 4)


# -- pass 1: establish each cohort's scale; refuse the pooled comparison --------
def pass1_claims():
    nums = {}
    for name, path in COHORTS.items():
        rows = load(path)
        totals = [row_total(r) for r in rows]
        mean_total = round(sum(totals) / len(totals), 4)
        max_dev_from_1 = round(max(abs(t - 1.0) for t in totals), 4)
        nums[name] = {"mean_row_total": mean_total, "max_dev_from_1": max_dev_from_1}
    return [{
        "id": "claim-cohort-scale",
        "type": "data",
        "source": "examples/cohort_divergence/data",
        "loop": 1,
        "claim": (f"cohortA rows are raw counts (mean row total "
                  f"{nums['A']['mean_row_total']}); cohortB rows are fractions "
                  f"(every row sums to 1, max deviation "
                  f"{nums['B']['max_dev_from_1']}). The two cohorts are on "
                  f"different scales."),
        "numbers": {"A_mean_row_total": nums["A"]["mean_row_total"],
                    "A_max_dev_from_1": nums["A"]["max_dev_from_1"],
                    "B_mean_row_total": nums["B"]["mean_row_total"],
                    "B_max_dev_from_1": nums["B"]["max_dev_from_1"]},
        "checks": [
            {"id": "A-is-counts", "kind": "bounds", "values": ["A_mean_row_total"],
             "lo": 10.0, "hi": 1e12,
             "description": "cohortA rows are large totals -> raw counts"},
            {"id": "B-is-fractions", "kind": "bounds", "values": ["B_max_dev_from_1"],
             "lo": 0.0, "hi": 0.01,
             "description": "cohortB rows sum to 1 -> already fractions"},
            {"id": "scales-differ", "kind": "approx",
             "a": "A_mean_row_total", "b": "B_mean_row_total", "max_decades": 1,
             "severity": "warn",
             "description": "the two cohorts differ by >1 order of magnitude in scale"},
        ],
    }]


def pass1_deviations():
    return [{
        "id": "dev-step3-scale",
        "loop": 1,
        "kind": "contract",
        "scope": "forward",
        "affects_step": "step-3",
        "affects_claims": ["claim-pooled-mac"],
        "observed": ("step-3 pools cohortA and cohortB as if both were raw counts, "
                     "but cohortB rows already sum to 1 (fractions). Summing raw "
                     "'counts' across the two is dominated by cohortA and is "
                     "meaningless; the planned pooled disease-vs-control claim "
                     "cannot be computed honestly."),
        "proposed_action": ("Stratify by cohort: compare disease vs control within "
                            "each cohort on per-sample Mac fractions, and only "
                            "assert a consistent disease effect if both cohorts "
                            "agree in direction."),
    }]


# -- pass 2: the re-planned, honest within-cohort comparison --------------------
def pass2_claims():
    out = []
    delta = {}
    for name, path in COHORTS.items():
        rows = load(path)
        ctrl = group_mean_mac_fraction(rows, "control")
        dis = group_mean_mac_fraction(rows, "disease")
        d = round(dis - ctrl, 4)
        delta[name] = d
        out.append({
            "id": f"claim-mac-cohort{name}",
            "type": "data+interpretation",
            "source": f"examples/cohort_divergence/data/cohort{name}.csv",
            "loop": 2,
            "claim": (f"cohort{name}: mean macrophage fraction is {ctrl} in control "
                      f"and {dis} in disease (delta {d:+})."),
            "interpretation": (f"In cohort {name}, disease "
                               + ("raises" if d > 0 else "lowers")
                               + " the macrophage fraction."),
            "numbers": {"ctrl_mac": ctrl, "dis_mac": dis, "delta": d},
            "checks": [
                {"id": "frac-bounds", "kind": "bounds",
                 "values": ["ctrl_mac", "dis_mac"], "lo": 0.0, "hi": 1.0},
                {"id": "delta-identity", "kind": "expr",
                 "lhs": "delta", "rhs": "dis_mac - ctrl_mac",
                 "vars": {}, "tol": 1e-6,
                 "description": "delta == disease - control"},
                {"id": "direction", "kind": "monotonic",
                 "values": ["ctrl_mac", "dis_mac"],
                 "direction": "increasing" if d > 0 else "decreasing",
                 "description": "disease > control" if d > 0 else "disease < control"},
            ],
            "search_terms": ["macrophage infiltration disease cohort"],
        })
    out.append({
        "id": "claim-mac-consistency",
        "type": "data+interpretation",
        "source": "examples/cohort_divergence/data",
        "loop": 2,
        "claim": (f"The disease effect on macrophage fraction is NOT consistent "
                  f"across cohorts: it rises in cohort A (delta {delta['A']:+}) but "
                  f"falls in cohort B (delta {delta['B']:+}); the product of the two "
                  f"deltas is {round(delta['A'] * delta['B'], 4)} (< 0)."),
        "interpretation": ("Macrophage response to disease is cohort-dependent, not a "
                           "uniform infiltration; the originally requested pooled "
                           "answer would have masked this divergence."),
        "numbers": {"deltaA": delta["A"], "deltaB": delta["B"],
                    "product": round(delta["A"] * delta["B"], 4)},
        "checks": [
            {"id": "product-identity", "kind": "expr",
             "lhs": "product", "rhs": "dA * dB",
             "vars": {"dA": {"claim": "claim-mac-cohortA", "key": "delta"},
                      "dB": {"claim": "claim-mac-cohortB", "key": "delta"}},
             "tol": 1e-6,
             "description": "product == deltaA * deltaB (cross-claim consistency)"},
            {"id": "directions-oppose", "kind": "bounds", "values": ["product"],
             "lo": -1.0, "hi": -1e-9,
             "description": "product < 0 -> the two cohorts move in opposite directions"},
        ],
        "search_terms": ["cohort heterogeneity macrophage disease"],
    })
    return out


EMIT = {
    ("1", "claims"): pass1_claims,
    ("1", "deviations"): pass1_deviations,
    ("2", "claims"): pass2_claims,
    ("2", "deviations"): lambda: [],
}


def main():
    if len(sys.argv) != 3 or (sys.argv[1], sys.argv[2]) not in EMIT:
        sys.exit("usage: analyze.py {1|2} {claims|deviations}")
    json.dump(EMIT[(sys.argv[1], sys.argv[2])](), sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
