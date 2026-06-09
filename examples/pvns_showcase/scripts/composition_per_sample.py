"""Per-sample cell-type composition (correct unit for differential-abundance reporting:
proportions per SAMPLE, then summarised per group - not pooled cells)."""
import warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import anndata as ad, pandas as pd, numpy as np
pd.set_option("display.width", 200); pd.set_option("display.max_columns", 30)

ROOT = Path(__file__).resolve().parents[1]
A = ad.read_h5ad(ROOT / "results" / "annotated_data_2r_relabeled.h5ad", backed="r")
obs = A.obs[["sample", "group", "cell_type"]].copy()

order = ["EC", "Fb", "Mural", "MΦ", "Osteoclast", "MC", "T"]
gorder = ["huamo", "pvns-c", "pvns-l"]

# per-sample proportions (%)
ct = pd.crosstab(obs["sample"], obs["cell_type"], normalize="index")[order] * 100
samp_group = obs.drop_duplicates("sample").set_index("sample")["group"]
ct["group"] = samp_group
ct = ct.sort_values("group")
print("=== per-sample cell-type proportions (%) ===")
print(ct.round(1).to_string())

print("\n=== group mean +/- SD across the 3 samples (%) ===")
g = ct.groupby("group", observed=True)[order]
mean = g.mean().reindex(gorder).round(1)
sd = g.std().reindex(gorder).round(1)
combined = mean.astype(str) + " ± " + sd.astype(str)
print(combined.to_string())

print("\n=== disease-associated types: per-sample %, to check rescue ordering ===")
for cty in ["MΦ", "Osteoclast", "Mural"]:
    print(f"\n{cty}:")
    for grp in gorder:
        vals = ct[ct["group"] == grp][cty].round(1).tolist()
        print(f"  {grp:8s}: {vals}  mean={np.mean(vals):.1f}")
