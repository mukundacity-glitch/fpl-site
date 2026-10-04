#!/usr/bin/env python3
"""Collect price/transfer snapshots and build a transparent Vortex price-pressure signal."""
from __future__ import annotations

import bisect
import datetime as dt
import json
import os
from typing import Any

from fpl_common import DATA, read_json, num

HISTORY_DIR = os.path.join(DATA, "history")
SNAPSHOT_FILE = os.path.join(HISTORY_DIR, "price_snapshots.json")
SIGNAL_FILE = os.path.join(HISTORY_DIR, "price_signals.json")
BOOTSTRAP_FILE = os.path.join(DATA, "fpl_api", "bootstrap.json")
RETENTION_DAYS = 21
MAX_SNAPSHOTS = 96
os.makedirs(HISTORY_DIR, exist_ok=True)


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def parse_iso(value: str) -> dt.datetime | None:
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)
    except (TypeError, ValueError):
        return None


def percentile_score(values: list[float], value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = bisect.bisect_right(ordered, value) / len(ordered)
    return max(-100.0, min(100.0, (rank - 0.5) * 200.0))


def atomic_json(path: str, payload: Any) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, separators=(",", ":"))
    os.replace(tmp, path)


bootstrap = read_json(BOOTSTRAP_FILE)
if not isinstance(bootstrap, dict) or not bootstrap.get("elements"):
    print("price history: bootstrap.json missing; kept existing history")
    raise SystemExit(0)

now = utc_now()
now_iso = now.isoformat().replace("+00:00", "Z")
players: dict[str, dict[str, float]] = {}
for element in bootstrap["elements"]:
    player_id = str(element.get("id"))
    players[player_id] = {
        "price": num(element.get("now_cost")) / 10.0,
        "own": num(element.get("selected_by_percent")),
        "net": num(element.get("transfers_in_event")) - num(element.get("transfers_out_event")),
    }

existing = read_json(SNAPSHOT_FILE, [])
snapshots = existing if isinstance(existing, list) else []
cutoff = now - dt.timedelta(days=RETENTION_DAYS)
kept: list[dict[str, Any]] = []
for snapshot in snapshots:
    stamp = parse_iso(str(snapshot.get("at", "")))
    if stamp and stamp >= cutoff and isinstance(snapshot.get("players"), dict):
        kept.append(snapshot)

if kept:
    last_stamp = parse_iso(str(kept[-1].get("at", "")))
    if last_stamp and (now - last_stamp).total_seconds() < 300:
        kept[-1] = {"at": now_iso, "players": players}
    else:
        kept.append({"at": now_iso, "players": players})
else:
    kept.append({"at": now_iso, "players": players})
kept = kept[-MAX_SNAPSHOTS:]
atomic_json(SNAPSHOT_FILE, kept)

previous = kept[-2] if len(kept) >= 2 else None
previous_players = previous.get("players", {}) if previous else {}
previous_at = parse_iso(str(previous.get("at", ""))) if previous else None
hours = max((now - previous_at).total_seconds() / 3600.0, 0.25) if previous_at else None

current_nets = [record["net"] for record in players.values()]
velocities: dict[str, float] = {}
if hours:
    for player_id, current in players.items():
        prior = previous_players.get(player_id)
        if isinstance(prior, dict):
            velocities[player_id] = (current["net"] - num(prior.get("net"))) / hours
velocity_values = list(velocities.values())

signals: dict[str, Any] = {"generated": now_iso, "samples": len(kept), "sample_hours": round(hours, 2) if hours else None, "players": {}}
for player_id, current in players.items():
    flow_score = percentile_score(current_nets, current["net"])
    velocity = velocities.get(player_id)
    velocity_score = percentile_score(velocity_values, velocity) if velocity is not None else flow_score
    score = int(round(0.72 * flow_score + 0.28 * velocity_score))
    prior = previous_players.get(player_id) if isinstance(previous_players, dict) else None
    price_change = round(current["price"] - num(prior.get("price")), 1) if isinstance(prior, dict) else 0.0
    direction = "rise" if score >= 20 else "fall" if score <= -20 else "stable"
    magnitude = abs(score)
    pressure = "very high" if magnitude >= 85 else "high" if magnitude >= 70 else "watch" if magnitude >= 50 else "low"
    signals["players"][player_id] = {
        "score": score,
        "direction": direction,
        "pressure": pressure,
        "velocity_per_hour": round(velocity, 1) if velocity is not None else None,
        "price_change_since_last": price_change,
    }

atomic_json(SIGNAL_FILE, signals)
print(f"price history: {len(players)} players, {len(kept)} snapshots, signals updated")
