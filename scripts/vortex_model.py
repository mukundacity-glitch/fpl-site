"""Vortex team-strength model and Vortex FDR (your own numbers).

Every number below is yours to change. These constants are starting values,
NOT yet tuned on data. Backtest before trusting them.
"""
import bisect, math

SEASON_WEIGHT = {"2026-2027": 1.0, "2025-2026": 0.45}
XG_SHARE = 0.7
L2 = 3.0
PROMOTED_PRIOR = -0.10
SWEEPS = 150
BIN_CUTS = (0.10, 0.35, 0.70, 0.90)

SCALE = [
    {"fdr": 1, "label": "Very easy", "color": "#3fae29", "text": "#101010"},
    {"fdr": 2, "label": "Easy",      "color": "#84d21c", "text": "#101010"},
    {"fdr": 3, "label": "Balanced",  "color": "#cda228", "text": "#101010"},
    {"fdr": 4, "label": "Hard",      "color": "#e8782a", "text": "#101010"},
    {"fdr": 5, "label": "Very hard", "color": "#d6403a", "text": "#ffffff"},
]


def fit(matches, extra_codes=(), promoted=()):
    codes = sorted(set(extra_codes) | {m["home"] for m in matches} | {m["away"] for m in matches})
    att = {c: 0.0 for c in codes}
    dfn = {c: 0.0 for c in codes}
    prior = {c: (PROMOTED_PRIOR if c in promoted else 0.0) for c in codes}
    tw = sum(m["w"] for m in matches) or 1.0
    mu = math.log(max(sum(m["w"] * (m["hy"] + m["ay"]) for m in matches) / (2 * tw), 0.3))
    hadv = 0.2
    by = {c: [] for c in codes}
    for m in matches:
        by[m["home"]].append(m)
        by[m["away"]].append(m)

    def lam_h(m): return math.exp(mu + hadv + att[m["home"]] - dfn[m["away"]])
    def lam_a(m): return math.exp(mu + att[m["away"]] - dfn[m["home"]])

    for _ in range(SWEEPS):
        g = h = 0.0
        for m in matches:
            lh, la = lam_h(m), lam_a(m)
            g += m["w"] * ((m["hy"] - lh) + (m["ay"] - la)); h += m["w"] * (lh + la)
        mu += g / h if h else 0
        g = h = 0.0
        for m in matches:
            lh = lam_h(m); g += m["w"] * (m["hy"] - lh); h += m["w"] * lh
        hadv += g / h if h else 0
        for c in codes:
            g, h = -L2 * (att[c] - prior[c]), L2
            for m in by[c]:
                if m["home"] == c: lam, y = lam_h(m), m["hy"]
                else: lam, y = lam_a(m), m["ay"]
                g += m["w"] * (y - lam); h += m["w"] * lam
            att[c] += g / h
            g, h = -L2 * (dfn[c] - prior[c]), L2
            for m in by[c]:
                if m["home"] == c: lam, y = lam_a(m), m["ay"]
                else: lam, y = lam_h(m), m["hy"]
                g += m["w"] * (lam - y); h += m["w"] * lam
            dfn[c] += g / h
        ma = sum(att.values()) / len(codes); md = sum(dfn.values()) / len(codes)
        for c in codes: att[c] -= ma; dfn[c] -= md
        mu += ma - md
    return {"mu": mu, "hadv": hadv, "att": att, "dfn": dfn}


def expected(model, team, opp, team_home):
    m = model
    lf = math.exp(m["mu"] + (m["hadv"] if team_home else 0) + m["att"][team] - m["dfn"][opp])
    la = math.exp(m["mu"] + (0 if team_home else m["hadv"]) + m["att"][opp] - m["dfn"][team])
    return lf, la


def _metrics(lf, la):
    return {"att": -math.log(lf), "def": math.log(la), "all": math.log(la) - math.log(lf)}


def reference(model, teams):
    ref = {"att": [], "def": [], "all": []}
    for t in teams:
        for o in teams:
            if t == o: continue
            for home in (True, False):
                for k, v in _metrics(*expected(model, t, o, home)).items():
                    ref[k].append(v)
    for k in ref: ref[k].sort()
    return ref


def rate(ref, kind, value):
    p = bisect.bisect_left(ref[kind], value) / len(ref[kind])
    fdr = 1 + sum(1 for c in BIN_CUTS if p >= c)
    return fdr, int(round(p * 100))


def fixture_difficulty(model, ref, team, opp, team_home):
    lf, la = expected(model, team, opp, team_home)
    out = {"xgf": round(lf, 2), "xga": round(la, 2)}
    for kind, v in _metrics(lf, la).items():
        out["fdr_" + kind], out["score_" + kind] = rate(ref, kind, v)
    return out
