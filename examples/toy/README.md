# Toy example

A self-contained, synthetic walkthrough of the pipeline driving only the
deterministic core (no LLM, standard library only).

```bash
./run.sh
```

## What it does

`data/counts.csv` holds per-sample cell counts for three groups (control,
disease, treated). `analyze.py` stands in for the **executor**: it computes
per-group macrophage percentages and the pooled disease composition, then emits
two claims, each carrying the numbers it produced and the checks that should hold.
`run.sh` then mirrors the agent pipeline against the deterministic CLI:

1. **overseer** - `guard register` records the input's sha256.
2. **executor** - `analyze.py | autoreview claim add -` logs the claims.
3. **reviewer-numeric** - `check run` evaluates the logic checks.
4. **overseer** - `guard verify` confirms the input was not mutated.
5. **report** - renders `ledger/REPORT.md`.

## Checks demonstrated

- `bounds` - percentages stay in [0, 100], fractions in [0, 1].
- `monotonic` - disease > control; treated < disease (the rescue).
- `expr` - the dimensional identity `dis_mac_count == fraction * dis_total`.
- `sum` - the pooled disease cell-type fractions sum to 1.
- `equal` - two independent counts of disease cells agree, and the disease total
  matches the value recorded by the other claim (**cross-analysis consistency**).

## See a violation caught

Edit `analyze.py` to break an invariant - e.g. drop a cell type from the `sum`
check, or change a recorded number so `count == fraction * total` no longer
holds - and re-run. The numeric verdict for that claim flips to `[VIOLATION]` and
the report names the failing check. The literature track stays pending because
that half needs the `reviewer-literature` agent.
