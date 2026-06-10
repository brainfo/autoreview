"""Step 5: Shared vs dataset-specific genes and cell-type labels.

Gene overlap:
  - hvg_vs_term:  |FT var (5000 HVG)| vs |term var (25777)|, intersection.
  - raw_vs_term:  |FT raw var (27526)| vs |term var (25777)|, intersection, Jaccard.
Label overlap (after the Hofbaucer->Hofbauer typo normalization from step-4):
  FT 'annotation_withperi' set vs term 'annotate_general' set.
Writes results/step-5_gene_overlap.csv and results/step-5_label_overlap.csv.
Emits claim JSON on stdout.
"""
import json
import sys
import anndata as ad
import pandas as pd

FT = "/mnt/run/jh/projects/tes_agent/first_trimester_final.h5ad"
TM = "/mnt/run/jh/projects/tes_agent/term_final.h5ad"
OUT_G = "/mnt/run/jh/projects/tes_agent/results/step-5_gene_overlap.csv"
OUT_L = "/mnt/run/jh/projects/tes_agent/results/step-5_label_overlap.csv"

FT_SHA = "85b09152b2be819023a0b8aa93557f9bc3eed793ed8df253491d651366354ce8"
TM_SHA = "888e0acd8a80c5de88a09bb2db3a69df60d94afa0019bb1e4202363842c8a0d3"

TYPO_MAP = {"Hofbaucer cells": "Hofbauer cells"}

ft = ad.read_h5ad(FT, backed='r')
ft_var = set(map(str, ft.var_names))
ft_raw_var = set(map(str, ft.raw.var_names))
ft_peri = set(map(str, ft.obs["annotation_withperi"].dropna().unique()))
ft.file.close()

tm = ad.read_h5ad(TM, backed='r')
tm_var = set(map(str, tm.var_names))
tm_gen_raw = set(map(str, tm.obs["annotate_general"].dropna().unique()))
tm.file.close()

# normalize term labels
tm_gen = {TYPO_MAP.get(x, x) for x in tm_gen_raw}


def overlap_row(name, a, b):
    inter = a & b
    union = a | b
    return dict(comparison=name, n_set_a=len(a), n_set_b=len(b),
                n_intersection=len(inter), n_union=len(union),
                jaccard=len(inter) / len(union) if union else 0.0)


g_rows = [
    overlap_row("hvg_vs_term", ft_var, tm_var),
    overlap_row("raw_vs_term", ft_raw_var, tm_var),
]
gdf = pd.DataFrame(g_rows)
gdf.to_csv(OUT_G, index=False)

# label overlap
all_labels = sorted(ft_peri | tm_gen)
l_rows = []
for lab in all_labels:
    in_ft = lab in ft_peri
    in_tm = lab in tm_gen
    l_rows.append(dict(label=lab, in_first_trimester=in_ft, in_term=in_tm,
                       shared=(in_ft and in_tm)))
ldf = pd.DataFrame(l_rows)
ldf.to_csv(OUT_L, index=False)

sys.stderr.write(gdf.to_string() + "\n\n" + ldf.to_string() + "\n")
sys.stderr.write(f"\nFT peri labels: {sorted(ft_peri)}\n"
                 f"TM general raw labels: {sorted(tm_gen_raw)}\n"
                 f"TM general normalized: {sorted(tm_gen)}\n")

hvg = g_rows[0]
raw = g_rows[1]
n_shared_labels = int(ldf["shared"].sum())
n_ft_only = int(((ldf["in_first_trimester"]) & (~ldf["in_term"])).sum())
n_tm_only = int(((~ldf["in_first_trimester"]) & (ldf["in_term"])).sum())

ft_in = {"path": FT, "sha256": FT_SHA}
tm_in = {"path": TM, "sha256": TM_SHA}

