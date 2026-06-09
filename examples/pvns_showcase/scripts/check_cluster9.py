"""Is leiden cluster 9 a true T+NK mixture or cytotoxic T cells? Look for a
CD3-negative NK island (NCAM1/KLRF1/NCR1/FCGR3A+ without CD3D/E/TRAC)."""
import warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import anndata as ad, numpy as np, pandas as pd, scipy.sparse as sp

ROOT = Path(__file__).resolve().parents[1]
A = ad.read_h5ad(ROOT / "results" / "annotated_data_2r_relabeled.h5ad", backed="r")
genes = ["CD3D","CD3E","TRAC","CD8A","NKG7","GNLY","KLRD1","NCAM1","KLRF1","NCR1","FCGR3A"]
present = [g for g in genes if g in A.var_names]
idx = [A.var_names.get_loc(g) for g in present]
o = np.argsort(idx)
sub = A.layers["lognorm"][:, [idx[i] for i in o]]
if sp.issparse(sub): sub = sub.toarray()
df = pd.DataFrame(sub, columns=[present[i] for i in o])
df["leiden"] = A.obs["leiden"].values
c9 = df[df["leiden"] == "9"].drop(columns="leiden")
n = len(c9)
print(f"cluster 9: {n} cells")
print("\nmean lognorm (cluster 9):")
print(c9.mean().round(3).to_string())

cd3 = (c9.get("CD3D",0)>0) | (c9.get("CD3E",0)>0) | (c9.get("TRAC",0)>0)
nkpos = (c9.get("NCAM1",0)>0) | (c9.get("KLRF1",0)>0) | (c9.get("NCR1",0)>0)
print(f"\nCD3+ (any of CD3D/E/TRAC > 0):        {cd3.mean()*100:5.1f}%")
print(f"CD3-negative:                         {(~cd3).mean()*100:5.1f}%")
print(f"CD3-neg & NK-receptor+ (NCAM1/KLRF1/NCR1): {(~cd3 & nkpos).mean()*100:5.1f}%  ({int((~cd3&nkpos).sum())} cells)")
print(f"  -> putative true-NK fraction of cluster 9")
