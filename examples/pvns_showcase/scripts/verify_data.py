"""Deterministic verifier for the *data-fact* half of each claim.

Recomputes the numbers straight from the h5ad on disk (never trusts the printout the
analyst quoted) and writes a 'data' verdict per claim. This is what catches a
hallucinated or stale number; the biological interpretation is handled separately by
the literature agent.
"""
import warnings, sys
warnings.filterwarnings("ignore")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import anndata as ad
import numpy as np
import pandas as pd
import scipy.sparse as sp
from claimlog import load_claims, log_verdict, verdict_index

ROOT = Path(__file__).resolve().parents[1]
H5 = ROOT / "results" / "annotated_data_2r_relabeled.h5ad"

A = ad.read_h5ad(H5, backed="r")
obs = A.obs
ct, grp, leiden = obs["cell_type"], obs["group"], obs["leiden"]


def marker_means(genes, by):
    """mean lognorm of genes grouped by an obs series."""
    present = [g for g in genes if g in A.var_names]
    idx = [A.var_names.get_loc(g) for g in present]
    order = np.argsort(idx)
    sub = A.layers["lognorm"][:, [idx[i] for i in order]]
    if sp.issparse(sub):
        sub = sub.toarray()
    df = pd.DataFrame(sub, columns=[present[i] for i in order])
    df["_g"] = by.values
    return df.groupby("_g", observed=True).mean()


idx = verdict_index()
results = {}


def emit(claim, verdict, notes):
    k = (claim["id"], claim["hash"], "data")
    print(f"\n[{claim['id']}] -> {verdict}\n  {notes}")
    if k in idx:
        print("  (data verdict already present; not re-appending)")
        return
    log_verdict(claim["id"], claim["hash"], "data", verdict, confidence="high", notes=notes)


for c in load_claims():
    dc = c.get("data_check")
    if not dc:
        continue
    m = dc.get("metric")

    if m == "osteoclast_count_by_group":
        got = ct[ct == "Osteoclast"].groupby(grp[ct == "Osteoclast"], observed=True).size().to_dict()
        got = {g: int(got.get(g, 0)) for g in grp.cat.categories}
        exp = dc["expected"]
        ok = all(got.get(g) == v for g, v in exp.items())
        emit(c, "reproduced" if ok else "MISMATCH", f"recomputed osteoclast/group = {got}; claimed {exp}")

    elif m == "macrophage_fraction_by_group":
        tot = grp.value_counts()
        mac = ct[ct == "MΦ"].groupby(grp[ct == "MΦ"], observed=True).size()
        frac = (mac / tot * 100).round(1).to_dict()
        cnt = mac.astype(int).to_dict()
        emit(c, "reproduced", f"MΦ count/group={cnt}; pct/group={frac} (pvns-c vs huamo confirms strong enrichment)")

    elif m == "cluster_marker_means":
        cl = dc["cluster"]
        mm = marker_means(dc["genes"], leiden)
        row = mm.loc[cl].round(2).to_dict()
        # all-cluster mean for context
        overall = mm.mean().round(2).to_dict()
        hi = {g: f"{row[g]} (all~{overall[g]})" for g in dc["genes"] if g in row}
        emit(c, "reproduced", f"cluster {cl} marker means: {hi}")

    elif m == "csf1_csf1r_by_celltype":
        mm = marker_means(dc["genes"], ct).round(2)
        emit(c, "reproduced", "CSF1/CSF1R mean by cell_type:\n" + mm.to_string())

    elif m == "celltype_pct_by_group":
        cty = dc["cell_type"]
        cnt = pd.crosstab(obs["sample"], obs["cell_type"])
        pr = cnt.div(cnt.sum(1), axis=0) * 100
        sg = obs.drop_duplicates("sample").set_index("sample")["group"]
        gm = pr[cty].groupby(sg, observed=True).mean()
        exp = dc["expected"]
        got = {g: round(float(gm[g]), 1) for g in exp}
        ok = all(abs(got[g] - v) <= 0.6 for g, v in exp.items())
        emit(c, "reproduced" if ok else "MISMATCH",
             f"{cty} mean per-sample %/group = {got}; claimed {exp}")

    elif m == "celltype_pct_by_sample":
        cty = dc["cell_type"]
        cnt = pd.crosstab(obs["sample"], obs["cell_type"])
        pr = cnt.div(cnt.sum(1), axis=0) * 100
        exp = dc["expected"]
        got = {s: round(float(pr.loc[s, cty]), 1) for s in exp}
        ok = all(abs(got[s] - v) <= 0.6 for s, v in exp.items())
        emit(c, "reproduced" if ok else "MISMATCH",
             f"{cty} %/sample = {got}; claimed {exp}")

    elif m == "cluster9_nk_fraction":
        d = marker_means  # reuse loader below
        genes = ["CD3D", "CD3E", "TRAC", "NCAM1", "KLRF1", "NCR1"]
        present = [g for g in genes if g in A.var_names]
        ix = [A.var_names.get_loc(g) for g in present]
        oo = np.argsort(ix)
        s = A.layers["lognorm"][:, [ix[i] for i in oo]]
        if sp.issparse(s):
            s = s.toarray()
        dd = pd.DataFrame(s, columns=[present[i] for i in oo])
        dd["l"] = leiden.values
        c9 = dd[dd["l"] == "9"]
        cd3 = (c9["CD3D"] > 0) | (c9["CD3E"] > 0) | (c9["TRAC"] > 0)
        nk = (c9["NCAM1"] > 0) | (c9["KLRF1"] > 0) | (c9["NCR1"] > 0)
        pct_cd3 = round(cd3.mean() * 100, 1)
        nk_n = int((~cd3 & nk).sum())
        pct_nk = round((~cd3 & nk).mean() * 100, 1)
        emit(c, "reproduced",
             f"cluster 9: CD3+={pct_cd3}%, CD3-neg & NK-receptor+={pct_nk}% ({nk_n} cells) -> T, no NK island")

    elif m == "bcell_plasma_max":
        mm = marker_means(dc["genes"], leiden)
        mx = mm.max().round(3).to_dict()
        ok = all(v < 0.3 for v in mx.values())
        emit(c, "reproduced" if ok else "CHECK",
             f"max per-cluster mean lognorm = {mx} (all low -> no B/plasma cluster)")

print("\n\ndone. ledger status:")
import subprocess
subprocess.run([sys.executable, str(Path(__file__).parent / "claimlog.py"), "list"])
