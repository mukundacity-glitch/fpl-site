#!/usr/bin/env python3
"""Fetch and validate official FPL API data while preserving the last good copy."""
from __future__ import annotations

import json
import os
import time
import urllib.request
from typing import Any, Callable

from fpl_common import DATA, read_json

BASE = "https://fantasy.premierleague.com/api/"
UA = "Mozilla/5.0 (compatible; fpl-vortex-website/1.0)"
OUT = os.path.join(DATA, "fpl_api")
LIVE = os.path.join(OUT, "live")
os.makedirs(OUT, exist_ok=True)
os.makedirs(LIVE, exist_ok=True)


def ok_bootstrap(data: Any) -> bool:
    return isinstance(data, dict) and len(data.get("elements", [])) > 300 and len(data.get("teams", [])) >= 18 and bool(data.get("events"))


def ok_fixtures(data: Any) -> bool:
    return isinstance(data, list) and len(data) >= 300 and all("team_h" in item and "team_a" in item for item in data[:20])


def ok_live(data: Any) -> bool:
    return isinstance(data, dict) and len(data.get("elements", [])) > 300


def request_json(path: str, check: Callable[[Any], bool]) -> Any | None:
    for attempt in range(3):
        try:
            request = urllib.request.Request(BASE + path, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(request, timeout=45) as response:
                data = json.loads(response.read().decode("utf-8"))
            if check(data):
                return data
            print(f"{path}: response failed checks (attempt {attempt + 1})")
        except Exception as exc:
            print(f"{path}: {exc} (attempt {attempt + 1})")
        time.sleep(2 * (attempt + 1))
    return None


def save_if_good(name: str, path: str, check: Callable[[Any], bool]) -> Any | None:
    data = request_json(path, check)
    target = os.path.join(OUT, name)
    if data is None:
        print(f"KEPT OLD  {name}")
        return read_json(target)
    tmp = target + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, separators=(",", ":"))
    os.replace(tmp, target)
    print(f"ok        {name}")
    return data


bootstrap = save_if_good("bootstrap.json", "bootstrap-static/", ok_bootstrap)
save_if_good("fixtures.json", "fixtures/", ok_fixtures)

if isinstance(bootstrap, dict):
    candidates = [
        int(event["id"])
        for event in bootstrap.get("events", [])
        if event.get("is_current") or event.get("finished") or event.get("data_checked")
    ][-3:]
    for gw in candidates:
        data = request_json(f"event/{gw}/live/", ok_live)
        target = os.path.join(LIVE, f"GW{gw}.json")
        if data is None:
            print(f"KEPT OLD  live/GW{gw}.json")
            continue
        tmp = target + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(data, handle, separators=(",", ":"))
        os.replace(tmp, target)
        print(f"ok        live/GW{gw}.json")
