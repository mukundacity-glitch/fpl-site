#!/usr/bin/env python3
"""Build the public FPL Vortex website dataset.

The generated JSON intentionally separates official FPL fields from Vortex-derived
analytics. Official API data is preferred when available; validated local CSV data is
used as a last-known-good fallback.
"""
from __future__ import annotations

import datetime as dt
import glob
import json
import math
import os
from typing import Any

from fpl_common import DATA, ROOT, SEASON, PRIOR_SEASONS, read_csv, read_json, num, code_of
import vortex_model as vm

HORIZON = 5
API = os.path.join(DATA, "fpl_api")
HISTORY = os.path.join(DATA, "history")
CORE_DIR = os.path.join(DATA, SEASON)
POS_API = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
POS_CORE = {"Goalkeeper": "GKP", "Defender": "DEF", "Midfielder": "MID", "Forward": "FWD"}
FDR_MULTIPLIER = {1: 1.25, 2: 1.12, 3: 1.00, 4: 0.88, 5: 0.76}

boot = read_json(os.path.join(API, "bootstrap.json"))
fixt = read_json(os.path.join(API, "fixtures.json"))
price_signals = read_json(os.path.join(HISTORY, "price_signals.json"), {}) or {}
price_by_id = price_signals.get("players", {}) if isinstance(price_signals, dict) else {}
accuracy = read_json(os.path.join(HISTORY, "accuracy.json"), []) or []


def require_file(path: str) -> None:
    if not os.path.exists(path):
        raise RuntimeError(f"Required fallback data is missing: {path}")


for required in ("teams.csv", "players.csv", "playerstats.csv"):
    require_file(os.path.join(CORE_DIR, required))

if isinstance(boot, dict) and boot.get("teams"):
    teams = [{"id": str(t["id"]), "code": code_of(t["code"]), "short": t["short_name"], "name": t["name"]} for t in boot["teams"]]
else:
    teams = [{"id": str(t["id"]), "code": code_of(t["code"]), "short": t["short_name"], "name": t["name"]} for t in read_csv(os.path.join(CORE_DIR, "teams.csv"))]

id2code = {t["id"]: t["code"] for t in teams}
code2short = {t["code"]: t["short"] for t in teams}
current_codes = [t["code"] for t in teams]


def load_matches(season: str, weight: float) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for path in glob.glob(os.path.join(DATA, "matches", season, "GW*.csv")):
        for row in read_csv(path):
            if "-prem-" not in row.get("match_id", "") or row.get("finished") != "True":
                continue
            home_goals = num(row.get("home_score"), None)
            away_goals = num(row.get("away_score"), None)
            if home_goals is None or away_goals is None:
                continue
            home_xg = num(row.get("home_expected_goals_xg"), None)
            away_xg = num(row.get("away_expected_goals_xg"), None)
            home_target = vm.XG_SHARE * home_xg + (1 - vm.XG_SHARE) * home_goals if home_xg is not None else home_goals
            away_target = vm.XG_SHARE * away_xg + (1 - vm.XG_SHARE) * away_goals if away_xg is not None else away_goals
            output.append({"home": code_of(row.get("home_team")), "away": code_of(row.get("away_team")), "hy": home_target, "ay": away_target, "w": weight})
    return output


matches = load_matches(SEASON, vm.SEASON_WEIGHT.get(SEASON, 1.0))
seen_before: set[str] = set()
for season in PRIOR_SEASONS:
    prior = load_matches(season, vm.SEASON_WEIGHT.get(season, 0.4))
    seen_before |= {m["home"] for m in prior} | {m["away"] for m in prior}
    matches += prior
promoted = [code for code in current_codes if code not in seen_before]
model = vm.fit(matches, current_codes, promoted)
reference = vm.reference(model, current_codes)
ratings = sorted(({"team": code2short[code], "attack": round(100 * math.exp(model["att"][code])), "defence": round(100 * math.exp(model["dfn"][code]))} for code in current_codes), key=lambda row: -(row["attack"] + row["defence"]))

