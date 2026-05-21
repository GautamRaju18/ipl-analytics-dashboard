"""
Q5 — Is there a home ground advantage in IPL?
Run from repo root: python notebooks/q5_home_advantage.py
Outputs: outputs/q5_home_advantage.html/.png
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import sys, os

sys.path.insert(0, "notebooks")
from config import load_clean, HOME_VENUES

os.makedirs("outputs", exist_ok=True)

# ── LOAD ──────────────────────────────────────────────────────────────────────

df = load_clean()

# ── BUILD REVERSE LOOKUP: venue -> home team ──────────────────────────────────
# After normalization, each canonical venue maps to exactly one home franchise.
venue_to_home_team = {}
for team, venues in HOME_VENUES.items():
    for venue in venues:
        venue_to_home_team[venue] = team

# ── MATCH-LEVEL EXTRACTION ────────────────────────────────────────────────────

match_cols = ["match_id", "year", "venue", "match_won_by", "valid_result", "is_neutral_season"]
matches = df.drop_duplicates("match_id")[match_cols].copy()

# Get both teams per match (team batting in innings 1 and innings 2)
innings_teams = (
    df[df["innings"].isin([1, 2])]
    .groupby(["match_id", "innings"])["batting_team"]
    .first()
    .unstack(level="innings")
    .rename(columns={1: "team1", 2: "team2"})
    .reset_index()
)
matches = matches.merge(innings_teams, on="match_id", how="left")
matches = matches[matches["valid_result"]].copy()

print(f"Valid matches: {len(matches)}")
print(f"Matches with both teams identified: {matches[['team1','team2']].notna().all(axis=1).sum()}")

# ── CLASSIFY HOME / AWAY / NEUTRAL ────────────────────────────────────────────

records = []
for _, row in matches.iterrows():
    team1, team2 = row["team1"], row["team2"]
    venue        = row["venue"]
    won_by       = row["match_won_by"]
    year         = row["year"]
    neutral      = bool(row["is_neutral_season"])

    home_team = venue_to_home_team.get(venue)   # None if venue isn't a known home ground

    for team in [team1, team2]:
        if pd.isna(team):
            continue
        won = 1 if won_by == team else 0

        if neutral:
            venue_type = "Neutral (2020)"
        elif home_team == team:
            venue_type = "Home"
        elif home_team is not None:
            venue_type = "Away"          # opponent is home
        else:
            venue_type = "Neutral"       # non-home venue (playoffs etc.)

        records.append({
            "team":       team,
            "venue_type": venue_type,
            "won":        won,
            "match_id":   row["match_id"],
            "year":       year,
        })

team_records = pd.DataFrame(records)
print(f"\nRecord breakdown:\n{team_records['venue_type'].value_counts().to_string()}")

# ── COMPUTE WIN % BY TEAM AND VENUE TYPE ─────────────────────────────────────

# Exclude 2020 neutral and generic neutral from the main H vs A analysis
ha_df = team_records[team_records["venue_type"].isin(["Home", "Away"])].copy()

team_ha = (
    ha_df
    .groupby(["team", "venue_type"])
    .agg(matches=("won", "count"), wins=("won", "sum"))
    .reset_index()
)
team_ha["win_pct"] = (team_ha["wins"] / team_ha["matches"] * 100).round(1)

# Pivot to home | away side by side
pivot = team_ha.pivot(index="team", columns="venue_type", values="win_pct").reset_index()
pivot.columns.name = None

# Only keep teams with >= 20 home matches AND >= 20 away matches
match_counts = team_ha.pivot(index="team", columns="venue_type", values="matches").reset_index()
match_counts.columns.name = None
pivot = pivot.merge(match_counts[["team", "Home", "Away"]], on="team", suffixes=("", "_n"))
pivot = pivot.rename(columns={"Home_n": "home_n", "Away_n": "away_n"})
pivot = pivot[(pivot["home_n"] >= 20) & (pivot["away_n"] >= 20)].copy()

# Home advantage differential
pivot["differential"] = (pivot["Home"] - pivot["Away"]).round(1)
pivot = pivot.sort_values("differential", ascending=False).reset_index(drop=True)

print("\n--- Home vs Away Win % (teams with >= 20 matches each) ---")
print(pivot[["team", "Home", "Away", "differential", "home_n", "away_n"]].to_string(index=False))

# ── CHART: DUMBBELL / LOLLIPOP ────────────────────────────────────────────────

teams = pivot["team"].tolist()
home_pct  = pivot["Home"].tolist()
away_pct  = pivot["Away"].tolist()
diff      = pivot["differential"].tolist()

# Color differential bars
diff_colors = ["#2ca02c" if d > 0 else "#d62728" for d in diff]

fig = go.Figure()

# Connecting line between home and away dots
for i, (team, h, a) in enumerate(zip(teams, home_pct, away_pct)):
    fig.add_trace(go.Scatter(
        x=[a, h], y=[i, i],
        mode="lines",
        line=dict(color="#cccccc", width=2),
        showlegend=False,
        hoverinfo="skip",
    ))

# Away dots
fig.add_trace(go.Scatter(
    x=away_pct,
    y=list(range(len(teams))),
    mode="markers",
    name="Away Win %",
    marker=dict(color="#e15759", size=12, symbol="circle",
                line=dict(width=1.5, color="white")),
    hovertemplate="<b>%{customdata}</b><br>Away: %{x:.1f}%<extra></extra>",
    customdata=teams,
))

# Home dots
fig.add_trace(go.Scatter(
    x=home_pct,
    y=list(range(len(teams))),
    mode="markers",
    name="Home Win %",
    marker=dict(color="#4e79a7", size=12, symbol="diamond",
                line=dict(width=1.5, color="white")),
    hovertemplate="<b>%{customdata[0]}</b><br>Home: %{x:.1f}%<br>Differential: %{customdata[1]:+.1f}pp<extra></extra>",
    customdata=list(zip(teams, diff)),
))

# Differential labels on right
for i, (d, h) in enumerate(zip(diff, home_pct)):
    color = "#2ca02c" if d >= 0 else "#d62728"
    fig.add_annotation(
        x=max(home_pct + away_pct) + 3.5,
        y=i,
        text=f"<b>{d:+.1f}</b>",
        showarrow=False,
        font=dict(size=11, color=color),
        xanchor="left",
    )

# 50% reference line
fig.add_vline(x=50, line_dash="dot", line_color="#aaa", line_width=1.5,
              annotation_text="50%", annotation_position="top")

fig.update_layout(
    title=dict(
        text="Home Ground Advantage in IPL — Win % at Home vs Away",
        font=dict(size=17), x=0.5,
    ),
    xaxis=dict(
        title="Win Rate (%)",
        range=[20, max(home_pct + away_pct) + 10],
        showgrid=True, gridcolor="#e8e8e8",
        ticksuffix="%",
    ),
    yaxis=dict(
        tickmode="array",
        tickvals=list(range(len(teams))),
        ticktext=teams,
        tickfont=dict(size=11),
        showgrid=False,
        autorange="reversed",
    ),
    plot_bgcolor="white",
    paper_bgcolor="white",
    height=max(480, len(teams) * 40 + 150),
    margin=dict(t=80, b=75, l=200, r=100),
    legend=dict(orientation="h", y=-0.14, x=0.5, xanchor="center"),
)
fig.add_annotation(
    x=0.5, y=-0.18, xref="paper", yref="paper",
    text="Source: IPL Dataset 2008-2025 | Kaggle (chaitu20) | 2020 season (UAE neutral) excluded | Min 20 home + 20 away matches",
    showarrow=False, font=dict(size=10, color="grey"),
)

# Column header for differential
fig.add_annotation(
    x=max(home_pct + away_pct) + 3.5,
    y=-0.7,
    text="<b>Diff</b>",
    showarrow=False,
    font=dict(size=11, color="#333"),
    xanchor="left",
)

fig.write_html("outputs/q5_home_advantage.html")
try:
    fig.write_image("outputs/q5_home_advantage.png", scale=2, width=950,
                    height=max(480, len(teams) * 40 + 150))
    print("\nSaved: outputs/q5_home_advantage.html + .png")
except Exception as e:
    print(f"\nSaved: outputs/q5_home_advantage.html (PNG skipped: {e})")

# ── SEASON-BY-SEASON HOME ADVANTAGE (top 3 franchises) ───────────────────────

top3 = pivot.head(3)["team"].tolist()

yearly_ha = (
    team_records[
        team_records["venue_type"].isin(["Home", "Away"]) &
        team_records["team"].isin(top3)
    ]
    .groupby(["team", "year", "venue_type"])
    .agg(matches=("won", "count"), wins=("won", "sum"))
    .reset_index()
)
yearly_ha["win_pct"] = (yearly_ha["wins"] / yearly_ha["matches"] * 100).round(1)
yearly_pivot = yearly_ha[yearly_ha["venue_type"] == "Home"].pivot(
    index="year", columns="team", values="win_pct"
)
print(f"\n--- Home Win % by Season (top 3 home-advantage teams) ---")
print(yearly_pivot.to_string())

# ── PRINT INSIGHT ─────────────────────────────────────────────────────────────

best_team  = pivot.iloc[0]
worst_team = pivot.iloc[-1]

print(f"\n{'='*65}")
print("Q5 INSIGHT SUMMARY")
print("="*65)
print(f"\nStrongest home advantage : {best_team['team']} ({best_team['Home']:.1f}% home vs {best_team['Away']:.1f}% away, +{best_team['differential']:.1f}pp)")
print(f"Least home-dependent     : {worst_team['team']} ({worst_team['Home']:.1f}% home vs {worst_team['Away']:.1f}% away, {worst_team['differential']:+.1f}pp)")
print(f"""
RECRUITER FRAMING:
The 2020 season, played entirely in UAE, functions as a natural
experiment — stripping away home advantage entirely. Teams that
outperformed their historical home-advantage differential in 2020
likely have a quality edge that isn't venue-dependent. The franchise
with the highest home-away differential ({best_team['team']}) may be
over-reliant on ground familiarity; the one closest to 0 ({worst_team['team']})
performs consistently regardless of location — a different kind of
competitive moat.
""")
