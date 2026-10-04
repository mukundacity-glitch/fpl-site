#!/usr/bin/env python3
"""Fail fast if generated FPL Vortex data is structurally unsafe or implausible."""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data.json"


def finite(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
players = data.get("players")
teams = data.get("teams")
assert isinstance(players, list) and len(players) > 300, "expected >300 players"
assert isinstance(teams, list) and len(teams) == 20, f"expected 20 teams, found {len(teams) if isinstance(teams, list) else 'invalid'}"
assert data.get("generated_iso"), "missing generated_iso"
assert int(data.get("schema_version", 0)) >= 2, "unexpected schema version"

player_ids: set[int] = set()
valid_positions = {"GKP", "DEF", "MID", "FWD"}
team_names = {team.get("team") for team in teams}
for player in players:
    player_id = player.get("id")
    assert isinstance(player_id, int) and player_id > 0, f"bad player id {player_id!r}"
    assert player_id not in player_ids, f"duplicate player id {player_id}"
    player_ids.add(player_id)
    assert player.get("pos") in valid_positions, f"bad position for {player.get('name')}"
    assert player.get("team") in team_names, f"unknown team for {player.get('name')}: {player.get('team')}"
    assert finite(player.get("price")) and 3.0 <= float(player["price"]) <= 20.0, f"implausible price {player.get('price')}"
    assert finite(player.get("own")) and 0 <= float(player["own"]) <= 100, f"bad ownership {player.get('own')}"
    assert finite(player.get("xpts")) and -1 <= float(player["xpts"]) <= 40, f"bad xpts {player.get('xpts')}"
    projections = player.get("projections")
    assert isinstance(projections, list) and len(projections) == int(data["quality"]["projection_horizon"]), f"projection horizon mismatch for {player.get('name')}"
    assert all(finite(item.get("xpts")) and -5 <= float(item["xpts"]) <= 80 for item in projections), f"bad projections for {player.get('name')}"

for team in teams:
    fixture_groups = team.get("fixtures")
    assert isinstance(fixture_groups, list) and len(fixture_groups) == int(data["quality"]["projection_horizon"])
    for group in fixture_groups:
        assert isinstance(group, list)
        for fixture in group:
            assert fixture.get("opp") in team_names, f"unknown opponent {fixture.get('opp')}"
            for key in ("fdr", "fdr_att", "fdr_def", "fdr_all"):
                value = int(fixture.get(key, 0))
                assert 1 <= value <= 5, f"bad {key}: {value}"

quality = data.get("quality", {})
assert quality.get("players") == len(players)
assert quality.get("teams") == len(teams)
assert int(quality.get("matches_used", 0)) > 100, "team model has too little match history"

if quality.get("official_fixtures_available"):
    assert any(team.get("avg") is not None for team in teams), "official fixtures marked available but no fixture ratings exist"

chips = data.get("chip_rules", {})
assert chips.get("sets") == 2
assert chips.get("first_set_expires_after_gw") == 19
assert chips.get("second_set_starts_gw") == 20
assert chips.get("one_chip_per_gameweek") is True

print(f"validated: {len(players)} players, {len(teams)} teams, {quality.get('matches_used')} model matches, fixtures={quality.get('official_fixtures_available')}")
