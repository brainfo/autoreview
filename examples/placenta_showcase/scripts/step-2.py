"""Step 2: Data-state of each matrix (X, layers, raw) per dataset.

For each dataset we read a slice of the first N_SLICE rows (backed read, never
the full matrix) and compute, for X / each layer / raw.X:
  - min over all entries (sparse zeros included -> 0 if any structural zero)
  - max over nonzero entries
  - fraction of NONZERO entries that are non-integer (|v-round(v)| > 1e-4)
  - has_negative
  - a categorical state label.

We also record two cross-matrix equalities to ground the interpretation:
  term X vs term log1pM, and FT raw.X vs FT X (max abs diff on the slice).
Writes results/step-2_datastate.csv and emits claim JSON on stdout.
"""
import json
import sys
import anndata as ad
import numpy as np
import scipy.sparse as sp

FT = "/mnt/run/jh/projects/tes_agent/first_trimester_final.h5ad"
TM = "/mnt/run/jh/projects/tes_agent/term_final.h5ad"
OUT = "/mnt/run/jh/projects/tes_agent/results/step-2_datastate.csv"
N_SLICE = 2000
NONINT_TOL = 1e-4   # generous vs float32 noise; integers near 0 still resolve

FT_SHA = "85b09152b2be819023a0b8aa93557f9bc3eed793ed8df253491d651366354ce8"
TM_SHA = "888e0acd8a80c5de88a09bb2db3a69df60d94afa0019bb1e4202363842c8a0d3"


def _dense_data(mat):
    """Return (all_values_1d, nonzero_values_1d)."""
    if sp.issparse(mat):
        nz = np.asarray(mat.data, dtype=np.float64).ravel()
        # min over ALL entries: structural zeros present if nnz < size
        has_struct_zero = mat.nnz < (mat.shape[0] * mat.shape[1])
        allmin = min(0.0, float(nz.min())) if (has_struct_zero and nz.size) else \
            (float(nz.min()) if nz.size else 0.0)
        return nz, allmin
    arr = np.asarray(mat, dtype=np.float64).ravel()
    nz = arr[arr != 0]
    allmin = float(arr.min()) if arr.size else 0.0
    return nz, allmin


def profile(mat):
    nz, allmin = _dense_data(mat)
    if nz.size == 0:
        return dict(min=allmin, max_nonzero=0.0, frac_noninteger=0.0, has_negative=False)
    max_nz = float(nz.max())
    noninteger = np.abs(nz - np.round(nz)) > NONINT_TOL
    frac_ni = float(noninteger.mean())
    has_neg = bool((nz < 0).any())
    return dict(min=allmin, max_nonzero=max_nz, frac_noninteger=frac_ni,
                has_negative=has_neg)


def label_state(prof):
    if prof["has_negative"]:
        return "scaled_zscore"
    if prof["frac_noninteger"] == 0.0 and prof["min"] >= 0:
        return "raw_counts"
    if prof["frac_noninteger"] > 0.0 and not prof["has_negative"]:
        return "log_normalized"
    return "unknown"


rows = []


def add(dataset, matrix, prof):
    lab = label_state(prof)
    rows.append(dict(dataset=dataset, matrix=matrix, min=prof["min"],
                     max_nonzero=prof["max_nonzero"],
                     frac_noninteger=prof["frac_noninteger"],
                     has_negative=prof["has_negative"], state_label=lab))
    return lab, prof


# ---- First trimester ----
ft = ad.read_h5ad(FT, backed='r')
ft_sl = ft[0:N_SLICE]
ft_X = ft_sl.X[:]
ft_counts = ft_sl.layers["counts"][:]
ft_rawX = ft.raw[0:N_SLICE].X[:]
ft_X_prof = profile(ft_X)
ft_counts_prof = profile(ft_counts)
ft_raw_prof = profile(ft_rawX)
# equality raw.X vs X on the slice, aligned on the shared (HVG) gene namespace:
# X is the 5000 HVG subset of the 27526 raw genes, so compare on those columns.
ftXd = ft_X.toarray() if sp.issparse(ft_X) else np.asarray(ft_X)
ftRd = ft_rawX.toarray() if sp.issparse(ft_rawX) else np.asarray(ft_rawX)
x_genes = list(ft.var_names)
raw_genes = list(ft.raw.var_names)
raw_idx = {g: i for i, g in enumerate(raw_genes)}
shared = [g for g in x_genes if g in raw_idx]
ft_n_shared_x_raw = len(shared)
if ft_n_shared_x_raw == len(x_genes):
    cols_x = list(range(len(x_genes)))
    cols_raw = [raw_idx[g] for g in x_genes]
