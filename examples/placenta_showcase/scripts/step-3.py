"""Step 3: Cell-type composition within each dataset as fractions summing to 1.

FT: obs['annotation'] (6 cats) and obs['annotation_withperi'] (7 cats).
Term: obs['annotate_general'] (7 cats).
For each (dataset, celltype_col): value_counts (drop NaN) -> count, fraction.
Writes results/step-3_composition.csv and results/step-3_composition_totals.csv.
Emits claim JSON on stdout.
"""
import json
import sys
import anndata as ad
import pandas as pd

FT = "/mnt/run/jh/projects/tes_agent/first_trimester_final.h5ad"
TM = "/mnt/run/jh/projects/tes_agent/term_final.h5ad"
OUT = "/mnt/run/jh/projects/tes_agent/results/step-3_composition.csv"
OUT_TOT = "/mnt/run/jh/projects/tes_agent/results/step-3_composition_totals.csv"

FT_SHA = "85b09152b2be819023a0b8aa93557f9bc3eed793ed8df253491d651366354ce8"
TM_SHA = "888e0acd8a80c5de88a09bb2db3a69df60d94afa0019bb1e4202363842c8a0d3"


def compose(adata, col, dataset):
    s = adata.obs[col]
    n_total = int(s.shape[0])
    n_nan = int(s.isna().sum())
    vc = s.value_counts(dropna=True)
    n_annotated = int(vc.sum())
    rows = []
    for ct, cnt in vc.items():
        rows.append(dict(dataset=dataset, celltype_col=col, celltype=str(ct),
                         count=int(cnt), fraction=float(cnt) / n_annotated,
                         n_annotated=n_annotated))
    tot = dict(dataset=dataset, celltype_col=col, n_annotated=n_annotated,
               n_nan=n_nan, n_total=n_total,
               sum_fraction=float(sum(r["fraction"] for r in rows)))
    return rows, tot


comp_rows, tot_rows = [], []

ft = ad.read_h5ad(FT, backed='r')
r, t = compose(ft, "annotation", "first_trimester");           comp_rows += r; tot_rows.append(t)
r, t = compose(ft, "annotation_withperi", "first_trimester");  comp_rows += r; tot_rows.append(t)
ft.file.close()

tm = ad.read_h5ad(TM, backed='r')
r, t = compose(tm, "annotate_general", "term");                comp_rows += r; tot_rows.append(t)
tm.file.close()

comp = pd.DataFrame(comp_rows)
tot = pd.DataFrame(tot_rows)
comp.to_csv(OUT, index=False)
tot.to_csv(OUT_TOT, index=False)
sys.stderr.write(comp.to_string() + "\n\n" + tot.to_string() + "\n")


def cmap(df, dataset, col):
    sub = df[(df.dataset == dataset) & (df.celltype_col == col)]
    out = {}
    for _, r in sub.iterrows():
        out[str(r["celltype"])] = dict(count=int(r["count"]), fraction=float(r["fraction"]))
    return out, int(sub["n_annotated"].iloc[0])


ft_ann, ft_ann_N = cmap(comp, "first_trimester", "annotation")
ft_per, ft_per_N = cmap(comp, "first_trimester", "annotation_withperi")
tm_gen, tm_gen_N = cmap(comp, "term", "annotate_general")

ft_in = {"path": FT, "sha256": FT_SHA}
tm_in = {"path": TM, "sha256": TM_SHA}


def num_block(cmapd, N, keys):
    out = {"n_annotated": N}
    for k in keys:
        safe = k.replace(" ", "_")
        out[f"{safe}_count"] = cmapd[k]["count"]
        out[f"{safe}_frac"] = cmapd[k]["fraction"]
    out["sum_frac"] = sum(cmapd[k]["fraction"] for k in cmapd)
    out["sum_count"] = sum(cmapd[k]["count"] for k in cmapd)
    return out


FT_KEYS = ["CTB", "Stroma", "Hofbauer cells", "EVT", "STB", "Endothelial cells"]
FT_PERI_KEYS = ["CTB", "Stroma", "Hofbauer cells", "Perivascular", "EVT", "STB", "Endothelial cells"]
TM_KEYS = ["CTB", "Stroma", "Hofbaucer cells", "EVT", "STB", "Endothelial cells", "Perivascular"]

