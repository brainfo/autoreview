"""Seed the ledger with the claims made during the annotation review of
results/annotated_data_2r_relabeled.h5ad. Re-running is idempotent.

Going forward, analysis scripts should call claimlog.log_claim(...) directly so claims
are captured at the moment they are made instead of being re-typed here.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from claimlog import log_claim

SRC = "results/annotated_data_2r_relabeled.h5ad"

log_claim(
    id="osteoclast-pvns-specificity", ctype="data+interpretation", source=SRC,
    claim="Osteoclast cluster is essentially PVNS-only: 407 cells in pvns-c, 101 in pvns-l, 0 in huamo (control).",
    bio_assertion="Osteoclast-like multinucleated giant cells are a hallmark of PVNS / tenosynovial giant cell tumour (TGCT) and are largely absent from normal/control synovium.",
    data_check={"metric": "osteoclast_count_by_group", "expected": {"pvns-c": 407, "pvns-l": 101, "huamo": 0}},
    search_terms=["pigmented villonodular synovitis osteoclast-like giant cells",
                  "tenosynovial giant cell tumor osteoclast differentiation",
                  "TGCT multinucleated giant cells normal synovium"],
)

log_claim(
    id="osteoclast-marker-signature", ctype="data+interpretation", source=SRC,
    claim="Leiden cluster 15 expresses MMP9, ACP5 (TRAP), CTSK and CSF1R highly, identifying it as osteoclasts / osteoclast-like giant cells.",
    bio_assertion="MMP9, ACP5/TRAP, cathepsin K (CTSK) and CSF1R are canonical markers of osteoclasts and osteoclast-like giant cells.",
    data_check={"metric": "cluster_marker_means", "cluster": "15",
                "genes": ["MMP9", "ACP5", "CTSK", "CSF1R"]},
    search_terms=["osteoclast markers ACP5 cathepsin K MMP9 CSF1R", "TRAP cathepsin K osteoclast marker single cell"],
)

log_claim(
    id="macrophage-enrichment-pvns", ctype="data+interpretation", source=SRC,
    claim="Macrophages are massively enriched in the PVNS lesion group pvns-c (~41%, 14544 cells) versus control huamo (~7%, 1925 cells).",
    bio_assertion="PVNS/TGCT is a macrophage-rich lesion in which macrophages make up a large fraction of lesional cellularity, far above normal synovium.",
    data_check={"metric": "macrophage_fraction_by_group"},
    search_terms=["PVNS tenosynovial giant cell tumor macrophage rich infiltrate",
                  "TGCT CD163 CD68 macrophage proportion"],
)

log_claim(
    id="csf1-csf1r-axis", ctype="interpretation", source=SRC,
    claim="CSF1 is expressed mainly by the stromal/fibroblast and mast compartments while CSF1R is highest in macrophages, consistent with a CSF1->CSF1R recruitment axis.",
    bio_assertion="PVNS/TGCT is driven by CSF1 overexpression (commonly via a COL6A3-CSF1 gene fusion) in neoplastic stromal cells, which recruits CSF1R-expressing macrophages - the 'landscape effect'; this is the rationale for CSF1R inhibitors (e.g. pexidartinib).",
    data_check={"metric": "csf1_csf1r_by_celltype", "genes": ["CSF1", "CSF1R"]},
    search_terms=["tenosynovial giant cell tumor CSF1 COL6A3 fusion landscape effect",
                  "pexidartinib CSF1R inhibitor TGCT", "PVNS CSF1 overexpression macrophage recruitment"],
)

log_claim(
    id="mural-pericyte-cluster", ctype="data+interpretation", source=SRC,
    claim="Leiden cluster 2 (13167 cells, originally labelled Fb) expresses RGS5/NOTCH3/ACTA2/PDGFRB with low collagen and absent PDGFRA, indicating mural/pericyte identity rather than fibroblast.",
    bio_assertion="RGS5, NOTCH3, PDGFRB and ACTA2 mark mural cells (pericytes / smooth muscle), whereas PDGFRA together with DCN/LUM/COL1A1 marks fibroblasts; pericytes are characteristically PDGFRA-negative.",
    data_check={"metric": "cluster_marker_means", "cluster": "2",
                "genes": ["RGS5", "NOTCH3", "ACTA2", "PDGFRB", "PDGFRA", "COL1A1", "DCN", "LUM"]},
    search_terms=["pericyte markers RGS5 NOTCH3 PDGFRB single cell", "PDGFRA fibroblast PDGFRB pericyte distinction",
                  "mural cell smooth muscle ACTA2 NOTCH3 synovium"],
)

log_claim(
    id="t-nk-mixed", ctype="data+interpretation", source=SRC,
    claim="The lymphocyte cluster (9) co-expresses T markers (CD3D/E, TRAC) and NK markers (NKG7, GNLY, KLRD1), so it is a mixed T/NK population.",
    bio_assertion="NKG7, GNLY and KLRD1 are NK-cell / cytotoxic markers; their co-occurrence with CD3 indicates a mixed T/NK compartment (cytotoxic CD8 T cells also express NKG7/GNLY).",
    data_check={"metric": "cluster_marker_means", "cluster": "9",
                "genes": ["CD3D", "CD3E", "TRAC", "NKG7", "GNLY", "KLRD1"]},
    search_terms=["NKG7 GNLY KLRD1 NK cell marker single cell", "cytotoxic T cell NKG7 GNLY expression"],
)

log_claim(
    id="absent-b-plasma", ctype="data+interpretation", source=SRC,
    claim="No B-cell or plasma-cell population is detected (MS4A1, CD79A, MZB1, IGHG1 ~0 across all clusters).",
    bio_assertion="The synovial immune infiltrate in PVNS/TGCT is dominated by macrophages and T cells, with B cells / plasma cells typically a minor or variable component.",
    data_check={"metric": "bcell_plasma_max", "genes": ["MS4A1", "CD79A", "MZB1", "IGHG1"]},
    search_terms=["PVNS TGCT lymphocyte infiltrate T cells B cells composition",
                  "tenosynovial giant cell tumor immune microenvironment single cell"],
)

print("seeded; current ledger:")
import subprocess
subprocess.run([sys.executable, str(Path(__file__).parent / "claimlog.py"), "list"])