else:
    cols_x = [i for i, g in enumerate(x_genes) if g in raw_idx]
    cols_raw = [raw_idx[g] for g in x_genes if g in raw_idx]
ft_rawX_eq_X_maxdiff = float(np.abs(ftXd[:, cols_x] - ftRd[:, cols_raw]).max())
add("first_trimester", "X", ft_X_prof)
add("first_trimester", "counts", ft_counts_prof)
add("first_trimester", "raw.X", ft_raw_prof)
ft.file.close()

# ---- Term ----
tm = ad.read_h5ad(TM, backed='r')
tm_sl = tm[0:N_SLICE]
tm_X = tm_sl.X[:]
tm_counts = tm_sl.layers["counts"][:]
tm_log = tm_sl.layers["log1pM"][:]
tm_X_prof = profile(tm_X)
tm_counts_prof = profile(tm_counts)
tm_log_prof = profile(tm_log)
tmXd = tm_X.toarray() if sp.issparse(tm_X) else np.asarray(tm_X)
tmLd = tm_log.toarray() if sp.issparse(tm_log) else np.asarray(tm_log)
tm_X_eq_log_maxdiff = float(np.abs(tmXd - tmLd).max())
add("term", "X", tm_X_prof)
add("term", "counts", tm_counts_prof)
add("term", "log1pM", tm_log_prof)
tm.file.close()

import pandas as pd
df = pd.DataFrame(rows)
df.to_csv(OUT, index=False)
sys.stderr.write(df.to_string() + "\n")
sys.stderr.write(f"FT raw.X vs X maxdiff={ft_rawX_eq_X_maxdiff:g}; "
                 f"TERM X vs log1pM maxdiff={tm_X_eq_log_maxdiff:g}\n")

ft_in = {"path": FT, "sha256": FT_SHA}
tm_in = {"path": TM, "sha256": TM_SHA}

