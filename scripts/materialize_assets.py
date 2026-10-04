#!/usr/bin/env python3
"""Materialize the exact user-supplied FPL Vortex logo from text-safe chunks."""
from __future__ import annotations

import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
parts = [ASSETS / f"logo-part{index}.txt" for index in range(1, 5)]
for part in parts:
    if not part.exists():
        raise RuntimeError(f"Missing logo source chunk: {part.name}")

encoded = "".join(part.read_text(encoding="utf-8").strip() for part in parts)
if len(encoded) != 8160:
    raise RuntimeError(f"Unexpected logo base64 length: {len(encoded)}")
raw = base64.b64decode(encoded, validate=True)
if len(raw) != 6120 or not raw.startswith(b"\xff\xd8\xff") or not raw.endswith(b"\xff\xd9"):
    raise RuntimeError("FPL Vortex logo source did not decode to the expected JPEG")

target = ASSETS / "fpl-vortex-logo.jpg"
target.write_bytes(raw)
print(f"materialized {target.relative_to(ROOT)} ({len(raw)} bytes)")
