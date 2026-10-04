# FPL VORTEX WEBSITE

Review-ready, zero-build Fantasy Premier League decision dashboard for the **FPL VORTEX** channel.

> **Deployment status:** intentionally **not published yet**. This repository is being prepared and verified first. Hosting can be connected only after review/approval.

## What the site does

- Uses the supplied FPL VORTEX lion/crown logo and channel branding.
- Loads `data.json` automatically; no upload button is needed for normal hosted use.
- Ranks captain and vice-captain candidates.
- Shows transparent five-Gameweek player projections.
- Finds transfer value, differentials and market momentum.
- Builds Vortex attack/defence/overall fixture difficulty from match history.
- Detects blanks and doubles from the official FPL fixture API.
- Tracks price **pressure** from repeated official transfer-flow snapshots.
- Stores prediction history and evaluates it after completed Gameweeks.
- Includes a 2026/27 chip radar for Wildcard, Free Hit, Bench Boost and Triple Captain.
- Includes **My Team Lab**: enter a public FPL Team ID to simulate squad-aware chip value using current squad, selling-value budget and chip history.
- Keeps last-known-good data when an upstream request fails validation.

## 2026/27 chip rules implemented

The planner follows the official 2026/27 structure:

- Wildcard, Free Hit, Bench Boost and Triple Captain.
- One of each in the first half and one of each in the second half (eight chips total).
- First-half chips expire after GW19; unused chips do not carry over.
- Second set starts in GW20.
- Only one chip can be played in a Gameweek.
- Wildcard and Free Hit cannot be played in Gameweek 1.
- Free Hit cannot be played in consecutive Gameweeks; using the first Free Hit in GW19 blocks the second in GW20.

Official reference: <https://www.premierleague.com/en/news/4679879/whats-happening-with-fpl-chips-in-202627>

## Automation

`.github/workflows/update-data.yml` runs four times per day and can be run manually. Each run:

1. unit-tests the Vortex team model;
2. fetches and validates official FPL bootstrap, fixtures and recent live-GW data;
3. refreshes/bootstrap historical match inputs;
4. stores a price-pressure snapshot;
5. stores/evaluates prediction history;
6. rebuilds `data.json`;
7. validates structure, team/player counts, projection ranges and FDR values;
8. commits only refreshed data.

The workflow itself does **not** publish or deploy the website.

## Projection transparency

- **Next Gameweek:** official FPL `ep_next` when the official API is available.
- **Later tracked Gameweeks:** transparent Vortex projection based on 55% next-GW estimate + 30% form + 15% points-per-game, adjusted using position-specific Vortex FDR and availability.
- Vortex future projections are explicitly separate from official FPL estimates.

## Chip simulation

The public Chip Planner provides league-level radar windows. **My Team Lab** adds manager-specific simulation:

- Bench Boost: projected bench points by Gameweek.
- Triple Captain: extra points above normal captaincy.
- Free Hit: beam-search squad optimization for each tracked Gameweek under budget, squad-shape and max-three-per-club constraints.
- Wildcard: multi-Gameweek optimized squad comparison versus holding the current squad.

These are projection-model simulations, not guarantees.

## Manager privacy

The site asks only for a public numeric FPL Team ID. It stores that ID only in browser `localStorage`. The included Cloudflare Pages Function (`functions/api/manager.js`) is a narrow proxy to official public FPL manager endpoints and stores no manager data.

## Local review

```bash
python3 scripts/build_data_json.py
python3 scripts/validate_data.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m http.server 8080
```

Open <http://localhost:8080>.

The manager-data proxy is available after Cloudflare Pages deployment. During local review, My Team Lab also tries the official FPL API directly as a fallback.

## Hosting later — not now

When the repo has been reviewed, Cloudflare Pages can be connected to this repository with no build command. The site root is `/`. The `functions/` directory will provide the manager-data proxy automatically.

## Data credit

See [`DATA_SOURCES.md`](DATA_SOURCES.md). Upstream data has its own usage terms; code ownership does not imply ownership of third-party data.
