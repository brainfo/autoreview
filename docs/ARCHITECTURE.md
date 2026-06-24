# Architecture

autoreview separates an analysis into roles that produce and check artifacts, and
keeps all shared state in an append-only, file-based ledger. The deterministic
parts run with no LLM; the agents only do what genuinely needs judgement.

## Data flow

```
  question + inputs
        |
   [planner]  --------------------------------> plan.json
        |                                          |
   [overseer] guard register inputs (sha256) ------+--> manifest.json
        |
   [executor] write + run code ---> results/ , scripts/
        |        log claims (numbers, checks, input/output hashes)
        |        record deviations for broken plan assumptions --> deviations.jsonl
        v
     claims.jsonl
        |
   [reviewer-numeric] author invariants, run engine --> verdicts.jsonl (numeric)
   [reviewer-literature] search literature ----------> verdicts.jsonl (literature)
        |
   [overseer] guard verify (inputs intact, outputs present, queues empty,
        |      no open contract deviation)
        v
   loop signal? (violation | refuted/uncertain | open/unenacted deviation)
        |  yes -> [planner] re-plan (loop N+1), enact deviations, supersede claims
        |  no  -> REPORT.md
```

The main loop (or the `/autoreview-run` command) is the conductor: it launches each
agent and runs the overseer between stages, proceeding only on GO. A run is a
single pass by default; it loops only when a pass leaves a signal that warrants
another (see "Deviations and the conditional loop").

## The ledger

Append-only JSONL files under the ledger directory (`.autoreview` by default):
`claims.jsonl` and `verdicts.jsonl` (below), plus `deviations.jsonl` (see
"Deviations and the conditional loop").

A **claim** records a conclusion and everything the reviewers need:

```jsonc
{
  "id": "toy-mac-enrichment",
  "hash": "40f3cb984838",     // f(claim, interpretation)  -> literature track identity
  "nhash": "7cff6536e3fa",    // f(numbers, checks)        -> numeric track identity
  "claim": "Macrophages rise from 9% (control) to 55% (disease)...",
  "interpretation": "A macrophage-rich infiltrate that expands in disease...",
  "numbers": { "mac_pct": { "control": 9.0, "disease": 55.0, "treated": 14.0 },
               "dis_total": 2000, "dis_mac_count": 1100 },
  "checks": [ /* declarative numeric specs, see below */ ],
  "inputs":  [{ "path": "data/counts.csv", "sha256": "..." }],
  "outputs": [{ "path": "results/...",     "sha256": "..." }],
  "search_terms": ["macrophage rich infiltrate disease"]
}
```

A **verdict** records one review on one track:

```jsonc
{ "id": "toy-mac-enrichment", "hash": "<claim hash for that track>",
  "kind": "numeric",               // numeric | literature
  "verdict": "consistent",         // consistent|violation (numeric); supported|partially-supported|refuted|uncertain (literature)
  "confidence": "high",            // literature only
  "checks": [ /* per-check results, numeric only */ ],
  "citations": [ /* literature only */ ],
  "notes": "the caveat" }
```

### Two hashes, two tracks

The literature track is keyed by `hash = f(claim, interpretation)`; the numeric
track by `nhash = f(numbers, checks)`. Re-logging a claim is idempotent. Editing
the prose re-opens only the literature verdict; editing a number or a check
re-opens only the numeric verdict. The two reviews never invalidate each other,
so you can refine one without redoing the other.

## Deviations and the conditional loop

An analysis sometimes discovers, mid-run, that the plan no longer matches the
data. The plan is a **contract**: the planner declares the claims each step will
produce, and the overseer verifies the executor delivered exactly those. If the
executor could rewrite the plan, that check would mean nothing — it would be
grading its own homework. So discoveries are handled by **capture, not enact**.

Three kinds, handled differently:

- **Method (case A).** A *how*, not a *what* — a renamed column, a misspelled
  label, a moved path. The executor adapts in place and records the adaptation in
  the claim. It never changes which claims are produced, so it never gates or
  loops. Recorded as a `method` deviation only if non-obvious (audit trail).
- **Contract (case B).** An assumption the plan rested on is false — an input
  lacks the raw counts a step needs; two datasets meant to be pooled are on
  different scales. The executor does **not** fabricate a number to satisfy the
  plan. It records a `contract` deviation and skips the claim it cannot honestly
  make (a promised claim may be absent only if a deviation names it). This gates
  sign-off and feeds the loop signal.
