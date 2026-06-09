"""Log the composition + treatment-rescue conclusions as tracked claims.
huamo=control, pvns-c=untreated PVNS, pvns-l=photodynamic-treated. Idempotent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from claimlog import log_claim

COMP = "results/composition/diffabund_stats.csv"
RESC = "results/rescue/rescue_summary.csv"

log_claim(
    id="composition-mac-rescue", ctype="data+interpretation", source=COMP,
    claim="Macrophage proportion (mean of per-sample %) rises from 7.1% in control to 41.4% in untreated PVNS and falls to 11.9% in photodynamic-treated PVNS - i.e. the macrophage expansion is largely normalised by treatment.",
    bio_assertion="Reduction of the expanded macrophage infiltrate back toward normal synovium is the expected signature of an effective PVNS/TGCT therapy, mirroring the mechanism of CSF1/CSF1R-targeted treatment.",
    data_check={"metric": "celltype_pct_by_group", "cell_type": "MΦ",
                "expected": {"huamo": 7.1, "pvns-c": 41.4, "pvns-l": 11.9}},
    search_terms=["PVNS TGCT treatment reduces macrophage infiltrate", "CSF1R inhibitor TGCT macrophage depletion response"],
)

log_claim(
    id="composition-osteoclast-rescue", ctype="data+interpretation", source=COMP,
    claim="Osteoclasts are absent in control (0%), induced in untreated PVNS (1.25%) and reduced ~77% by photodynamic treatment (0.29%).",
    bio_assertion="Loss of osteoclast-like giant cells indicates regression of the PVNS/TGCT lesion, since these cells are a disease hallmark absent from normal synovium.",
    data_check={"metric": "celltype_pct_by_group", "cell_type": "Osteoclast",
                "expected": {"huamo": 0.0, "pvns-c": 1.25, "pvns-l": 0.29}},
    search_terms=["tenosynovial giant cell tumor treatment giant cell reduction", "PVNS osteoclast-like giant cell regression therapy"],
)

log_claim(
    id="pvns-c3-outlier", ctype="data+interpretation", source="results/composition/proportions_per_sample.csv",
    claim="Sample pvns-c3 is a compositional outlier within the disease group: only 6.9% macrophages vs 69.5% (pvns-c) and 47.8% (pvns-c2), making it control-like and inflating disease-group variance.",
    bio_assertion="PVNS/TGCT lesions are spatially heterogeneous, so a single biopsy can under-sample the macrophage-rich tumour and appear stroma-dominated - a known sampling caveat rather than necessarily a technical failure.",
    data_check={"metric": "celltype_pct_by_sample", "cell_type": "MΦ",
                "expected": {"pvns-c": 69.5, "pvns-c2": 47.8, "pvns-c3": 6.9}},
    search_terms=["tenosynovial giant cell tumor intratumoral heterogeneity", "PVNS biopsy sampling heterogeneity histology"],
)

log_claim(
    id="global-directional-rescue", ctype="data+interpretation", source=RESC,
    claim="Across cell types, disease-altered genes reverse direction under treatment far above chance (macrophages 67.3% opposite, sign-test p=3e-9; fibroblasts 80.7%, p~1e-47), evidencing a global transcriptional rescue despite limited per-gene power.",
    bio_assertion="An effective therapy is expected to reverse the disease transcriptional program direction across genes; a genome-wide directional reversal (sign test) is a valid readout when individual genes are underpowered.",
    data_check=None,
    search_terms=["reversal of disease gene signature treatment connectivity", "sign test directional concordance differential expression rescue"],
)

log_claim(
    id="treatment-own-signature", ctype="data+interpretation", source="results/DEGs_pseudobulk/dge_summary.csv",
    claim="Treated vs control still differs in many genes (e.g. 730 DEGs in macrophages), so photodynamic treatment does not fully restore the control transcriptome - it imposes its own signature on top of partial disease reversal.",
    bio_assertion="Photodynamic therapy generates reactive oxygen species and induces oxidative-stress, cell-death and inflammatory transcriptional programs, producing a treatment-specific signature distinct from untreated tissue.",
    data_check=None,
    search_terms=["photodynamic therapy oxidative stress transcriptional response", "PDT reactive oxygen species gene expression cell death"],
)

log_claim(
    id="ambient-myeloid-in-nonmyeloid", ctype="data+interpretation", source="results/rescue/genes_of_interest_status.csv",
    claim="Macrophage markers (CD163, MARCO, AIF1, C1QB, MMP9) appear as disease-up genes in the fibroblast, EC and T pseudobulks, consistent with ambient-RNA / contamination from the massive macrophage expansion rather than genuine expression by those cell types.",
    bio_assertion="Ambient (cell-free) RNA contamination in droplet scRNA-seq causes highly expressed genes from an abundant cell type to appear in other cell types' profiles, especially when that cell type dominates the sample.",
    data_check=None,
    search_terms=["ambient RNA contamination single cell droplet SoupX", "scRNA-seq ambient RNA highly expressed genes cross-contamination"],
)

print("logged rescue/composition claims; status:")
import subprocess
subprocess.run([sys.executable, str(Path(__file__).parent / "claimlog.py"), "list"])
