# FPL Vortex data sources and methodology

## Official Fantasy Premier League API

The automated workflow uses public FPL endpoints for:

- player prices, ownership, form, transfers, status and `ep_next`;
- current/next Gameweek metadata and deadlines;
- Premier League fixtures, blanks and doubles;
- completed Gameweek live points for prediction evaluation;
- manager summary, chip history and current picks in My Team Lab.

Official site: <https://fantasy.premierleague.com/>

New data is validated before it replaces the last-known-good copy. If an API call fails, the updater preserves the previous valid data.

## FPL Core Insights bootstrap/history

Historical and current-season CSV inputs are refreshed from:

<https://github.com/olbauday/FPL-Core-Insights>

They provide match/result/xG history used as raw input to Vortex team-strength modelling. The source repository's README asks websites/blogs using the data to link back to it. Keep this credit visible.

The external repository does not currently provide a conventional LICENSE file in the data package reviewed for this project. Treat its README permission and any upstream provider terms as separate from this repository's own code.

## Vortex FDR

Vortex FDR is computed by this project; it is not the official FPL difficulty rating.

Inputs:

- finished Premier League results;
- match xG when available;
- official future fixtures.

The model fits attack and defensive strengths with recency/season weights and shrinkage, estimates expected goals for each possible fixture, and converts the relative fixture difficulty distribution into 1–5 bands for:

- overall;
- attack (MID/FWD planning);
- defence (GKP/DEF planning).

Model constants live in `scripts/vortex_model.py` and are intentionally explicit so they can be backtested and tuned.

## Player projections

- The next-GW value uses official FPL `ep_next` when available.
- Later tracked GWs use a transparent Vortex heuristic: 55% `ep_next`, 30% form and 15% points-per-game, then fixture-adjusted by position-specific Vortex FDR and availability.
- The UI labels these later values as Vortex projections; they are not represented as official FPL forecasts.

## Price pressure

FPL Vortex does **not** claim to know FPL's private price-change formula.

The site stores repeated official snapshots and creates a -100 to +100 pressure score from:

- current net transfer flow;
- change in net transfer flow per hour when multiple snapshots exist.

The result is called **Price Pressure**, not a guaranteed probability.

## Prediction accuracy

Before an upcoming Gameweek the workflow stores each player's official `ep_next`. After the Gameweek is finalized, it compares those saved predictions with official Gameweek points and reports mean absolute error and median absolute error.

This prevents hindsight rewriting of the forecast history.

## 2026/27 chips

Official Premier League guidance confirms two sets of Wildcard, Free Hit, Bench Boost and Triple Captain in 2026/27, one set per half-season, with the first set expiring after GW19 and only one chip playable per Gameweek:

<https://www.premierleague.com/en/news/4679879/whats-happening-with-fpl-chips-in-202627>
