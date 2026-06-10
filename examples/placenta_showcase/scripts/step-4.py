"""Step 4: SHIFT in cell-type composition first trimester -> term on shared labels.

Input: results/step-3_composition.csv (FT annotation_withperi, term annotate_general).
Normalize term's typo 'Hofbaucer cells' -> 'Hofbauer cells' before joining (recorded).
Restrict to the labels shared by FT annotation_withperi and term annotate_general,
recompute fractions on the shared-label denominator (each side sums to 1), then
delta = frac_term - frac_ft and log2_ratio = log2(frac_term/frac_ft).
Writes results/step-4_composition_shift.csv and emits claim JSON on stdout.
"""
import json
import math
import sys
import hashlib
import pandas as pd

COMP = "/mnt/run/jh/projects/tes_agent/results/step-3_composition.csv"
OUT = "/mnt/run/jh/projects/tes_agent/results/step-4_composition_shift.csv"

TYPO_MAP = {"Hofbaucer cells": "Hofbauer cells"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


comp = pd.read_csv(COMP)

ft = comp[(comp.dataset == "first_trimester") &
          (comp.celltype_col == "annotation_withperi")].copy()
tm = comp[(comp.dataset == "term") & (comp.celltype_col == "annotate_general")].copy()

# raw label sets (before normalization)
ft_labels_raw = sorted(ft.celltype.astype(str).unique())
tm_labels_raw = sorted(tm.celltype.astype(str).unique())

# normalize term typo
tm["celltype_norm"] = tm.celltype.astype(str).replace(TYPO_MAP)
ft["celltype_norm"] = ft.celltype.astype(str)
tm_labels_norm = sorted(tm.celltype_norm.unique())
n_typo_renamed = int((tm.celltype.astype(str) != tm.celltype_norm).sum())

shared = sorted(set(ft.celltype_norm) & set(tm.celltype_norm))

ft_counts = ft.groupby("celltype_norm")["count"].sum().to_dict()
tm_counts = tm.groupby("celltype_norm")["count"].sum().to_dict()
ft_den = sum(ft_counts[k] for k in shared)
tm_den = sum(tm_counts[k] for k in shared)

rows = []
for ct in shared:
    fft = ft_counts[ct] / ft_den
    ftm = tm_counts[ct] / tm_den
    delta = ftm - fft
    log2r = math.log2(ftm / fft)
    direction = "rises" if delta > 0 else ("falls" if delta < 0 else "flat")
    rows.append(dict(celltype=ct, frac_first_trimester=fft, frac_term=ftm,
                     delta=delta, log2_ratio=log2r, direction=direction))

# order by delta descending for readability
rows.sort(key=lambda r: r["delta"], reverse=True)
df = pd.DataFrame(rows)
df.to_csv(OUT, index=False)
sys.stderr.write(df.to_string() + "\n")
sys.stderr.write(f"shared={shared}\nFT raw={ft_labels_raw}\nTM raw={tm_labels_raw}\n"
                 f"TM norm={tm_labels_norm} typo_renamed={n_typo_renamed}\n")

comp_in = {"path": COMP, "sha256": sha256(COMP)}

by = {r["celltype"]: r for r in rows}
sum_ft = sum(r["frac_first_trimester"] for r in rows)
sum_tm = sum(r["frac_term"] for r in rows)
sum_delta = sum(r["delta"] for r in rows)


def safe(k):
    return k.replace(" ", "_")


numbers_dir = {}
for ct in shared:
    r = by[ct]
    numbers_dir[f"{safe(ct)}_frac_ft"] = r["frac_first_trimester"]
    numbers_dir[f"{safe(ct)}_frac_tm"] = r["frac_term"]
    numbers_dir[f"{safe(ct)}_delta"] = r["delta"]
    numbers_dir[f"{safe(ct)}_log2r"] = r["log2_ratio"]

claims = [
    {
        "id": "claim-shift-conservation",
        "type": "data+interpretation",
        "source": COMP,
        "claim": (f"On the shared {len(shared)}-label set, fractions sum to 1 per dataset "
                  f"(FT sum={sum_ft:.6f}, term sum={sum_tm:.6f}) and deltas sum to "
                  f"{sum_delta:.2e}, so the shift is a redistribution among compartments."),
        "interpretation": ("No cells are created or destroyed in the comparison; rises in "
                           "some compartments are exactly offset by falls in others."),
        "numbers": {
            "n_shared": len(shared),
            "sum_frac_ft": sum_ft,
            "sum_frac_tm": sum_tm,
            "sum_delta": sum_delta,
            **numbers_dir,
        },
        "checks": [
            {"id": "shift-ft-sum1", "kind": "sum",
             "values": [f"{safe(c)}_frac_ft" for c in shared], "target": 1.0, "tol": 1e-9},
            {"id": "shift-tm-sum1", "kind": "sum",
             "values": [f"{safe(c)}_frac_tm" for c in shared], "target": 1.0, "tol": 1e-9},
            {"id": "shift-delta-sum0", "kind": "sum",
             "values": [f"{safe(c)}_delta" for c in shared], "target": 0.0, "tol": 1e-9},
        ] + [
            {"id": f"shift-delta-id-{safe(c)}", "kind": "expr", "lhs": "delta",
             "rhs": "ftm - fft", "tol": 1e-12,
             "vars": {"delta": f"{safe(c)}_delta", "ftm": f"{safe(c)}_frac_tm",
                      "fft": f"{safe(c)}_frac_ft"}}
            for c in shared
        ],
        "inputs": [comp_in],
        "outputs": [{"path": OUT}],
        "search_terms": ["compositional data redistribution simplex closure"],
    },
    {
        "id": "claim-shift-direction",
        "type": "data+interpretation",
        "source": COMP,
        "claim": (f"Relative to first trimester, term has a HIGHER fraction of Hofbauer "
                  f"cells (delta={by['Hofbauer cells']['delta']:+.4f}, rises) and Stroma "
                  f"(delta={by['Stroma']['delta']:+.4f}) and a LOWER fraction of CTB "
                  f"(delta={by['CTB']['delta']:+.4f}, falls): the dominant trophoblast "
                  f"compartment shrinks as the villous stroma/macrophage compartment "
                  f"expands toward term. (term 'Hofbaucer cells' normalized to "
                  f"'Hofbauer cells'; {n_typo_renamed} rows renamed.)"),
        "interpretation": ("A decline in proliferative cytotrophoblast fraction with "
                           "relative expansion of Hofbauer (placental macrophage) and "
                           "stromal populations is consistent with placental maturation "
                           "from first trimester to term."),
        "numbers": {
            "CTB_delta": by["CTB"]["delta"],
            "CTB_log2r": by["CTB"]["log2_ratio"],
            "CTB_frac_ft": by["CTB"]["frac_first_trimester"],
            "CTB_frac_tm": by["CTB"]["frac_term"],
            "Hofbauer_delta": by["Hofbauer cells"]["delta"],
            "Hofbauer_log2r": by["Hofbauer cells"]["log2_ratio"],
            "Hofbauer_frac_ft": by["Hofbauer cells"]["frac_first_trimester"],
            "Hofbauer_frac_tm": by["Hofbauer cells"]["frac_term"],
            "Stroma_delta": by["Stroma"]["delta"],
            "n_typo_renamed": n_typo_renamed,
        },
        "checks": [
            {"id": "ctb-falls", "kind": "monotonic",
             "values": ["CTB_frac_tm", "CTB_frac_ft"], "direction": "increasing"},
            {"id": "ctb-delta-neg", "kind": "bounds", "values": ["CTB_delta"], "hi": 0},
            {"id": "ctb-log2-neg", "kind": "bounds", "values": ["CTB_log2r"], "hi": 0},
            {"id": "hofb-rises", "kind": "monotonic",
             "values": ["Hofbauer_frac_ft", "Hofbauer_frac_tm"], "direction": "increasing"},
            {"id": "hofb-delta-pos", "kind": "bounds", "values": ["Hofbauer_delta"], "lo": 0},
            {"id": "hofb-log2-pos", "kind": "bounds", "values": ["Hofbauer_log2r"], "lo": 0},
            {"id": "typo-renamed", "kind": "equal", "values": ["n_typo_renamed", 1], "tol": 0},
        ],
        "inputs": [comp_in],
        "outputs": [{"path": OUT}],
        "search_terms": ["cytotrophoblast decrease term placenta maturation",
                         "Hofbauer cells placental macrophage expansion gestation",
                         "trophoblast stroma proportion first trimester versus term"],
    },
]

print(json.dumps(claims, indent=2))
