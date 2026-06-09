"""File-integrity guard - the deterministic half of the overseer agent.

Before any step runs, the overseer registers the files it will read or write and
their sha256. It then verifies, at any later point, that declared inputs still
exist and are byte-for-byte unchanged, and that declared outputs were actually
produced. This is what lets the overseer assert "the inputs the executor ran on
are intact" without trusting any agent's word for it.
"""
import hashlib
import json
from pathlib import Path

__all__ = ["sha256_file", "register", "verify", "Manifest"]

_CHUNK = 1 << 20


def sha256_file(path):
    """Return the hex sha256 of a file, or None if it does not exist."""
    p = Path(path)
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def register(paths, role="input"):
    """Build a manifest entry list for ``paths`` (each {path, sha256, role}).

    A missing file is recorded with sha256=None and exists=False so the overseer
    can refuse to start a step whose declared input is absent.
    """
    out = []
    for p in paths:
        digest = sha256_file(p)
        out.append({"path": str(p), "sha256": digest,
                    "exists": digest is not None, "role": role})
    return out


def verify(manifest):
    """Re-hash every entry in ``manifest`` and classify it.

    Returns (ok, results) where results is a list of
    {path, role, status, expected, actual}. status is one of:
      ok       - present and hash matches the recorded value
      missing  - file no longer exists
      changed  - file exists but hash differs from the recorded value
      appeared - was recorded as absent but now exists (expected output produced)
    ``ok`` is True only when every input entry is "ok" and every output entry is
    "ok" or "appeared".
    """
    results = []
    all_ok = True
    for e in manifest:
        expected = e.get("sha256")
        actual = sha256_file(e["path"])
        role = e.get("role", "input")
        if actual is None:
            status = "missing"
        elif expected is None:
            status = "appeared"
        elif actual == expected:
            status = "ok"
        else:
            status = "changed"
        entry_ok = status == "ok" or (role == "output" and status == "appeared")
        all_ok = all_ok and entry_ok
        results.append({"path": e["path"], "role": role, "status": status,
                        "expected": expected, "actual": actual})
    return all_ok, results


class Manifest:
    """A persisted set of registered files for one analysis run."""

    def __init__(self, path):
        self.path = Path(path)

    def load(self):
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text())

    def add(self, paths, role="input"):
        entries = self.load()
        seen = {(e["path"], e.get("role", "input")) for e in entries}
        for new in register(paths, role=role):
            if (new["path"], new["role"]) not in seen:
                entries.append(new)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(entries, indent=2))
        return entries

    def verify(self):
        return verify(self.load())
