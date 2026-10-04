#!/usr/bin/env python3
"""Fail fast if generated FPL Vortex data is structurally unsafe or implausible."""
from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data.json"


def finite(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def close_enough(left: float, right: float, tolerance: float = 0.06) -> bool:
    return abs(float(left) - float(right)) <= tolerance


data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
players = data.get("players")
teams = data.get("teams")
quality = data.get("quality", {})

assert isinstance(players, list) and len(players) > 300, "expected >300 players"
assert isinstance(teams, list) and len(teams) == 20, f"expected 20 teams, found {len(teams) if isinstance(teams, list) else 'invalid'}"
assert data.get("generated_iso"), "missing generated_iso"
assert int(data.get("schema_version", 0)) >= 2, "unexpected schema version"

# Generated timestamp must be parseable and must never be materially in the future.
generated = dt.datetime.fromisoformat(str(data["generated_iso"]).replace("Z", "+00:00"))
assert generated.tzinfo is not None, "generated_iso must include timezone"
assert generated <= dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=10), "generated_iso is unexpectedly in the future"

horizon = int(quality.get("projection_horizon", 0))
assert horizon == 5, f"expected five-gameweek horizon, got {horizon}"
events = data.get("events")
assert isinstance(events, list) and len(events) == horizon, "event horizon mismatch"
event_gws = [int(event.get("gw", 0)) for event in events]
assert event_gws == list(range(int(data.get("first_gw", 0)), int(data.get("first_gw", 0)) + horizon)), "events are not sequential"

team_names = [team.get("team") for team in teams]
assert len(set(team_names)) == 20, "duplicate team code/short name"
team_name_set = set(team_names)

player_ids: set[int] = set()
valid_positions = {"GKP", "DEF", "MID", "FWD"}
for player in players:
    player_id = player.get("id")
    assert isinstance(player_id, int) and player_id > 0, f"bad player id {player_id!r}"
    assert player_id not in player_ids, f"duplicate player id {player_id}"
    player_ids.add(player_id)
    assert player.get("pos") in valid_positions, f"bad position for {player.get('name')}"
    assert player.get("team") in team_name_set, f"unknown team for {player.get('name')}: {player.get('team')}"
    assert finite(player.get("price")) and 3.0 <= float(player["price"]) <= 20.0, f"implausible price {player.get('price')}"
    assert finite(player.get("own")) and 0 <= float(player["own"]) <= 100, f"bad ownership {player.get('own')}"
    assert finite(player.get("xpts")) and -1 <= float(player["xpts"]) <= 40, f"bad xpts {player.get('xpts')}"

    projections = player.get("projections")
    assert isinstance(projections, list) and len(projections) == horizon, f"projection horizon mismatch for {player.get('name')}"
    assert [int(item.get("gw", 0)) for item in projections] == event_gws, f"projection gameweeks mismatch for {player.get('name')}"
    assert all(finite(item.get("xpts")) and -5 <= float(item["xpts"]) <= 80 for item in projections), f"bad projections for {player.get('name')}"
    projection_sum = round(sum(float(item["xpts"]) for item in projections), 2)
    assert finite(player.get("projection_total")) and close_enough(player["projection_total"], projection_sum), f"projection total mismatch for {player.get('name')}"

    signal = player.get("price_signal")
    if signal:
        score = signal.get("score")
        assert finite(score) and -100 <= float(score) <= 100, f"bad price-pressure score for {player.get('name')}"

for team in teams:
    fixture_groups = team.get("fixtures")
    assert isinstance(fixture_groups, list) and len(fixture_groups) == horizon
    for group in fixture_groups:
        assert isinstance(group, list)
        for fixture in group:
            assert fixture.get("opp") in team_name_set, f"unknown opponent {fixture.get('opp')}"
            assert fixture.get("opp") != team.get("team"), f"self fixture for {team.get('team')}"
            for key in ("fdr", "fdr_att", "fdr_def", "fdr_all"):
                value = int(fixture.get(key, 0))
                assert 1 <= value <= 5, f"bad {key}: {value}"

assert quality.get("players") == len(players)
assert quality.get("teams") == len(teams)
assert int(quality.get("matches_used", 0)) > 100, "team model has too little match history"

if quality.get("official_api_available"):
    assert data.get("sources", {}).get("players") == "official_fpl_api", "official API available but player source is not official"

if quality.get("official_fixtures_available"):
    assert data.get("sources", {}).get("fixtures") == "official_fpl_api", "official fixtures available but fixture source is not official"
    assert any(team.get("avg") is not None for team in teams), "official fixtures marked available but no fixture ratings exist"
    chip_radar = data.get("chips")
    assert isinstance(chip_radar, list) and len(chip_radar) == 4, "expected all four chip radar recommendations"
    expected_chips = {"Wildcard radar", "Free Hit radar", "Bench Boost radar", "Triple Captain radar"}
    assert {item.get("chip") for item in chip_radar} == expected_chips, "chip radar is incomplete"
    for item in chip_radar:
        assert int(item.get("gw", 0)) in event_gws, f"chip radar GW outside planning horizon: {item}"
        assert finite(item.get("score")), f"chip radar score invalid: {item}"

chips = data.get("chip_rules", {})
assert chips.get("sets") == 2
assert chips.get("first_set_expires_after_gw") == 19
assert chips.get("second_set_starts_gw") == 20
assert chips.get("one_chip_per_gameweek") is True

print(
    f"validated: {len(players)} players, {len(teams)} teams, "
    f"{quality.get('matches_used')} model matches, fixtures={quality.get('official_fixtures_available')}, "
    f"chips={len(data.get('chips') or [])}, horizon={horizon}"
)