stats_all = read_csv(os.path.join(CORE_DIR, "playerstats.csv"))
core_gw = max((int(num(row.get("gw"))) for row in stats_all), default=0)
events: list[dict[str, Any]] = []
if isinstance(boot, dict) and boot.get("events"):
    current = next((event["id"] for event in boot["events"] if event.get("is_current")), None)
    next_event = next((event["id"] for event in boot["events"] if event.get("is_next")), None)
    gw = int(current or core_gw)
    first_gw = int(next_event or gw + 1)
    for event in boot["events"]:
        if first_gw <= int(event["id"]) < first_gw + HORIZON:
            events.append({"gw": int(event["id"]), "name": event.get("name") or f"Gameweek {event['id']}", "deadline": event.get("deadline_time"), "finished": bool(event.get("finished"))})
else:
    gw = core_gw
    first_gw = gw + 1
    events = [{"gw": first_gw + offset, "name": f"Gameweek {first_gw + offset}", "deadline": None, "finished": False} for offset in range(HORIZON)]

team_fx: dict[str, list[list[dict[str, Any]]]] = {team["code"]: [[] for _ in range(HORIZON)] for team in teams}
if isinstance(fixt, list):
    for fixture in fixt:
        event = fixture.get("event")
        if event is None or not (first_gw <= int(event) < first_gw + HORIZON) or fixture.get("finished"):
            continue
        home = id2code.get(str(fixture.get("team_h")))
        away = id2code.get(str(fixture.get("team_a")))
        if not home or not away:
            continue
        for team, opponent, is_home in ((home, away, True), (away, home, False)):
            difficulty = vm.fixture_difficulty(model, reference, team, opponent, is_home)
            difficulty.update({"opp": code2short[opponent], "h": is_home, "fdr": difficulty["fdr_all"], "event": int(event)})
            team_fx[team][int(event) - first_gw].append(difficulty)

teams_out: list[dict[str, Any]] = []
for team in teams:
    flat = [fixture for gameweek in team_fx[team["code"]] for fixture in gameweek]
    teams_out.append({"team": team["short"], "name": team["name"], "fixtures": team_fx[team["code"]], "avg": round(sum(fixture["fdr_all"] for fixture in flat) / len(flat), 2) if flat else None})
teams_out.sort(key=lambda row: (row["avg"] is None, row["avg"] if row["avg"] is not None else 99))


def fixtures_for(team_code: str, position: str) -> list[dict[str, Any]]:
    key = "fdr_att" if position in ("MID", "FWD") else "fdr_def"
    return [dict(fixture, fdr=fixture[key]) for gameweek in team_fx.get(team_code, []) for fixture in gameweek]


def projections_for(team_code: str, position: str, ep_next: float, form: float, ppg: float, chance: float | None) -> list[dict[str, Any]]:
    availability = 1.0 if chance is None else max(0.0, min(1.0, chance / 100.0))
    base = max(0.0, 0.55 * ep_next + 0.30 * form + 0.15 * ppg)
    key = "fdr_att" if position in ("MID", "FWD") else "fdr_def"
    output: list[dict[str, Any]] = []
    for offset, gameweek_fixtures in enumerate(team_fx.get(team_code, [[] for _ in range(HORIZON)])):
        event = first_gw + offset
        if not gameweek_fixtures:
            projected = 0.0 if isinstance(fixt, list) else (ep_next if offset == 0 else base)
        elif offset == 0 and ep_next >= 0:
            projected = ep_next
        else:
            projected = sum(base * FDR_MULTIPLIER.get(int(fixture[key]), 1.0) for fixture in gameweek_fixtures)
        output.append({"gw": event, "xpts": round(projected * availability, 2), "fixtures": [{"opp": fixture["opp"], "h": fixture["h"], "fdr": fixture[key]} for fixture in gameweek_fixtures]})
    return output


