#!/usr/bin/env python3
"""Materialize binary web assets from repository-safe text sources."""
from __future__ import annotations

import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
encoded = ROOT / "assets" / "logo-data.txt"
target = ROOT / "assets" / "fpl-vortex-logo.jpg"
raw = base64.b64decode(encoded.read_text(encoding="utf-8").strip(), validate=True)
if not raw.startswith(b"\xff\xd8\xff"):
    raise RuntimeError("FPL Vortex logo source did not decode to JPEG")
target.write_bytes(raw)
print(f"materialized {target.relative_to(ROOT)} ({len(raw)} bytes)")
