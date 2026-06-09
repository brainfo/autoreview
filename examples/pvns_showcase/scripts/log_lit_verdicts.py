"""Record the literature verdicts returned by the verifier agents into the ledger.
Keyed by current (id, hash) so it stays in sync if a claim is later edited."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from claimlog import load_claims, log_verdict, verdict_index

by_id = {c["id"]: c for c in load_claims()}
idx = verdict_index()

V = {
 "osteoclast-pvns-specificity": dict(verdict="supported", confidence="high",
  notes="Giant cells are abundance-variable: less common in the diffuse form and rare/absent in ~20% of TGCT cases, so absence does not exclude TGCT - but presence still discriminates PVNS from normal synovium, so the claim's direction holds.",
  citations=[
   {"title":"Multinucleated cells in PVNS and GCTTS express features of osteoclasts (Darling)","year":1997,"url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC1858182/"},
   {"title":"Giant cells in PVNS express osteoclast phenotype incl. lacunar resorption (Neale)","year":1997,"url":"https://pubmed.ncbi.nlm.nih.gov/9306944/"},
   {"title":"Osteoclast-like giant cells in TGCT from CD14+ monocytes (Robert/Miossec)","year":2022,"url":"https://www.frontiersin.org/journals/immunology/articles/10.3389/fimmu.2022.820046/full"},
   {"title":"PVNS - StatPearls (osteoclast-type giant cells characteristic)","year":2024,"url":"https://www.ncbi.nlm.nih.gov/books/NBK549850/"}]),

 "osteoclast-marker-signature": dict(verdict="supported", confidence="high",
  notes="Refinement: CSF1R marks the myeloid/osteoclast lineage (most CSF1R+ cells in TGCT are recruited macrophages) rather than being osteoclast-restricted like TRAP/CTSK; MMP9 is likewise not osteoclast-exclusive.",
  citations=[
   {"title":"Cathepsin K and MMP-9 most abundant osteoclast proteases; TRAP an osteoclast marker (Logar)","year":2007,"url":"https://pubmed.ncbi.nlm.nih.gov/17593491/"},
   {"title":"Acp5+ cells express classical osteoclast markers Acp5/Mmp9/Ctsk","year":2022,"url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC9461675/"},
   {"title":"CSF1/CSF1R role in TGCT (Cassier/Brahmi)","year":2024,"url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC11167812/"}]),

 "macrophage-enrichment-pvns": dict(verdict="supported", confidence="high",
  notes="Exact percentage is cohort/subtype/marker-definition dependent; normal synovium has resident macrophages, so this is relative enrichment rather than absence-vs-presence.",
  citations=[
   {"title":"A landscape effect in tenosynovial giant-cell tumor (West)","year":2006,"url":"https://pubmed.ncbi.nlm.nih.gov/16407111/"},
   {"title":"Single-cell analysis of pathological heterogeneity in TGCT (Xie)","year":2025,"url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC12244509/"},
   {"title":"Structure-guided blockade of CSF1R in TGCT - pexidartinib (Tap)","year":2015,"url":"https://pubmed.ncbi.nlm.nih.gov/26222558/"}]),

 "csf1-csf1r-axis": dict(verdict="supported", confidence="high",
  notes="COL6A3-CSF1 is the most common but NOT universal mechanism (alternative CSF1 fusion partners exist; some cases lack any detectable CSF1 alteration). The neoplastic fraction is a small minority (~2-16%). Mast-cell CSF1 is at most a secondary source, not the established driver.",
  citations=[
   {"title":"A landscape effect in tenosynovial giant-cell tumor (West)","year":2006,"url":"https://pubmed.ncbi.nlm.nih.gov/16407111/"},
   {"title":"COL6A3-CSF1 fusion transcripts in TGCT (Moller)","year":2008,"url":"https://pubmed.ncbi.nlm.nih.gov/17918257/"},
   {"title":"CSF1R blockade in TGCT - pexidartinib (Tap, NEJM)","year":2015,"url":"https://pubmed.ncbi.nlm.nih.gov/26222558/"},
   {"title":"FDA approves pexidartinib for TGCT","year":2019,"url":"https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-pexidartinib-tenosynovial-giant-cell-tumor"}]),

 "mural-pericyte-cluster": dict(verdict="supported", confidence="high",
  notes="NOTCH3/ACTA2 are shared with a THY1+ perivascular fibroblast subset and RGS5/NOTCH3 are organ-variable - rely on the full panel plus PDGFRA/collagen NEGATIVITY, not single genes.",
  citations=[
   {"title":"RGS5 as a pericyte/VSMC marker (Bondjers)","year":2003,"url":"https://pubmed.ncbi.nlm.nih.gov/12598306/"},
   {"title":"Synovial mural cells distinct from PDGFRA+ fibroblasts (Wei, Nature)","year":2020,"url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC7841716/"},
   {"title":"PDGFRB core pericyte vs PDGFRA/LUM/DCN fibroblast (Baek)","year":2022,"url":"https://www.frontiersin.org/journals/cardiovascular-medicine/articles/10.3389/fcvm.2022.876591/full"},
   {"title":"Distinct fibroblast subsets in synovium (Croft, Nature)","year":2019,"url":"https://www.nature.com/articles/s41586-019-1263-7"}]),

 "t-nk-mixed": dict(verdict="supported", confidence="high",
  notes="IMPORTANT NUANCE: NKG7/GNLY/KLRD1 are cytotoxic markers, NOT NK-exclusive - cytotoxic CD8 (and gamma-delta) T cells co-express them. Co-expression with CD3 does NOT prove a separate NK population; a true NK call needs a CD3/TRAC-negative subset with NCAM1/KLRF1/FCGR3A. The cluster may be cytotoxic T rather than genuine T+NK mixture.",
  citations=[
   {"title":"NKG7 cytolytic gene in CD8 T and NK (Wen)","year":2022,"url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC8816890/"},
   {"title":"NKG7 pan-cytotoxicity marker (Turiello)","year":2025,"url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC12179582/"},
   {"title":"NKG7 in ~93-99% of cytotoxic T cells (Pizzolato, PNAS)","year":2019,"url":"https://www.pnas.org/doi/10.1073/pnas.1818488116"}]),

 "cluster9-t-not-nk": dict(verdict="supported", confidence="high",
  notes="Confirmed by both data (>80% CD3+, only 2.6% CD3-neg NK-receptor+) and literature: NKG7/GNLY/KLRD1 are pan-cytotoxic, so co-expression with CD3 indicates cytotoxic T cells rather than a true NK population. This is the corrected annotation (was T/NK).",
  citations=[
   {"title":"NKG7 cytolytic gene expressed by both CD8 T and NK cells (Wen)","year":2022,"url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC8816890/"},
   {"title":"NKG7 in ~93-99% of cytotoxic T cells (Pizzolato, PNAS)","year":2019,"url":"https://www.pnas.org/doi/10.1073/pnas.1818488116"},
   {"title":"NKG7 as a pan-cytotoxicity marker (Turiello)","year":2025,"url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC12179582/"}]),

 "absent-b-plasma": dict(verdict="supported", confidence="medium",
  notes="Precise wording is 'minor/variable', not 'absent': lymphoid/lymphoplasmacytic aggregates occur in some lesions and B/plasma appear as a small cluster in some scRNA-seq datasets. Plasma cells are rarely quantified explicitly - hence medium confidence.",
  citations=[
   {"title":"TGCT macrophage-dominated infiltrate, unlike T-rich RA (Robert/Miossec)","year":2022,"url":"https://www.frontiersin.org/journals/immunology/articles/10.3389/fimmu.2022.820046/full"},
   {"title":"scRNA-seq of TGCT - macrophages/fibroblasts predominant, B cells minor (Xie)","year":2025,"url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC12244509/"},
   {"title":"TGCT clusters: macrophage/T/giant, no B/plasma reported (Fahnrich)","year":2024,"url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC11464255/"},
   {"title":"Synovial B/plasma substantial in RA (contrast) (Zhang)","year":2019,"url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC6602051/"}]),
}

for cid, v in V.items():
    c = by_id.get(cid)
    if not c:
        print("skip (no claim):", cid); continue
    if (c["id"], c["hash"], "literature") in idx:
        print("already logged:", cid); continue
    log_verdict(c["id"], c["hash"], "literature", v["verdict"],
                confidence=v["confidence"], citations=v["citations"], notes=v["notes"])
    print("logged:", cid, "->", v["verdict"], v["confidence"])