def chip_radar() -> list[dict[str, Any]]:
    if not isinstance(fixt, list):
        return []
    windows: list[dict[str, Any]] = []
    for offset in range(HORIZON):
        gameweek_groups = [team_fx[team["code"]][offset] for team in teams]
        blanks = sum(1 for fixtures in gameweek_groups if len(fixtures) == 0)
        doubles = sum(1 for fixtures in gameweek_groups if len(fixtures) > 1)
        flat = [fixture for fixtures in gameweek_groups for fixture in fixtures]
        if not flat:
            continue
        average = sum(fixture["fdr_all"] for fixture in flat) / len(flat)
        attack_options = [(fixture["fdr_att"], team["short"]) for team in teams for fixture in team_fx[team["code"]][offset]]
        best_attack = min(attack_options) if attack_options else (5, "—")
        easy_teams = sum(1 for team in teams if team_fx[team["code"]][offset] and min(fixture["fdr_all"] for fixture in team_fx[team["code"]][offset]) <= 2)
        windows.append({"gw": first_gw + offset, "blanks": blanks, "doubles": doubles, "avg": average, "easy_teams": easy_teams, "best_attack_fdr": best_attack[0], "best_attack_team": best_attack[1]})
    if not windows:
        return []
    free_hit_windows = [window for window in windows if window["gw"] != 1]
    if not free_hit_windows:
        free_hit_windows = windows
    free_hit = max(free_hit_windows, key=lambda window: window["blanks"] * 3 + window["doubles"] * 2 + window["easy_teams"] * 0.35)
    bench_boost = max(windows, key=lambda window: window["doubles"] * 4 + window["easy_teams"] * 0.4 + max(0.0, 3.2 - window["avg"]))
    triple_captain = max(windows, key=lambda window: (2 if window["doubles"] else 0) + (6 - window["best_attack_fdr"]) + window["easy_teams"] * 0.12)
    wildcard_candidates: list[tuple[float, int, int]] = []
    for start in range(len(windows)):
        remaining = windows[start:]
        if remaining:
            score = sum(window["easy_teams"] * 0.3 + window["doubles"] * 0.9 - window["blanks"] * 0.35 for window in remaining) / len(remaining)
            wildcard_candidates.append((score, windows[start]["gw"], len(remaining)))
    _, wildcard_gw, wildcard_span = max(wildcard_candidates)
    return [
        {"chip": "Wildcard radar", "gw": wildcard_gw, "score": round(max(score for score, _, _ in wildcard_candidates), 2), "note": f"Best fixture reset point across the next {wildcard_span} tracked GWs"},
        {"chip": "Free Hit radar", "gw": free_hit["gw"], "score": round(free_hit["blanks"] * 3 + free_hit["doubles"] * 2 + free_hit["easy_teams"] * 0.35, 2), "note": f"{free_hit['blanks']} blank teams · {free_hit['doubles']} double teams"},
        {"chip": "Bench Boost radar", "gw": bench_boost["gw"], "score": round(bench_boost["doubles"] * 4 + bench_boost["easy_teams"] * 0.4, 2), "note": f"{bench_boost['doubles']} double teams · {bench_boost['easy_teams']} teams with an easy fixture"},
        {"chip": "Triple Captain radar", "gw": triple_captain["gw"], "score": round((6 - triple_captain["best_attack_fdr"]) + (2 if triple_captain["doubles"] else 0), 2), "note": f"Best attacking fixture: {triple_captain['best_attack_team']}"},
    ]


players: list[dict[str, Any]] = []
if isinstance(boot, dict) and boot.get("elements"):
    source = "official_fpl_api"
    for element in boot["elements"]:
        if num(element.get("minutes")) <= 0 and num(element.get("ep_next")) <= 0:
            continue
        position = POS_API.get(element.get("element_type"), "?")
        team_code = id2code.get(str(element.get("team")), "")
        ep_next, form, ppg = num(element.get("ep_next")), num(element.get("form")), num(element.get("points_per_game"))
        chance_value = element.get("chance_of_playing_next_round")
        chance = num(chance_value, None) if chance_value is not None else None
        projections = projections_for(team_code, position, ep_next, form, ppg, chance)
        players.append({"id": int(element["id"]), "name": element.get("web_name") or "Unknown", "team": code2short.get(team_code, "?"), "team_id": int(element.get("team") or 0), "pos": position, "price": num(element.get("now_cost")) / 10.0, "own": num(element.get("selected_by_percent")), "form": form, "ppg": ppg, "xpts": ep_next, "projection_total": round(sum(item["xpts"] for item in projections), 2), "projections": projections, "net": int(num(element.get("transfers_in_event")) - num(element.get("transfers_out_event"))), "status": element.get("status") or "u", "chance": chance, "news": element.get("news") or "", "fixtures": fixtures_for(team_code, position), "price_signal": price_by_id.get(str(element["id"]))})