ft_nb = num_block(ft_ann, ft_ann_N, FT_KEYS)
ft_per_nb = num_block(ft_per, ft_per_N, FT_PERI_KEYS)
tm_nb = num_block(tm_gen, tm_gen_N, TM_KEYS)

ann_frac_refs = [f"{k.replace(' ', '_')}_frac" for k in FT_KEYS]
peri_frac_refs = [f"{k.replace(' ', '_')}_frac" for k in FT_PERI_KEYS]
tm_frac_refs = [f"{k.replace(' ', '_')}_frac" for k in TM_KEYS]

claims = [
    {
        "id": "claim-ft-composition",
        "type": "data+interpretation",
        "source": FT,
        "claim": (f"First trimester (annotation) is dominated by CTB "
                  f"({ft_ann['CTB']['count']} cells, {ft_ann['CTB']['fraction']:.3f}), "
                  f"followed by Stroma ({ft_ann['Stroma']['count']}), Hofbauer cells "
                  f"({ft_ann['Hofbauer cells']['count']}), EVT ({ft_ann['EVT']['count']}), "
                  f"STB ({ft_ann['STB']['count']}), Endothelial cells "
                  f"({ft_ann['Endothelial cells']['count']}); n_annotated={ft_ann_N}."),
        "interpretation": ("CTB (cytotrophoblast) is the single largest population in early "
                           "placenta, consistent with the proliferative trophoblast "
                           "compartment of first-trimester villi."),
        "numbers": ft_nb,
        "checks": [
            {"id": "ft-comp-frac-sum1", "kind": "sum", "values": ann_frac_refs,
             "target": 1.0, "tol": 1e-9},
            {"id": "ft-comp-frac-bounds", "kind": "bounds", "values": ann_frac_refs,
             "lo": 0, "hi": 1},
            {"id": "ft-comp-counts-sum", "kind": "equal",
             "values": ["sum_count", "n_annotated"], "tol": 0},
            {"id": "ft-comp-N-eq-ncells", "kind": "equal",
             "values": ["n_annotated", {"claim": "claim-ft-shape", "key": "n_cells"}], "tol": 0},
            {"id": "ft-comp-ctb-max", "kind": "monotonic",
             "values": ["Stroma_count", "CTB_count"], "direction": "increasing"},
            {"id": "ft-comp-ctb-count-id", "kind": "expr", "lhs": "CTB_count",
             "rhs": "round(CTB_frac*n_annotated)", "tol": 1,
             "vars": {"CTB_count": "CTB_count", "CTB_frac": "CTB_frac",
                      "n_annotated": "n_annotated"}},
        ],
        "inputs": [ft_in],
        "outputs": [{"path": OUT}, {"path": OUT_TOT}],
        "search_terms": ["cytotrophoblast dominant cell type first trimester placenta",
                         "villous cytotrophoblast proliferation early gestation"],
    },
    {
        "id": "claim-ft-withperi",
        "type": "data+interpretation",
        "source": FT,
        "claim": (f"Under annotation_withperi, first trimester gains a Perivascular "
                  f"population ({ft_per['Perivascular']['count']} cells) carved out of "
                  f"Stroma, which drops from {ft_ann['Stroma']['count']} (annotation) to "
                  f"{ft_per['Stroma']['count']} (withperi); the other 5 categories are "
                  f"unchanged."),
        "interpretation": ("Perivascular cells are a stromal subset distinguished only "
                           "under the finer annotation; choice of annotation column changes "
                           "the stromal fraction."),
        "numbers": {
            **{f"peri_{k}": v for k, v in ft_per_nb.items()},
            "ann_Stroma_count": ft_ann["Stroma"]["count"],
            "ann_n_annotated": ft_ann_N,
            "peri_Stroma_plus_Peri": ft_per["Stroma"]["count"] + ft_per["Perivascular"]["count"],
            "ann_CTB_count": ft_ann["CTB"]["count"],
            "ann_Hofbauer_count": ft_ann["Hofbauer cells"]["count"],
            "ann_EVT_count": ft_ann["EVT"]["count"],
            "ann_STB_count": ft_ann["STB"]["count"],
            "ann_Endothelial_count": ft_ann["Endothelial cells"]["count"],
        },
        "checks": [
            {"id": "peri-frac-sum1", "kind": "sum",
             "values": [f"peri_{r}" for r in peri_frac_refs], "target": 1.0, "tol": 1e-9},
            {"id": "peri-N-eq-ann-N", "kind": "equal",
             "values": ["peri_n_annotated", "ann_n_annotated"], "tol": 0},
            {"id": "peri-stroma-split", "kind": "equal",
             "values": ["peri_Stroma_plus_Peri", "ann_Stroma_count"], "tol": 0},
            {"id": "peri-CTB-unchanged", "kind": "equal",
             "values": ["peri_CTB_count", "ann_CTB_count"], "tol": 0},
            {"id": "peri-Hofb-unchanged", "kind": "equal",
             "values": ["peri_Hofbauer_cells_count", "ann_Hofbauer_count"], "tol": 0},
            {"id": "peri-EVT-unchanged", "kind": "equal",
             "values": ["peri_EVT_count", "ann_EVT_count"], "tol": 0},
            {"id": "peri-STB-unchanged", "kind": "equal",
             "values": ["peri_STB_count", "ann_STB_count"], "tol": 0},
            {"id": "peri-Endo-unchanged", "kind": "equal",
             "values": ["peri_Endothelial_cells_count", "ann_Endothelial_count"], "tol": 0},
            {"id": "peri-counts-sum", "kind": "equal",
             "values": ["peri_sum_count", "peri_n_annotated"], "tol": 0},
        ],
        "inputs": [ft_in],
        "outputs": [{"path": OUT}, {"path": OUT_TOT}],
        "search_terms": ["perivascular cells stromal subset placenta annotation"],
    },
    {
        "id": "claim-tm-composition",
        "type": "data+interpretation",
        "source": TM,
        "claim": (f"Term (annotate_general) is led by CTB ({tm_gen['CTB']['count']} cells, "
                  f"{tm_gen['CTB']['fraction']:.3f}), then Stroma "
                  f"({tm_gen['Stroma']['count']}), Hofbauer cells "
                  f"({tm_gen['Hofbaucer cells']['count']}; note source spelling "
                  f"'Hofbaucer cells'), EVT ({tm_gen['EVT']['count']}), STB "
                  f"({tm_gen['STB']['count']}), Endothelial cells "
                  f"({tm_gen['Endothelial cells']['count']}), Perivascular "
                  f"({tm_gen['Perivascular']['count']}); n_annotated={tm_gen_N}."),
        "interpretation": ("Term placenta still shows trophoblast and stromal/Hofbauer "
                           "dominance, but the relative balance among compartments differs "
                           "from first trimester (quantified in step-4)."),
        "numbers": tm_nb,
        "checks": [
            {"id": "tm-comp-frac-sum1", "kind": "sum", "values": tm_frac_refs,
             "target": 1.0, "tol": 1e-9},
            {"id": "tm-comp-frac-bounds", "kind": "bounds", "values": tm_frac_refs,
             "lo": 0, "hi": 1},
            {"id": "tm-comp-counts-sum", "kind": "equal",
             "values": ["sum_count", "n_annotated"], "tol": 0},
            {"id": "tm-comp-N-eq-ncells", "kind": "equal",
             "values": ["n_annotated", {"claim": "claim-tm-shape", "key": "n_cells"}], "tol": 0},
            {"id": "tm-comp-ctb-max", "kind": "monotonic",
             "values": ["Stroma_count", "CTB_count"], "direction": "increasing"},
            {"id": "tm-comp-ctb-count-id", "kind": "expr", "lhs": "CTB_count",
             "rhs": "round(CTB_frac*n_annotated)", "tol": 1,
             "vars": {"CTB_count": "CTB_count", "CTB_frac": "CTB_frac",
                      "n_annotated": "n_annotated"}},
        ],
        "inputs": [tm_in],
        "outputs": [{"path": OUT}, {"path": OUT_TOT}],
        "search_terms": ["term placenta cell type composition trophoblast Hofbauer stroma"],
    },
]

print(json.dumps(claims, indent=2))
