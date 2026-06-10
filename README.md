# autoreview

A plan / execute / review harness for **trustworthy computational analysis**.

It separates the work of an analysis into distinct roles and it keeps a deterministic, append-only ledger of every claim and
every verdict so nothing rests on an agent's say-so.

A full worked run is saved in `examples/placenta_showcase/`, which was from one prompt "/autoreview-run what you notice with @first_trimester_final.h5ad
@term_final.h5ad".

## Install

The following two are required

### 1. The CLI

```bash
pip install -e .            # or:  uv pip install -e .
pip install -e '.[dev]'     # with pytest
uv tool install --editable .   # global: the `autoreview` command in every project
```

The agents call `autoreview` as a bare command, so the global `uv tool install`
is the most convenient form for the plugin below.

### 2. Claude Code plugin

The five subagents, the `/autoreview-run` command, and the Stop hook ship as a
plugin, so they are available in every project without copying `.claude/` around.
This repo is its own marketplace.

```
/plugin marketplace add brainfo/autoreview
/plugin install autoreview@autoreview-marketplace
```

Without the plugin you can still copy `.claude/agents/` and
`.claude/commands/autoreview-run.md` into a project's `.claude/`, or into
`~/.claude/` for all projects.

## Running the agent pipeline

In Claude Code:

```
/autoreview-run  <your analysis question>  path/to/data ...
```

### During the run - the agents drive the CLI for you

Every role records and checks its work *through* the `autoreview` CLI, so the
state of the review lands in `.autoreview/` as it happens:

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

### The Stop hook

`.claude/hooks/autoreview_stop.sh` re-runs the deterministic checks and refreshes
the report after each turn, surfacing what still needs an agent. It is a safe
no-op in any project without an `.autoreview` ledger.

To enable it **without** the plugin, create a
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

## License

MIT - see `LICENSE`.