else:
    source = "validated_core_csv_fallback"
    player_meta = {player["player_id"]: player for player in read_csv(os.path.join(CORE_DIR, "players.csv"))}
    for stat in stats_all:
        if int(num(stat.get("gw"))) != core_gw or stat.get("id") not in player_meta:
            continue
        meta = player_meta[stat["id"]]
        position = POS_CORE.get(meta.get("position"), "?")
        team_code = code_of(meta.get("team_code"))
        ep_next, form = num(stat.get("ep_next")), num(stat.get("form"))
        ppg = num(stat.get("points_per_game"), form)
        chance_value = stat.get("chance_of_playing_next_round")
        chance = num(chance_value, None) if chance_value not in (None, "") else None
        projections = projections_for(team_code, position, ep_next, form, ppg, chance)
        players.append({"id": int(float(stat["id"])), "name": meta.get("web_name") or "Unknown", "team": code2short.get(team_code, "?"), "team_id": int(float(meta.get("team_id") or 0)) if meta.get("team_id") else 0, "pos": position, "price": num(stat.get("now_cost")), "own": num(stat.get("selected_by_percent")), "form": form, "ppg": ppg, "xpts": ep_next, "projection_total": round(sum(item["xpts"] for item in projections), 2), "projections": projections, "net": int(num(stat.get("transfers_in_event")) - num(stat.get("transfers_out_event"))), "status": stat.get("status") or "u", "chance": chance, "news": stat.get("news") or "", "fixtures": fixtures_for(team_code, position), "price_signal": price_by_id.get(str(stat["id"]))})

players.sort(key=lambda row: (-row["xpts"], -row["projection_total"], row["price"]))
fixture_source = "official_fpl_api" if isinstance(fixt, list) else "missing_until_api_refresh"
now = dt.datetime.now(dt.timezone.utc)
output = {
    "schema_version": 2, "season": SEASON.replace("-", "/"), "gw": gw, "first_gw": first_gw, "events": events,
    "generated": now.strftime("%Y-%m-%d %H:%M UTC"), "generated_iso": now.isoformat().replace("+00:00", "Z"),
    "sources": {"players": source, "fixtures": fixture_source, "team_model": "Vortex xG/results model"},
    "xpts_source": "Official FPL ep_next for the next GW; transparent Vortex fixture-adjusted projection for later GWs",
    "fdr_name": "Vortex FDR", "fdr_scale": vm.SCALE,
    "projection_method": {"next_gw": "official FPL ep_next", "future_gws": "55% ep_next + 30% form + 15% points-per-game, adjusted by Vortex position-specific FDR and availability", "fdr_multipliers": FDR_MULTIPLIER},
    "chip_rules": {"season": "2026/27", "chips": ["Wildcard", "Free Hit", "Bench Boost", "Triple Captain"], "sets": 2, "first_set_expires_after_gw": 19, "second_set_starts_gw": 20, "one_chip_per_gameweek": True, "wildcard_not_allowed_gw1": True, "free_hit_not_allowed_gw1": True, "free_hit_not_consecutive": True},
    "ratings": ratings, "teams": teams_out, "players": players, "chips": chip_radar(), "accuracy": accuracy,
    "automation": {"price_snapshots": price_signals.get("samples", 0) if isinstance(price_signals, dict) else 0, "price_signal_generated": price_signals.get("generated") if isinstance(price_signals, dict) else None},
    "quality": {"players": len(players), "teams": len(teams), "matches_used": len(matches), "official_api_available": isinstance(boot, dict) and bool(boot.get("elements")), "official_fixtures_available": isinstance(fixt, list), "projection_horizon": HORIZON, "promoted_prior_teams": [code2short.get(code, code) for code in promoted]},
}

with open(os.path.join(ROOT, "data.json"), "w", encoding="utf-8") as handle:
    json.dump(output, handle, separators=(",", ":"), ensure_ascii=False)
with open(os.path.join(DATA, "ratings.json"), "w", encoding="utf-8") as handle:
    json.dump({"generated": output["generated"], "ratings": ratings, "matches_used": len(matches), "promoted_prior_teams": output["quality"]["promoted_prior_teams"]}, handle, indent=2, ensure_ascii=False)

print("data.json: GW%d (next GW%d), %d players, %d matches, players=%s, fixtures=%s" % (gw, first_gw, len(players), len(matches), source, fixture_source))
