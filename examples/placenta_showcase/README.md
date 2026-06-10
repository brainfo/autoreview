# Placenta showcase (frozen)

Results from one prompt "/autoreview-run what you notice with @first_trimester_final.h5ad
@term_final.h5ad",

## The data 

The two inputs are openly deposited:

> Hong, Jiang; Deng, Qiaolin. *Integrated and annotated human placenta scRNA-seq
> matrices.* Zenodo, 2024.
> DOI: [10.5281/zenodo.11103744](https://doi.org/10.5281/zenodo.11103744) (CC BY 4.0).
> Files: `first_trimester_final.h5ad` (1.0 GB), `term_final.h5ad` (349.8 MB).

`.autoreview/manifest.json` records
the sha256 of each input, so after downloading you can confirm you have the exact
matrices that were reviewed (place them at the recorded paths, then
`autoreview guard verify`).

## Process

- Stage 1 — overseer pre-flight.
  - overseer pre-flight: GO. Both inputs exist and carry valid HDF5 signatures — first_trimester_final.h5ad (~1.01 GB) and term_final.h5ad (~349.8 MB).
- Stage 2 — planner. 
  - Designing a comparative plan (per-dataset
  structural summary, cell-type composition + the first-trimester→term shift, shared/specific genes & labels, data-state checks) and writing plan.json.
- Stage 3 — overseer post-plan.
  - POST-PLAN: GO. 5 steps, 12 unique claim ids, 7 output files; both inputs registered (sha256 baselined) and guard verify → OK.
- Stage 4 — executor.
  - all 5 steps ran, 7 outputs written + registered, all 12 claims logged, inputs unmutated. Now the integrity gate.
- Stage 5 — overseer post-exec.
  - POST-EXEC: GO. All 7 outputs present, all 12 claims in the ledger, both inputs byte-identical to baseline.
- Stage 6 — reviewer-numeric.
  - 65 task-specific invariants added across all 12 claims, all consistent, zero violations. Now the overseer post-numeric checkpoint.
  - POST-NUMERIC: GO. Numeric queue empty, all 12 claims consistent, zero
  violations, manifest intact
- Stage 7 — reviewer-literature.
  - All 12 carry literature verdicts. The key catch: claim-shift-direction is only partially-supported (low confidence) — the Hofbauer-cell rise toward term is contradicted by histology and likely a cross-dataset method/batch artifact.
  - overseer post-literature.
  - POST-LITERATURE: GO. Queue empty, all 12 verdicts carry resolving citations (5 substantive PMIDs all HTTP 200; the one empty-PMID MDPI reference verified genuine via Crossref), manifest intact. Now the final step.
- Stage 8 — regenerate report
  - Report regenerated at .autoreview/REPORT.md (12 claims, all num:ok lit:ok). The ls REPORT.md at repo root is what threw exit 2 — the file lives under the ledger dir. Let me confirm the report rendered cleanly.

## Results
see claims in .autoreview/ and the reviews of the claims in REPORT.md. The contents following "*Caveat:*" in the report would be of interest.