claims = [
    {
        "id": "claim-gene-overlap",
        "type": "data+interpretation",
        "source": "both",
        "claim": (f"The first-trimester 5000-gene HVG set overlaps term's "
                  f"{hvg['n_set_b']} genes in {hvg['n_intersection']} genes; using "
                  f"first-trimester's full raw gene set ({raw['n_set_a']}) the overlap "
                  f"with term is {raw['n_intersection']} genes "
                  f"(Jaccard {raw['jaccard']:.4f})."),
        "interpretation": ("The datasets use largely overlapping but non-identical gene "
                           "namespaces; the working-matrix overlap is limited because first "
                           "trimester is HVG-subset, so cross-dataset gene-level analysis "
                           "should use the raw/full namespaces."),
        "numbers": {
            "hvg_n_set_a": hvg["n_set_a"], "hvg_n_set_b": hvg["n_set_b"],
            "hvg_n_intersection": hvg["n_intersection"], "hvg_n_union": hvg["n_union"],
            "hvg_jaccard": hvg["jaccard"],
            "raw_n_set_a": raw["n_set_a"], "raw_n_set_b": raw["n_set_b"],
            "raw_n_intersection": raw["n_intersection"], "raw_n_union": raw["n_union"],
            "raw_jaccard": raw["jaccard"],
        },
        "checks": [
            {"id": "hvg-inter-le-a", "kind": "monotonic",
             "values": ["hvg_n_intersection", "hvg_n_set_a"], "direction": "nondecreasing"},
            {"id": "hvg-inter-le-b", "kind": "monotonic",
             "values": ["hvg_n_intersection", "hvg_n_set_b"], "direction": "nondecreasing"},
            {"id": "raw-inter-le-a", "kind": "monotonic",
             "values": ["raw_n_intersection", "raw_n_set_a"], "direction": "nondecreasing"},
            {"id": "raw-inter-le-b", "kind": "monotonic",
             "values": ["raw_n_intersection", "raw_n_set_b"], "direction": "nondecreasing"},
            {"id": "hvg-union-id", "kind": "expr", "lhs": "n_union",
             "rhs": "a + b - inter", "tol": 0,
             "vars": {"n_union": "hvg_n_union", "a": "hvg_n_set_a", "b": "hvg_n_set_b",
                      "inter": "hvg_n_intersection"}},
            {"id": "raw-union-id", "kind": "expr", "lhs": "n_union",
             "rhs": "a + b - inter", "tol": 0,
             "vars": {"n_union": "raw_n_union", "a": "raw_n_set_a", "b": "raw_n_set_b",
                      "inter": "raw_n_intersection"}},
            {"id": "hvg-jaccard-id", "kind": "expr", "lhs": "jaccard",
             "rhs": "inter / n_union", "tol": 1e-9,
             "vars": {"jaccard": "hvg_jaccard", "inter": "hvg_n_intersection",
                      "n_union": "hvg_n_union"}},
            {"id": "raw-jaccard-id", "kind": "expr", "lhs": "jaccard",
             "rhs": "inter / n_union", "tol": 1e-9,
             "vars": {"jaccard": "raw_jaccard", "inter": "raw_n_intersection",
                      "n_union": "raw_n_union"}},
            {"id": "jaccard-bounds", "kind": "bounds",
             "values": ["hvg_jaccard", "raw_jaccard"], "lo": 0, "hi": 1},
            {"id": "raw-inter-ge-hvg-inter", "kind": "monotonic",
             "values": ["hvg_n_intersection", "raw_n_intersection"], "direction": "increasing"},
        ],
        "inputs": [ft_in, tm_in],
        "outputs": [{"path": OUT_G}],
        "search_terms": ["gene namespace overlap two single-cell atlases highly variable genes"],
    },
    {
        "id": "claim-label-overlap",
        "type": "data+interpretation",
        "source": "both",
        "claim": (f"After normalizing the Hofbauer spelling, the comparable cell-type "
                  f"label sets are fully shared between first trimester "
                  f"(annotation_withperi) and term (annotate_general): "
                  f"n_shared={n_shared_labels}, ft_only={n_ft_only}, term_only={n_tm_only}; "
                  f"shared labels = {sorted(ft_peri & tm_gen)}."),
        "interpretation": ("The two atlases were annotated onto a common 7-compartment "
                           "scheme, which is what makes the step-4 compositional comparison "
                           "valid."),
        "numbers": {
            "n_shared": n_shared_labels,
            "n_ft_only": n_ft_only,
            "n_term_only": n_tm_only,
            "n_ft_labels": len(ft_peri),
            "n_tm_labels": len(tm_gen),
            "shift_n_shared": 7,  # the shared set used by step-4 (cross-check)
        },
        "checks": [
            {"id": "label-ft-partition", "kind": "expr", "lhs": "ft_only + shared",
             "rhs": "n_ft_labels", "tol": 0,
             "vars": {"ft_only": "n_ft_only", "shared": "n_shared", "n_ft_labels": "n_ft_labels"}},
            {"id": "label-tm-partition", "kind": "expr", "lhs": "tm_only + shared",
             "rhs": "n_tm_labels", "tol": 0,
             "vars": {"tm_only": "n_term_only", "shared": "n_shared", "n_tm_labels": "n_tm_labels"}},
            {"id": "label-ft-only-zero", "kind": "equal", "values": ["n_ft_only", 0], "tol": 0},
            {"id": "label-tm-only-zero", "kind": "equal", "values": ["n_term_only", 0], "tol": 0},
            {"id": "label-shared-7", "kind": "equal", "values": ["n_shared", 7], "tol": 0},
            {"id": "label-matches-step4", "kind": "equal",
             "values": ["n_shared", {"claim": "claim-shift-conservation", "key": "n_shared"}],
             "tol": 0},
        ],
        "inputs": [ft_in, tm_in],
        "outputs": [{"path": OUT_L}],
        "search_terms": ["common cell type annotation scheme placenta compartments"],
    },
]

print(json.dumps(claims, indent=2))