claims = [
    {
        "id": "claim-term-counts-raw",
        "type": "data+interpretation",
        "source": TM,
        "claim": (f"Term layers['counts'] contains genuine raw integer UMI counts "
                  f"(min={tm_counts_prof['min']:g}, max_nonzero={tm_counts_prof['max_nonzero']:g}, "
                  f"frac_noninteger={tm_counts_prof['frac_noninteger']:g}) whereas term X is "
                  f"log-normalized (frac_noninteger={tm_X_prof['frac_noninteger']:.4f}, "
                  f"has_negative={tm_X_prof['has_negative']}) and equals layers['log1pM'] "
                  f"(max abs diff {tm_X_eq_log_maxdiff:g} on the first {N_SLICE} cells)."),
        "interpretation": ("Term provides recoverable raw counts suitable for "
                           "re-normalization or pseudobulk; X is already log1p-normalized."),
        "numbers": {
            "n_slice": N_SLICE,
            "counts_min": tm_counts_prof["min"],
            "counts_max_nonzero": tm_counts_prof["max_nonzero"],
            "counts_frac_noninteger": tm_counts_prof["frac_noninteger"],
            "counts_has_negative": 1 if tm_counts_prof["has_negative"] else 0,
            "X_frac_noninteger": tm_X_prof["frac_noninteger"],
            "X_has_negative": 1 if tm_X_prof["has_negative"] else 0,
            "X_vs_log1pM_maxdiff": tm_X_eq_log_maxdiff,
        },
        "checks": [
            {"id": "tm-counts-int", "kind": "equal",
             "values": ["counts_frac_noninteger", 0.0], "tol": 0},
            {"id": "tm-counts-nonneg", "kind": "bounds", "values": ["counts_min"], "lo": 0},
            {"id": "tm-counts-no-neg", "kind": "equal",
             "values": ["counts_has_negative", 0], "tol": 0},
            {"id": "tm-X-noninteger", "kind": "bounds",
             "values": ["X_frac_noninteger"], "lo": 1e-6, "hi": 1.0},
            {"id": "tm-X-no-neg", "kind": "equal", "values": ["X_has_negative", 0], "tol": 0},
            {"id": "tm-X-eq-log1pM", "kind": "bounds",
             "values": ["X_vs_log1pM_maxdiff"], "lo": 0, "hi": 1e-3},
        ],
        "inputs": [tm_in],
        "outputs": [{"path": OUT}],
        "search_terms": ["raw UMI counts log1p normalization scRNA-seq",
                         "anndata layers counts log-normalized X"],
    },
    {
        "id": "claim-ft-counts-not-raw",
        "type": "data+interpretation",
        "source": FT,
        "claim": (f"First trimester has NO genuine raw counts: X "
                  f"(frac_noninteger={ft_X_prof['frac_noninteger']:.4f}), layers['counts'] "
                  f"(frac_noninteger={ft_counts_prof['frac_noninteger']:.4f}, "
                  f"min={ft_counts_prof['min']:g}) and raw.X "
                  f"(frac_noninteger={ft_raw_prof['frac_noninteger']:.4f}) are all "
                  f"non-integer and non-negative; raw.X equals X on the shared "
                  f"{ft_n_shared_x_raw} HVG (max abs diff {ft_rawX_eq_X_maxdiff:g}). "
                  f"So the 'counts' layer is misnamed relative to term."),
        "interpretation": ("Pseudobulk/DE that assumes integer counts cannot be done "
                           "directly on first trimester; the two datasets are NOT symmetric "
                           "in available raw data, a key caveat for any cross-dataset "
                           "quantitative comparison."),
        "numbers": {
            "n_slice": N_SLICE,
            "X_frac_noninteger": ft_X_prof["frac_noninteger"],
            "X_has_negative": 1 if ft_X_prof["has_negative"] else 0,
            "counts_frac_noninteger": ft_counts_prof["frac_noninteger"],
            "counts_min": ft_counts_prof["min"],
            "counts_has_negative": 1 if ft_counts_prof["has_negative"] else 0,
            "rawX_frac_noninteger": ft_raw_prof["frac_noninteger"],
            "rawX_has_negative": 1 if ft_raw_prof["has_negative"] else 0,
            "rawX_vs_X_maxdiff": ft_rawX_eq_X_maxdiff,
            "n_shared_x_raw": ft_n_shared_x_raw,
            "term_counts_frac_noninteger": tm_counts_prof["frac_noninteger"],
        },
        "checks": [
            {"id": "ft-counts-noninteger", "kind": "bounds",
             "values": ["counts_frac_noninteger"], "lo": 1e-6, "hi": 1.0},
            {"id": "ft-X-noninteger", "kind": "bounds",
             "values": ["X_frac_noninteger"], "lo": 1e-6, "hi": 1.0},
            {"id": "ft-rawX-noninteger", "kind": "bounds",
             "values": ["rawX_frac_noninteger"], "lo": 1e-6, "hi": 1.0},
            {"id": "ft-X-no-neg", "kind": "equal", "values": ["X_has_negative", 0], "tol": 0},
            {"id": "ft-counts-no-neg", "kind": "equal",
             "values": ["counts_has_negative", 0], "tol": 0},
            {"id": "ft-rawX-no-neg", "kind": "equal",
             "values": ["rawX_has_negative", 0], "tol": 0},
            {"id": "ft-rawX-eq-X", "kind": "bounds",
             "values": ["rawX_vs_X_maxdiff"], "lo": 0, "hi": 1e-3},
            {"id": "asymmetry-term-int-ft-not", "kind": "equal",
             "values": ["term_counts_frac_noninteger", 0.0], "tol": 0},
        ],
        "inputs": [ft_in, tm_in],
        "outputs": [{"path": OUT}],
        "search_terms": ["log-normalized data mistaken for raw counts scRNA-seq",
                         "non-integer counts layer placenta atlas pseudobulk caveat"],
    },
]

print(json.dumps(claims, indent=2))
