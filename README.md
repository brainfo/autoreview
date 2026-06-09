# autoreview

A plan / execute / review harness for **trustworthy computational analysis**.

It separates the work of an analysis into distinct roles - one plans, one runs
the code and states conclusions, and independent reviewers check those
conclusions - and it keeps a deterministic, append-only ledger of every claim and
every verdict so nothing rests on an agent's say-so.

It grew out of a single-cell RNA-seq review (see `examples/pvns_showcase/`) and is
generalized for bioinformatics analyses, but the core is domain-agnostic.

## The idea

Every conclusion is logged as a **claim** and reviewed on two independent tracks:

- **Numeric / logic** - the numbers must obey the relations they imply: proportions
  sum to 1, counts are non-negative, `count == fraction * total`, the same quantity
  reported by two analyses agrees, control < disease, orders of magnitude line up.
  These are evaluated by a **deterministic engine**, never by an LLM's arithmetic.
- **Literature** - the domain interpretation is checked against the published record,
  with citations, a confidence level, and an explicit caveat.

A separate **integrity guard** content-hashes every input and output, so the
overseer can assert that the files an analysis ran on exist and were not altered
mid-run.

## Roles

Five Claude Code subagents (`.claude/agents/`), each with one job:

| role | does | reviews |
|---|---|---|
| `planner` | turns a question + inputs into an explicit `plan.json` | - |
| `executor` | writes and runs the analysis code, logs claims + numbers | - |
| `reviewer-numeric` | authors task-specific invariants as checks, runs them | the numbers |
| `reviewer-literature` | searches the literature, logs cited verdicts | the interpretation |
| `overseer` | guards file integrity, checks every other agent did its job | the agents |

The deterministic parts (the ledger, the numeric/logic engine, the integrity
guard) live in the Python package and run with no LLM. The agents drive that core
through the `autoreview` CLI, so the state of a review is always in files you can
inspect, diff, and re-run - not in a transcript.

### Why the numeric reviewer authors checks instead of using a fixed checklist

A fixed checklist can only catch the invariants someone anticipated. The numeric
reviewer instead reads the specific task, plan, and results and **invents** the
invariants they imply - then writes each as a declarative spec (or a safe
arithmetic expression) that the deterministic engine evaluates. You get the
agent's task-awareness without ever trusting it to do the arithmetic: if it cannot
express a judgement as a runnable check, the number is not reviewed. A standard
library of always-applicable invariants ships alongside, so the common cases are
free.

## Install

```bash
pip install -e .            # or:  uv pip install -e .
pip install -e '.[dev]'     # with pytest
```

## Quickstart - the toy example

```bash
cd examples/toy
./run.sh
```

This guards a synthetic `counts.csv`, runs a small analysis that logs two claims
with their numbers and checks, runs the numeric review (sum-to-one, bounds,
`count == fraction * total`, cross-analysis consistency, disease/treatment
ordering), verifies the input was not mutated, and writes `ledger/REPORT.md`. The
literature track is left pending - that half needs the `reviewer-literature` agent.

To see a violation caught, edit a number in `examples/toy/analyze.py` (e.g. make a
fraction not sum to 1) and re-run: the numeric verdict flips to `[VIOLATION]` and
the failing check is named.

## CLI

```
autoreview claim add  <file|->        log claim(s) from JSON
autoreview verdict add <file|->       log verdict(s) from JSON
autoreview check run  [--specs f]     run numeric/logic checks, log verdicts
autoreview guard register <files...>  record files + sha256 in the manifest
autoreview guard verify               re-hash the manifest, report drift
autoreview report                     (re)generate REPORT.md
autoreview status                     one line per claim, both tracks
autoreview pending [--kind ...]       claims still needing review
```

The ledger directory defaults to `.autoreview` (override with `--dir` or
`$AUTOREVIEW_DIR`).

## Running the agent pipeline

In Claude Code, from a project that has its data:

```
/autoreview-run  <your analysis question>  path/to/data ...
```

The command conducts planner -> executor -> reviewer-numeric ->
reviewer-literature, launching the `overseer` between stages and stopping on any
integrity failure or unmet promise.

### Optional: the Stop hook

`.claude/hooks/autoreview_stop.sh` re-runs the deterministic checks and refreshes
the report after each turn, surfacing what still needs an agent. It is **opt-in** -
this repo does not ship an active `.claude/settings.json`. To enable it, create
`.claude/settings.json` yourself with:

```json
{
  "permissions": { "allow": ["Bash(autoreview:*)"] },
  "hooks": {
    "Stop": [
      { "matcher": "",
        "hooks": [
          { "type": "command",
            "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/autoreview_stop.sh\"" }
        ] }
    ]
  }
}
```

## Layout

```
src/autoreview/        deterministic core (no LLM)
  ledger.py            append-only claim/verdict ledger, two-hash tracks
  checks/numeric.py    the invariant engine (sum, equal, bounds, monotonic, approx, expr)
  checks/expr.py       safe arithmetic evaluator for agent-authored invariants
  checks/integrity.py  content-hash file guard
  report.py  cli.py
.claude/agents/        planner, executor, reviewer-numeric, reviewer-literature, overseer
.claude/commands/      /autoreview-run
.claude/hooks/         the opt-in Stop hook
examples/toy/          runnable synthetic walkthrough
examples/pvns_showcase/  the original scRNA-seq review (frozen; data not bundled)
tests/                 pytest suite for the deterministic core
docs/ARCHITECTURE.md   data model, check-spec schema, design notes
```

## License

MIT - see `LICENSE`.
