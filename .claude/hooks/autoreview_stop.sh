#!/usr/bin/env bash
# Stop hook: auto-run the DETERMINISTIC half of the review (numeric/logic checks
# and the integrity guard - both cheap and tokenless), refresh REPORT.md, and
# surface what still needs an agent (numeric or literature verdicts). No-op when
# there is no ledger, so it is near-free on unrelated turns.
#
# Generalized from the original PVNS auto_verify.sh: no hardcoded paths. The
# ledger directory is $AUTOREVIEW_DIR, else .autoreview under the project root.
# Literature checks are NOT auto-run here: they are networked and need an agent;
# the pending list is surfaced so you can launch reviewer-literature on demand.
set -uo pipefail

# Avoid re-entrancy if a previous stop-hook pass already triggered a continuation.
input="$(cat 2>/dev/null || true)"
case "$input" in *'"stop_hook_active":true'*) exit 0 ;; esac

root="${CLAUDE_PROJECT_DIR:-$PWD}"
dir="${AUTOREVIEW_DIR:-$root/.autoreview}"
[ -f "$dir/claims.jsonl" ] || exit 0

# Resolve the CLI: prefer an installed entry point, fall back to the module.
if command -v autoreview >/dev/null 2>&1; then
  AR=(autoreview)
else
  AR=(python -m autoreview.cli)
fi
run() { "${AR[@]}" --dir "$dir" "$@"; }

# Deterministic, safe-to-automate: re-run numeric checks and regenerate the report.
run check run >/tmp/autoreview_check.log 2>&1 || true
run report >/dev/null 2>&1 || true

num="$(run pending --kind numeric --ids 2>/dev/null || true)"
lit="$(run pending --kind literature --ids 2>/dev/null || true)"

msg=""
[ -n "$num" ] && msg="Pending NUMERIC review: $num . "
[ -n "$lit" ] && msg="${msg}Pending LITERATURE review: $lit . Launch the reviewer agents to complete."
if [ -n "$msg" ]; then
  printf '{"systemMessage": "autoreview ledger: data checks auto-run (see %s/REPORT.md). %s"}\n' "$dir" "$msg"
fi
exit 0
