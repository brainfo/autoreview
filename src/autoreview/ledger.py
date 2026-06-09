"""Append-only ledger of analysis claims and their review verdicts.

This is the domain-agnostic core the original PVNS prototype was built around,
generalized so any analysis can use it. Two JSONL files live under a ledger
directory:

    claims.jsonl    one claim per line (append-only, idempotent on content)
    verdicts.jsonl  one verdict per line (append-only)

A claim is decomposed into the parts the different reviewers act on:

    claim          the human-readable statement the executor made
    interpretation the literature-checkable assertion (reviewer-literature)
    numbers        structured values the executor produced (reviewer-numeric)
    checks         declarative numeric invariants over those numbers
    inputs/outputs files consumed/produced, for the overseer's integrity guard

Two content hashes key the two review tracks independently, so re-running a
review only re-opens the track whose content actually changed:

    hash   = f(claim, interpretation)   -> literature verdict identity
    nhash  = f(numbers, checks)         -> numeric verdict identity

Editing the prose re-opens the literature verdict; editing the numbers or the
checks re-opens the numeric verdict; neither disturbs the other.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

__all__ = ["Ledger"]

KINDS = ("numeric", "literature")


def _sha(*parts):
    h = hashlib.sha1()
    for p in parts:
        h.update(p.encode())
        h.update(b"\x00")
    return h.hexdigest()[:12]


def _canon(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False) if obj else ""


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Ledger:
    """A claim/verdict ledger rooted at a directory."""

    def __init__(self, root):
        self.root = Path(root)
        self.claims_path = self.root / "claims.jsonl"
        self.verdicts_path = self.root / "verdicts.jsonl"

    # -- io -------------------------------------------------------------
    @staticmethod
    def _read(path):
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

    def _append(self, path, rec):
        self.root.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec

    def load_claims(self):
        return self._read(self.claims_path)

    def load_verdicts(self):
        return self._read(self.verdicts_path)

    # -- hashing --------------------------------------------------------
    @staticmethod
    def content_hash(claim, interpretation=None):
        return _sha((claim or "").strip(), (interpretation or "").strip())

    @staticmethod
    def numbers_hash(numbers=None, checks=None):
        return _sha(_canon(numbers), _canon(checks))

    # -- claims ---------------------------------------------------------
    def log_claim(self, id, claim, interpretation=None, numbers=None, checks=None,
                  ctype="data+interpretation", source=None, inputs=None,
                  outputs=None, search_terms=None):
        """Append a claim. Idempotent: an identical (id, hash, nhash) is a no-op."""
        chash = self.content_hash(claim, interpretation)
        nhash = self.numbers_hash(numbers, checks)
        for c in self.load_claims():
            if c["id"] == id and c["hash"] == chash and c.get("nhash") == nhash:
                return c
        rec = {
            "id": id, "hash": chash, "nhash": nhash, "ts": _now(),
            "type": ctype, "claim": claim, "interpretation": interpretation,
            "numbers": numbers, "checks": checks or [],
            "source": source, "inputs": inputs or [], "outputs": outputs or [],
            "search_terms": search_terms or [],
        }
        return self._append(self.claims_path, rec)

    def claim_numbers(self, id):
        """Latest recorded numbers for a claim id, or None (cross-analysis refs)."""
        found = None
        for c in self.load_claims():
            if c["id"] == id and c.get("numbers") is not None:
                found = c["numbers"]
        return found

    # -- verdicts -------------------------------------------------------
    def log_verdict(self, id, hash, kind, verdict, confidence=None,
                    citations=None, checks=None, notes=None):
        if kind not in KINDS:
            raise ValueError(f"kind must be one of {KINDS}, got {kind!r}")
        rec = {"id": id, "hash": hash, "kind": kind, "verdict": verdict,
               "confidence": confidence, "citations": citations or [],
               "checks": checks or [], "notes": notes, "ts": _now()}
        return self._append(self.verdicts_path, rec)

    def verdict_index(self):
        return {(v["id"], v["hash"], v["kind"]) for v in self.load_verdicts()}

    def verdict_for(self, id, hash, kind):
        match = None
        for v in self.load_verdicts():
            if v["id"] == id and v["hash"] == hash and v["kind"] == kind:
                match = v  # last one wins
        return match

    # -- status ---------------------------------------------------------
    def pending(self, kind=None):
        """Claims still lacking a verdict.

        numeric is pending when a claim declares numbers/checks but has no
        verdict for its current nhash; literature is pending when a claim has an
        interpretation but no verdict for its current hash.
        """
        idx = self.verdict_index()
        out = []
        for c in self.load_claims():
            cid, chash, nhash = c["id"], c["hash"], c.get("nhash")
            need_num = (c.get("numbers") is not None or c.get("checks")) \
                and (cid, nhash, "numeric") not in idx
            need_lit = c.get("interpretation") and (cid, chash, "literature") not in idx
            if kind == "numeric" and need_num:
                out.append(c)
            elif kind == "literature" and need_lit:
                out.append(c)
            elif kind is None and (need_num or need_lit):
                out.append(c)
        return out

    def status_rows(self):
        """One (claim, numeric_verdict, literature_verdict) row per claim."""
        rows = []
        for c in self.load_claims():
            nv = self.verdict_for(c["id"], c.get("nhash"), "numeric")
            lv = self.verdict_for(c["id"], c["hash"], "literature")
            rows.append((c, nv, lv))
        return rows
