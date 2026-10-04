import csv, json, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data")
SEASON = os.environ.get("SEASON", "2026-2027")
PRIOR_SEASONS = ["2025-2026"]

def read_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))

def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def num(x, d=0.0):
    try:
        v = float(x)
        return d if v != v else v
    except (TypeError, ValueError):
        return d

def code_of(x):
    """'43.0' -> '43' so team codes match across files."""
    try:
        return str(int(float(x)))
    except (TypeError, ValueError):
        return ""