- **Finding (case C).** Just a result — it is a claim, and it gets reviewed. No
  special machinery.

A deviation is an append-only record in `deviations.jsonl`, mirroring the
claim → verdict pattern: the executor writes the observation; only the
planner/overseer gate writes a resolution (`accepted` / `rejected` / `deferred`,
with where the fix is `enacted_in`). Its `scope` says what a fix touches and so
whether it is a same-run amendment or a next-loop supersede:

- `forward` — a not-yet-settled step changes; the re-plan amends the tail. No
  reviewed artifact is invalidated.
- `backward` — a step already executed is invalid; its claims are **superseded**
  in a new loop. The loop-N claim (same id, new `nhash`, stamped `loop: N`)
  overrides the loop-1 claim in every query, while the original stays on disk as
  history. Nothing is overwritten.

**The loop is conditional.** After a pass the conductor gathers the loop signal —
any numeric `violation`, any literature `refuted`/`uncertain`, any contract
deviation still open or accepted-but-unenacted. Empty signal → stop; the initial
plan was sufficient. Non-empty → the planner re-plans to address exactly those
signals, and the pass repeats (capped at 3 loops). The signal *is* the reason to
loop, so the loop earns its place instead of running by ritual.

**The ledger is the memory.** The "what we learned for the next loop" is not a
separate notes file — it is `deviations.jsonl` plus the `violation` / `refuted`
verdicts in `verdicts.jsonl`, already on disk, already diffable, each already
tagged with the step or claim it attaches to. The re-planning planner reads them
directly.

## The numeric / logic engine

A check is a small JSON spec. Values are referenced by:

- a literal number `0.55`
- a dotted key into the claim's `numbers`: `"mac_pct.disease"`
- `{"value": x}`
- `{"claim": "other-id", "key": "dotted.key"}` - a number from **another** claim,
  which is how cross-analysis consistency is expressed.

Kinds:

| kind | asserts | key fields |
|---|---|---|
| `sum` | referenced values sum to a target | `values`, `target`, `tol` |
| `equal` | all referenced values agree | `values`, `tol`, `rel` |
| `bounds` | each value lies in `[lo, hi]` | `values`, `lo`, `hi` |
| `monotonic` | a sequence is increasing/decreasing/... | `values`, `direction` |
| `approx` | two values agree to a rel. tol. or N decades | `a`, `b`, `max_rel` or `max_decades` |
| `expr` | `lhs` and `rhs` expressions are equal | `lhs`, `rhs`, `vars`, `tol`, `rel` |

`severity: "warn"` surfaces a failed check without turning the verdict into a
violation; the default is `"error"` (blocking).

### Safe expressions

`expr` checks (and the `vars` of any check) are evaluated by `checks/expr.py`, a
whitelisted AST evaluator: numeric literals, named variables, `+ - * / // % **`,
list/tuple literals, and a fixed set of math functions (`abs min max sum len round
sqrt exp log log2 log10 floor ceil`). Attribute access, arbitrary calls,
comprehensions, and dunder tricks all raise `ExprError`. This is what lets an agent
author a novel invariant (`count == fraction * total`, `log2fc_AB == -log2fc_BA`)
as data the engine runs, with no risk of the spec reading the filesystem or
importing a module.

A malformed spec is reported as a *failed check* (with `SPEC ERROR:` in its
detail), never an exception that aborts the batch - one bad spec cannot hide the
others.

## The integrity guard

`checks/integrity.py` content-hashes files (sha256) into a manifest. `verify`
classifies each entry as `ok`, `missing`, `changed`, or `appeared` (an output that
was absent and is now present). An input that is `missing` or `changed` is a
NO-GO; an output still `missing` after its step ran is a NO-GO. This is the
deterministic backbone of the overseer: it can assert the analysis ran on intact
inputs without trusting any agent's word.

## Design choices

- **Files over memory.** Every claim, verdict, check result, and hash is on disk.
  A review is reproducible and diffable; an agent's context is not part of the
  trust boundary.
- **Deterministic where possible, agentic only where necessary.** Arithmetic,
  hashing, and bookkeeping are plain tested Python. LLMs are used for planning,
  writing analysis code, judging literature, and *proposing* invariants - never
  for computing or checking a number.
- **Idempotent and append-only.** Nothing is overwritten; re-running converges.
  Editing a claim re-opens exactly the track that changed.
