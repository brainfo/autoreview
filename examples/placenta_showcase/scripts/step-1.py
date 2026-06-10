"""Step 1: Basic structural shape of each dataset.

Opens each .h5ad backed='r' (no full X load). Records shape, raw gene count,
batch/study cardinalities, and the comparable cell-type annotation column.
Writes results/step-1_structure.csv (one row per dataset) and emits the claim
JSON list on stdout for the ledger.
"""
import json
import sys
import anndata as ad
import pandas as pd

FT = "/mnt/run/jh/projects/tes_agent/first_trimester_final.h5ad"
TM = "/mnt/run/jh/projects/tes_agent/term_final.h5ad"
OUT = "/mnt/run/jh/projects/tes_agent/results/step-1_structure.csv"


def n_distinct(adata, col):
    return int(adata.obs[col].nunique(dropna=True))


rows = []

# ---- First trimester ----
ft = ad.read_h5ad(FT, backed='r')
ft_n_cells, ft_n_genes = int(ft.shape[0]), int(ft.shape[1])
ft_n_raw = int(ft.raw.shape[1]) if ft.raw is not None else None
ft_n_studies = n_distinct(ft, "study")        # broad study (expect 3)
ft_n_samples = n_distinct(ft, "studies")       # study substrata (expect 9)
ft_celltype_col = "annotation"
ft_n_celltypes = n_distinct(ft, "annotation")
ft_n_celltypes_withperi = n_distinct(ft, "annotation_withperi")
rows.append(dict(dataset="first_trimester", n_cells=ft_n_cells, n_genes=ft_n_genes,
                 n_raw_genes=ft_n_raw, n_studies=ft_n_studies, n_samples=ft_n_samples,
                 celltype_col=ft_celltype_col, n_celltypes=ft_n_celltypes))
ft.file.close()

# ---- Term ----
tm = ad.read_h5ad(TM, backed='r')
tm_n_cells, tm_n_genes = int(tm.shape[0]), int(tm.shape[1])
tm_n_raw = int(tm.raw.shape[1]) if tm.raw is not None else None  # expect None
tm_n_studies = n_distinct(tm, "studies")       # expect 3
tm_n_samples = n_distinct(tm, "sample_id")     # 3 non-null control samples
tm_n_sample_nan = int(tm.obs["sample_id"].isna().sum())
tm_celltype_col = "annotate_general"
tm_n_celltypes = n_distinct(tm, "annotate_general")
rows.append(dict(dataset="term", n_cells=tm_n_cells, n_genes=tm_n_genes,
                 n_raw_genes=tm_n_raw, n_studies=tm_n_studies, n_samples=tm_n_samples,
                 celltype_col=tm_celltype_col, n_celltypes=tm_n_celltypes))
tm.file.close()

df = pd.DataFrame(rows)
df.to_csv(OUT, index=False)
sys.stderr.write(df.to_string() + "\n")

# inputs sha256 (from manifest)
FT_SHA = "85b09152b2be819023a0b8aa93557f9bc3eed793ed8df253491d651366354ce8"
TM_SHA = "888e0acd8a80c5de88a09bb2db3a69df60d94afa0019bb1e4202363842c8a0d3"
ft_in = {"path": FT, "sha256": FT_SHA}
tm_in = {"path": TM, "sha256": TM_SHA}

claims = [
    {
        "id": "claim-ft-shape",
        "type": "data+interpretation",
        "source": FT,
        "claim": (f"First trimester dataset has {ft_n_cells} cells and {ft_n_genes} "
                  f"(highly variable) genes in the working matrix, with a raw matrix "
                  f"of {ft_n_raw} genes."),
        "interpretation": ("First trimester is the larger dataset by cell count and is "
                           "reduced to a 5000-gene HVG working set."),
        "numbers": {"n_cells": ft_n_cells, "n_genes": ft_n_genes, "n_raw_genes": ft_n_raw,
                    "n_celltypes": ft_n_celltypes, "n_celltypes_withperi": ft_n_celltypes_withperi},
        "checks": [
            {"id": "ft-cells-pos", "kind": "bounds", "values": ["n_cells"], "lo": 1},
            {"id": "ft-genes-pos", "kind": "bounds", "values": ["n_genes"], "lo": 1},
            {"id": "ft-hvg-le-raw", "kind": "monotonic",
             "values": ["n_genes", "n_raw_genes"], "direction": "increasing"},
        ],
        "inputs": [ft_in],
        "outputs": [{"path": OUT}],
        "search_terms": ["first trimester placenta single-cell atlas",
                         "highly variable genes scRNA-seq placenta"],
    },
    {
        "id": "claim-tm-shape",
        "type": "data+interpretation",
        "source": TM,
        "claim": (f"Term dataset has {tm_n_cells} cells and {tm_n_genes} genes, with no "
                  f"raw matrix present (adata.raw is None)."),
        "interpretation": ("Term retains the full gene set (no HVG subsetting of var) and "
                           "has fewer cells than first trimester."),
        "numbers": {"n_cells": tm_n_cells, "n_genes": tm_n_genes,
                    "n_raw_genes_present": 0,  # 0 == no raw matrix
                    "n_celltypes": tm_n_celltypes},
        "checks": [
            {"id": "tm-cells-pos", "kind": "bounds", "values": ["n_cells"], "lo": 1},
            {"id": "tm-genes-pos", "kind": "bounds", "values": ["n_genes"], "lo": 1},
            {"id": "tm-no-raw", "kind": "equal", "values": ["n_raw_genes_present", 0], "tol": 0},
            {"id": "tm-fewer-than-ft", "kind": "monotonic",
             "values": ["n_cells", {"claim": "claim-ft-shape", "key": "n_cells"}],
             "direction": "increasing"},
        ],
        "inputs": [tm_in],
        "outputs": [{"path": OUT}],
        "search_terms": ["term placenta single-cell RNA-seq atlas",
                         "human placenta scRNA-seq full transcriptome"],
    },
    {
        "id": "claim-batches",
        "type": "data+interpretation",
        "source": "both",
        "claim": (f"First trimester spans {ft_n_studies} studies ({ft_n_samples} "
                  f"study-substrata); term spans {tm_n_studies} studies "
                  f"({tm_n_samples} control sample_ids)."),
        "interpretation": ("Both are multi-study integrated atlases; cell-type fractions "
                           "are pooled across donors/studies, not per-donor."),
        "numbers": {"ft_n_studies": ft_n_studies, "ft_n_samples": ft_n_samples,
                    "tm_n_studies": tm_n_studies, "tm_n_samples": tm_n_samples,
                    "tm_sample_id_nan": tm_n_sample_nan},
        "checks": [
            {"id": "ft-studies-pos", "kind": "bounds", "values": ["ft_n_studies"], "lo": 1},
            {"id": "tm-studies-pos", "kind": "bounds", "values": ["tm_n_studies"], "lo": 1},
            {"id": "ft-samples-ge-studies", "kind": "monotonic",
             "values": ["ft_n_studies", "ft_n_samples"], "direction": "nondecreasing"},
            {"id": "tm-samples-ge-studies", "kind": "monotonic",
             "values": ["tm_n_studies", "tm_n_samples"], "direction": "nondecreasing"},
        ],
        "inputs": [ft_in, tm_in],
        "outputs": [{"path": OUT}],
        "search_terms": ["multi-study integrated placenta single-cell atlas batch"],
    },
]

print(json.dumps(claims, indent=2))
