"""Toy executor step.

This stands in for the code the *executor* agent would write to carry out one
plan step: it reads the (registered, hash-guarded) input, computes a result, and
emits the claims it is making - each carrying the structured numbers it produced
and the declarative checks the numeric reviewer can run against them.

It deliberately uses only the standard library so the example runs anywhere.
Run it with the example driver (`run.sh`), which guards the input first and logs
the emitted claims into the ledger.
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
CELL_TYPES = ["Mac", "Fb", "T", "Other"]


def load(path):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            for ct in CELL_TYPES:
                r[ct] = int(r[ct])
            rows.append(r)
    return rows


def main():
    rows = load(HERE / "data" / "counts.csv")

    # per-sample totals and macrophage percentage
    per_sample_total = {r["sample"]: sum(r[ct] for ct in CELL_TYPES) for r in rows}
    by_group = defaultdict(list)
    for r in rows:
        by_group[r["group"]].append(r)

    # mean macrophage % per group (the unit of analysis is the sample, not the cell)
    mac_pct = {}
    for g, rs in by_group.items():
        mac_pct[g] = round(sum(r["Mac"] / per_sample_total[r["sample"]] * 100
                               for r in rs) / len(rs), 2)

    # pooled disease composition (fractions over all disease cells)
    dis = by_group["disease"]
    dis_total = sum(per_sample_total[r["sample"]] for r in dis)
    pooled = {ct: round(sum(r[ct] for r in dis) / dis_total, 4) for ct in CELL_TYPES}
    dis_mac_count = sum(r["Mac"] for r in dis)

    # an independent second count of disease cells (sum over cell types) - should
    # agree with dis_total; this is what the cross-analysis consistency check tests
    dis_total_recount = sum(r[ct] for r in dis for ct in CELL_TYPES)

    claims = [
        {
            "id": "toy-mac-enrichment",
            "type": "data+interpretation",
            "source": "examples/toy/data/counts.csv",
            "claim": f"Macrophages rise from {mac_pct['control']}% (control) to "
                     f"{mac_pct['disease']}% (disease) and fall to "
                     f"{mac_pct['treated']}% under treatment.",
            "interpretation": "A macrophage-rich infiltrate that expands in disease "
                              "and contracts under effective treatment.",
            "numbers": {"mac_pct": mac_pct, "dis_total": dis_total,
                        "dis_mac_count": dis_mac_count},
            "checks": [
                {"id": "pct-in-range", "kind": "bounds",
                 "values": ["mac_pct.control", "mac_pct.disease", "mac_pct.treated"],
                 "lo": 0.0, "hi": 100.0,
                 "description": "percentages must lie in [0, 100]"},
                {"id": "disease-up", "kind": "monotonic",
                 "values": ["mac_pct.control", "mac_pct.disease"],
                 "direction": "increasing",
                 "description": "disease > control"},
                {"id": "treatment-down", "kind": "monotonic",
                 "values": ["mac_pct.disease", "mac_pct.treated"],
                 "direction": "decreasing",
                 "description": "treated < disease (rescue)"},
                {"id": "count-vs-fraction", "kind": "expr",
                 "lhs": "dis_mac_count",
                 "rhs": "mac_frac * dis_total",
                 "vars": {"mac_frac": {"value": round(dis_mac_count / dis_total, 4)}},
                 "tol": 1.0,
                 "description": "dimensional identity count == fraction * total"},
            ],
            "search_terms": ["macrophage rich infiltrate disease",
                             "treatment reduces macrophage infiltrate"],
        },
        {
            "id": "toy-disease-composition",
            "type": "data",
            "source": "examples/toy/data/counts.csv",
            "claim": "Pooled disease composition: "
                     + ", ".join(f"{ct} {pooled[ct]:.3f}" for ct in CELL_TYPES) + ".",
            "numbers": {"pooled": pooled,
                        "dis_total": dis_total, "dis_total_recount": dis_total_recount},
            "checks": [
                {"id": "fractions-sum-to-one", "kind": "sum",
                 "values": [f"pooled.{ct}" for ct in CELL_TYPES],
                 "target": 1.0, "tol": 1e-9,
                 "description": "cell-type fractions partition the cells"},
                {"id": "fractions-bounded", "kind": "bounds",
                 "values": [f"pooled.{ct}" for ct in CELL_TYPES], "lo": 0.0, "hi": 1.0},
                {"id": "total-consistent", "kind": "equal",
                 "values": ["dis_total", "dis_total_recount"], "tol": 0,
                 "description": "two independent counts of disease cells must agree"},
                {"id": "total-matches-other-claim", "kind": "equal",
                 "values": ["dis_total",
                            {"claim": "toy-mac-enrichment", "key": "dis_total"}],
                 "tol": 0,
                 "description": "cross-analysis: same disease total as the enrichment claim"},
            ],
        },
    ]
    json.dump(claims, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
