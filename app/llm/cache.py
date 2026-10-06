"""Disk cache of model replies, keyed by what can change the answer (ADR-0009).

The key hashes the prompt version, the model and the full request body, so a
new prompt, a new model or a different contract can never reuse an old reply
(Q-028). Files are JSON, one per key, and are committed so `make check` runs
offline.
"""

import hashlib
import json
import os
from collections.abc import Mapping
from pathlib import Path


def cache_key(prompt_version: str, model: str, body: Mapping[str, object]) -> str:
    """SHA-256 hex of the canonical JSON of prompt version, model and request body."""
    canonical = json.dumps(
        {"prompt": prompt_version, "model": model, "body": body},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


class ReplyCache:
    """Replies stored as `<key>.json` under one directory."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def get(self, key: str) -> dict[str, object] | None:
        """The stored reply for `key`, or None."""
        path = self.root / f"{key}.json"
        if not path.exists():
            return None
        try:
            data: dict[str, object] = json.loads(path.read_text())
        except json.JSONDecodeError:
            return None  # a half-written file is a miss; the next good reply replaces it
        return data

    def put(self, key: str, reply: Mapping[str, object]) -> None:
        """Store `reply` under `key`."""
        self.root.mkdir(parents=True, exist_ok=True)
        partial = self.root / f".{key}.tmp"
        partial.write_text(json.dumps(reply, indent=2, sort_keys=True) + "\n")
        os.replace(partial, self.root / f"{key}.json")  # atomic: never a half-written reply
