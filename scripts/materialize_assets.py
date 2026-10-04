#!/usr/bin/env python3
"""Materialize the exact user-supplied FPL Vortex logo from text-safe chunks."""
from __future__ import annotations

import base64
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
parts = [
    ASSETS / "logo-part1a1.txt",
    ASSETS / "logo-part1a2.txt",
    ASSETS / "logo-part1a3.txt",
    ASSETS / "logo-part1a4.txt",
    ASSETS / "logo-part1b.txt",
    ASSETS / "logo-part2.txt",
    ASSETS / "logo-part3.txt",
    ASSETS / "logo-part4.txt",
]
for part in parts:
    if not part.exists():
        raise RuntimeError(f"Missing logo source chunk: {part.name}")

encoded = "".join(part.read_text(encoding="utf-8").strip() for part in parts)
if len(encoded) != 8160:
    raise RuntimeError(f"Unexpected logo base64 length: {len(encoded)}")
raw = base64.b64decode(encoded, validate=True)
sha256 = hashlib.sha256(raw).hexdigest()
expected_sha256 = "0df6d6c1652f539fa2f2c879ea5cdedf3d3bee63fb37d59a25deec4b12e18228"
if len(raw) != 6120 or not raw.startswith(b"\xff\xd8\xff") or not raw.endswith(b"\xff\xd9") or sha256 != expected_sha256:
    raise RuntimeError(f"FPL Vortex logo checksum mismatch: {sha256}")

target = ASSETS / "fpl-vortex-logo.jpg"
target.write_bytes(raw)
print(f"materialized {target.relative_to(ROOT)} ({len(raw)} bytes, sha256={sha256})")
