#!/usr/bin/env python3
"""Validate the exact review-branch frontend before data refresh/commit."""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
html = (ROOT / "index.html").read_text(encoding="utf-8")

required = [
    "assets/fpl-vortex-logo.jpg",
    "Overview",
    "Captain",
    "Transfers",
    "5GW Plan",
    "Price pressure",
    "Fixtures",
    "Chip planner",
    "My Team Lab",
    "Accuracy",
    "Data quality",
    "data.json",
]
for needle in required:
    assert needle in html, f"frontend is missing required UI marker: {needle}"

scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", html, flags=re.S | re.I)
assert scripts, "no inline JavaScript found"
combined = "\n".join(scripts)

# window.top is a restricted browser global. A top-level lexical declaration
# can pass Node parsing but prevent the entire browser script from starting.
for forbidden in ("const top=", "let top=", "var top="):
    assert forbidden not in combined, f"browser-global collision in frontend: {forbidden}"
with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as handle:
    handle.write(combined)
    js_path = handle.name

try:
    subprocess.run(["node", "--check", js_path], check=True)
    subprocess.run(["node", "--check", str(ROOT / "functions" / "api" / "manager.js")], check=True)
finally:
    Path(js_path).unlink(missing_ok=True)

print("frontend validated: required sections present; browser and manager-proxy JavaScript parse cleanly")
