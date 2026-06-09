"""Append-only ledger for claims made during analysis, plus their verdicts.

Two files live next to this module:
  claims.jsonl    - one claim per line (append-only, deduped on id+content hash)
  verdicts.jsonl  - one verdict per line (append-only); a claim is "verified" for a
                    given kind once a verdict with the matching (id, hash, kind) exists

A claim is decomposed into:
  - claim         : the human-readable statement as made by the analyst
  - data_check    : optional, a deterministically recomputable fact (numbers + source)
  - bio_assertion : optional, the literature-checkable biological interpretation

Keying on a content hash means: re-logging the same claim is a no-op, but editing the
claim text or its assertion yields a new hash -> it shows up as pending again.

CLI:
    python claimlog.py list      # all claims with per-kind verdict status
    python claimlog.py pending   # claims still needing a data and/or literature verdict
"""
import json, hashlib, sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
CLAIMS = HERE / "claims.jsonl"
VERDICTS = HERE / "verdicts.jsonl"


def _hash(claim, bio_assertion):
    h = hashlib.sha1()
    h.update((claim or "").strip().encode())
    h.update(b"\x00")
    h.update((bio_assertion or "").strip().encode())
    return h.hexdigest()[:12]


def _read(path):
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def load_claims():
    return _read(CLAIMS)


def load_verdicts():
    return _read(VERDICTS)


def log_claim(id, claim, ctype="interpretation", bio_assertion=None,
              data_check=None, source=None, search_terms=None):
    chash = _hash(claim, bio_assertion)
    for c in load_claims():
        if c["id"] == id and c["hash"] == chash:
            return c  # already logged, unchanged -> idempotent
    rec = {
        "id": id, "hash": chash,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "type": ctype, "claim": claim, "bio_assertion": bio_assertion,
        "data_check": data_check, "source": source,
        "search_terms": search_terms or [],
    }
    with CLAIMS.open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def log_verdict(id, hash, kind, verdict, confidence=None, citations=None, notes=None):
    """kind in {'data','literature'}; citations = [{title,authors,year,journal,url,pmid,evidence}]"""
    rec = {
        "id": id, "hash": hash, "kind": kind, "verdict": verdict,
        "confidence": confidence, "citations": citations or [], "notes": notes,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    with VERDICTS.open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def verdict_index():
    return {(v["id"], v["hash"], v["kind"]) for v in load_verdicts()}


def pending(kind=None):
    """Claims lacking a verdict. If kind given, lacking that kind; else lacking either
    data (when a data_check exists) or literature (when a bio_assertion exists)."""
    idx = verdict_index()
    out = []
    for c in load_claims():
        key = (c["id"], c["hash"])
        if kind:
            if (key[0], key[1], kind) not in idx:
                out.append(c)
        else:
            need_data = c.get("data_check") and (key[0], key[1], "data") not in idx
            need_lit = c.get("bio_assertion") and (key[0], key[1], "literature") not in idx
            if need_data or need_lit:
                out.append(c)
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    idx = verdict_index()
    if cmd == "pending":
        print(json.dumps(pending(), indent=2, ensure_ascii=False))
    else:
        for c in load_claims():
            k = (c["id"], c["hash"])
            d = "data:✓" if (k[0], k[1], "data") in idx else ("data:·" if c.get("data_check") else "data:-")
            l = "lit:✓" if (k[0], k[1], "literature") in idx else ("lit:·" if c.get("bio_assertion") else "lit:-")
            print(f"{c['id']:30s} [{c['hash']}] {d} {l}  {c['claim'][:70]}")
