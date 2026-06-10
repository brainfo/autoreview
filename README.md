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

Two independent pieces: the `autoreview` **CLI** (the deterministic core,
installed once as normal software) and the Claude Code **presets** (the agents
and the `/autoreview-run` command, distributed as a plugin). Each is installed
once; neither implies the other.

### 1. The CLI (the deterministic core)

```bash
pip install -e .            # or:  uv pip install -e .
pip install -e '.[dev]'     # with pytest
uv tool install --editable .   # global: the `autoreview` command in every project
```

The agents call `autoreview` as a bare command, so the global `uv tool install`
is the most convenient form for the plugin below.

### 2. The presets (Claude Code plugin)

The five subagents, the `/autoreview-run` command, and the Stop hook ship as a
plugin, so they are available in every project without copying `.claude/` around.
This repo is its own marketplace.

```
# from a local clone (works now, no GitHub needed):
/plugin marketplace add /path/to/autoreview
/plugin install autoreview@autoreview-marketplace

# or, once the repo is on GitHub:
/plugin marketplace add <owner>/autoreview
/plugin install autoreview@autoreview-marketplace
```

The plugin distributes the presets only - it does **not** install the CLI, so
step 1 stays a prerequisite. Installing it also enables the deterministic Stop
hook, a safe no-op in any project without an `.autoreview` ledger.

Without the plugin you can still copy `.claude/agents/` and
`.claude/commands/autoreview-run.md` into a project's `.claude/`, or into
`~/.claude/` for all projects.

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

In Claude Code, from a project that has its data and the presets (the
`.claude/agents/` roles and the `/autoreview-run` command, available via the
plugin - see Install - or in the project's `.claude/`, or at user level in
`~/.claude/`):

```
/autoreview-run  <your analysis question>  path/to/data ...
```

The command conducts the staged pipeline, launching the `overseer` between every
stage and stopping on any integrity failure or unmet promise.

### During the run - the agents drive the CLI for you

Every role records and checks its work *through* the `autoreview` CLI, so the
state of the review lands in `.autoreview/` as it happens - it is never left to
live only in the chat. Given the CLI is installed, you do nothing during the run:

| role | drives | writes |
|---|---|---|
| `conductor` (the `/autoreview-run` command) | sets `AUTOREVIEW_DIR`; launches each role and the overseer; `autoreview report` | orchestration; the final `REPORT.md` and summary |
| `overseer` (at every checkpoint) | `autoreview guard register`, `autoreview guard verify`, `autoreview pending`, `autoreview status` | the integrity manifest; a GO / NO-GO gate between stages |
| `planner` | writes `plan.json` directly | the ordered plan: inputs, steps, and the claims each step will produce |
| `executor` | `autoreview claim add`, `autoreview guard register` | each claim with its numbers, seed checks, and input/output hashes |
| `reviewer-numeric` | `autoreview check run` | the task-specific invariants and the numeric verdicts |
| `reviewer-literature` | `autoreview verdict add` | cited literature verdicts, each with a confidence and a caveat |

### After the run - you drive the same CLI to verify

Because the record is in files and the checks have no LLM in them, you point the
*same* CLI at `.autoreview/` to inspect the run and independently reproduce its
verdicts - without re-running the agents or taking their word for anything:

```
autoreview status          # every claim, both review tracks, one line each
autoreview pending         # anything still unreviewed
autoreview guard verify    # re-hash inputs/outputs, confirm nothing drifted mid-run
autoreview check run       # re-run the numeric checks - deterministic, same verdicts
autoreview report          # regenerate REPORT.md
```

The agent run and your audit use identical commands against identical files. That
sameness is reproducibility, not redundancy: it is what lets you re-earn trust in
a result without re-trusting the agents that produced it.

### The loop

```
presets installed once
  -> /autoreview-run <question> <data>
  -> read REPORT.md / autoreview status
  -> re-run guard verify + check run whenever you want to re-earn trust
```

### The Stop hook

`.claude/hooks/autoreview_stop.sh` re-runs the deterministic checks and refreshes
the report after each turn, surfacing what still needs an agent. It is a safe
no-op in any project without an `.autoreview` ledger.

If you installed the plugin, this hook ships with it and is already active - you
need do nothing. To enable it **without** the plugin, create a
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
.claude/hooks/         the Stop hook (autoreview_stop.sh) + plugin hook config (hooks.json)
.claude/.claude-plugin/plugin.json   the presets packaged as a Claude Code plugin
.claude-plugin/marketplace.json      this repo as its own plugin marketplace
examples/toy/          runnable synthetic walkthrough
examples/pvns_showcase/  the original scRNA-seq review (frozen; data not bundled)
tests/                 pytest suite for the deterministic core
docs/ARCHITECTURE.md   data model, check-spec schema, design notes
```

## License

MIT - see `LICENSE`.
