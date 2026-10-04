#!/usr/bin/env python3
"""Save pre-deadline ep_next predictions and evaluate them after a gameweek finishes."""
from __future__ import annotations

import json
import os
import statistics
from typing import Any

from fpl_common import DATA, read_json, num

API_DIR = os.path.join(DATA, "fpl_api")
HISTORY_DIR = os.path.join(DATA, "history")
PREDICTION_DIR = os.path.join(HISTORY_DIR, "predictions")
ACCURACY_FILE = os.path.join(HISTORY_DIR, "accuracy.json")
os.makedirs(PREDICTION_DIR, exist_ok=True)


def atomic_json(path: str, payload: Any, pretty: bool = False) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2 if pretty else None, separators=None if pretty else (",", ":"))
    os.replace(tmp, path)


bootstrap = read_json(os.path.join(API_DIR, "bootstrap.json"))
if not isinstance(bootstrap, dict) or not bootstrap.get("elements") or not bootstrap.get("events"):
    print("accuracy: bootstrap.json missing; kept existing history")
    raise SystemExit(0)

events = bootstrap["events"]
next_event = next((event for event in events if event.get("is_next")), None)
if next_event:
    gw = int(next_event["id"])
    payload = {
        "gw": gw,
        "generated": str(bootstrap.get("last_updated_data") or ""),
        "source": "FPL ep_next",
        "players": {
            str(element["id"]): round(num(element.get("ep_next")), 3)
            for element in bootstrap["elements"]
            if element.get("id") is not None
        },
    }
    atomic_json(os.path.join(PREDICTION_DIR, f"GW{gw}.json"), payload)
    print(f"accuracy: saved latest pre-GW{gw} prediction snapshot")

existing = read_json(ACCURACY_FILE, [])
records = existing if isinstance(existing, list) else []
by_gw = {int(record["gw"]): record for record in records if isinstance(record, dict) and "gw" in record}
finished = {int(event["id"]) for event in events if event.get("finished") or event.get("data_checked")}

for gw in sorted(finished):
    prediction = read_json(os.path.join(PREDICTION_DIR, f"GW{gw}.json"))
    live = read_json(os.path.join(API_DIR, "live", f"GW{gw}.json"))
    if not isinstance(prediction, dict) or not isinstance(live, dict):
        continue
    predicted = prediction.get("players", {})
    live_elements = live.get("elements", [])
    if not isinstance(predicted, dict) or not isinstance(live_elements, list):
        continue

    errors: list[float] = []
    predicted_values: list[float] = []
    actual_values: list[float] = []
    for element in live_elements:
        player_id = str(element.get("id"))
        if player_id not in predicted:
            continue
        stats = element.get("stats") or {}
        actual = num(stats.get("total_points"), None)
        forecast = num(predicted.get(player_id), None)
        if actual is None or forecast is None:
            continue
        errors.append(abs(forecast - actual))
        predicted_values.append(forecast)
        actual_values.append(actual)

    if not errors:
        continue
    by_gw[gw] = {
        "gw": gw,
        "mae": round(sum(errors) / len(errors), 3),
        "median_abs_error": round(statistics.median(errors), 3),
        "players": len(errors),
        "mean_prediction": round(sum(predicted_values) / len(predicted_values), 3),
        "mean_actual": round(sum(actual_values) / len(actual_values), 3),
        "source": str(prediction.get("source", "FPL ep_next")),
    }

records = [by_gw[gw] for gw in sorted(by_gw)]
atomic_json(ACCURACY_FILE, records, pretty=True)
print(f"accuracy: {len(records)} completed gameweek evaluations available")
