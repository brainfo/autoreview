"""autoreview - a plan / execute / review harness for trustworthy analysis.

Separated roles (see .claude/agents/):
  planner    designs the analysis plan
  executor   writes and runs the analysis code, recording claims + numbers
  reviewer-literature  checks each interpretation against published evidence
  reviewer-numeric     checks the numbers by logic (deterministic invariants)
  overseer   guards file integrity and watches the other agents

The deterministic core (this package) carries the ledger, the numeric/logic
check engine, and the file-integrity guard - none of which require an LLM.
"""
from .ledger import Ledger
from .checks import run_check, run_checks, Manifest, sha256_file

__version__ = "0.1.0"
__all__ = ["Ledger", "run_check", "run_checks", "Manifest", "sha256_file", "__version__"]
