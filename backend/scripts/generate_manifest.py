#!/usr/bin/env python3
"""
Generate backend/release_manifest.json with SHA256 checksums and test status.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_files() -> List[Dict]:
    out = []
    for p in sorted(BACKEND.rglob("*")):
        if p.is_dir():
            continue
        # skip venv/cache
        if any(part in ("__pycache__", ".pytest_cache") for part in p.parts):
            continue
        rel = p.relative_to(ROOT).as_posix()
        out.append(
            {
                "path": rel,
                "sha256": sha256_file(p),
                "bytes": p.stat().st_size,
            }
        )
    return out


def main():
    manifest_path = BACKEND / "release_manifest.json"
    data = {
        "release_branch": "release/backend-next",
        "generated_from": str(ROOT),
        "artifacts": collect_files(),
        "tests": {
            "unit_pytest": os.getenv("MANIFEST_PYTEST_STATUS", "unknown"),
            "e2e_smoke": os.getenv("MANIFEST_E2E_STATUS", "unknown"),
        },
    }
    manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Wrote {manifest_path}")


if __name__ == "__main__":
    main()

