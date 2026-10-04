#!/usr/bin/env python3
"""Refresh the local FPL Vortex source dataset safely.

The first run bootstraps both the current season core CSVs and the previous
season match history from FPL Core Insights. Later runs refresh only the
current season plus any missing historical files. A failed download never
replaces a known-good local file.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import os
import sys
import urllib.request
from pathlib import Path

from fpl_common import DATA, PRIOR_SEASONS, SEASON

RAW_ROOT = "https://raw.githubusercontent.com/olbauday/FPL-Core-Insights/main/data"
CURRENT_DIR = Path(DATA) / SEASON
MATCH_ROOT = Path(DATA) / "matches"
CURRENT_DIR.mkdir(parents=True, exist_ok=True)
MATCH_ROOT.mkdir(parents=True, exist_ok=True)

REQUIRED = {
    "players.csv": ["player_id", "web_name", "position", "team_code"],
    "playerstats.csv": ["id", "now_cost", "selected_by_percent", "gw", "transfers_in_event", "transfers_out_event"],
    "teams.csv": ["code", "id", "short_name"],
    "gameweek_summaries.csv": ["id", "is_current"],
    "team_history.csv": ["player_id", "gw", "team_code"],
}
MATCH_COLS = ["gameweek", "home_team", "away_team", "home_score", "away_score", "finished", "match_id"]
USER_AGENT = "Mozilla/5.0 (compatible; fpl-vortex-website/1.0)"
log: list[str] = []


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/csv,*/*"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8")


def parsed_rows(text: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(text)))


def save_csv(path: Path, text: str, columns: list[str], shrink_check: bool = True) -> int:
    rows = parsed_rows(text)
    if not rows:
        raise ValueError("empty response")
    missing = [column for column in columns if column not in rows[0]]
    if missing:
        raise ValueError(f"missing columns {missing}")
    if shrink_check and path.exists():
        with path.open(encoding="utf-8") as handle:
            old_count = len(parsed_rows(handle.read()))
        if old_count > 1 and len(rows) < 0.8 * old_count:
            raise ValueError(f"rows dropped from {old_count} to {len(rows)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="")
    os.replace(tmp, path)
    return len(rows) - 1


def refresh_current_core() -> None:
    for name, columns in REQUIRED.items():
        url = f"{RAW_ROOT}/{SEASON}/{name}"
        target = CURRENT_DIR / name
        try:
            count = save_csv(target, fetch(url), columns)
            log.append(f"ok       {name} ({count} rows)")
        except Exception as exc:
            if target.exists():
                log.append(f"KEPT OLD {name} ({exc})")
            else:
                raise RuntimeError(f"Cannot bootstrap required {name}: {exc}") from exc


def current_last_gameweek() -> int:
    target = CURRENT_DIR / "playerstats.csv"
    with target.open(encoding="utf-8") as handle:
        values = [int(float(row["gw"])) for row in csv.DictReader(handle) if row.get("gw")]
    return max(values, default=0)


def refresh_match(season: str, gameweek: int, required: bool = False) -> None:
    target = MATCH_ROOT / season / f"GW{gameweek}.csv"
    if season != SEASON and target.exists():
        return
    url = f"{RAW_ROOT}/{season}/By%20Gameweek/GW{gameweek}/matches.csv"
    try:
        count = save_csv(target, fetch(url), MATCH_COLS, shrink_check=False)
        log.append(f"ok       matches {season} GW{gameweek} ({count} rows)")
    except Exception as exc:
        if target.exists():
            log.append(f"KEPT OLD matches {season} GW{gameweek} ({exc})")
        elif required:
            raise RuntimeError(f"Cannot bootstrap {season} GW{gameweek}: {exc}") from exc
        else:
            log.append(f"SKIPPED  matches {season} GW{gameweek} ({exc})")


def bootstrap_previous_seasons() -> None:
    for season in PRIOR_SEASONS:
        for gameweek in range(1, 39):
            refresh_match(season, gameweek, required=False)


refresh_current_core()
bootstrap_previous_seasons()
for gw in range(1, current_last_gameweek() + 1):
    refresh_match(SEASON, gw, required=True)

stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
(CURRENT_DIR / "UPDATE_LOG.txt").write_text(stamp + "\n" + "\n".join(log) + "\n", encoding="utf-8")
print(stamp)
print("\n".join(log))
sys.exit(0)
