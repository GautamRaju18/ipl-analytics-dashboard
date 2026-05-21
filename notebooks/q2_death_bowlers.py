"""
Q2 — Which bowlers are most destructive in death overs (16-20)?
Run from repo root: python notebooks/q2_death_bowlers.py
Outputs: outputs/q2_death_bowlers.html/.png
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import sys, os

sys.path.insert(0, "notebooks")
from config import load_clean

os.makedirs("outputs", exist_ok=True)

# ── LOAD & FILTER TO DEATH OVERS ──────────────────────────────────────────────

df = load_clean()

# Death overs: 0-indexed overs 15–19 (i.e., overs 16–20 in broadcast terms)
# Exclude super over matches to avoid inflating economy in 1-over pressure
# Exclude DLS matches (incomplete innings skew death-over exposure)
death = df[
    df["over"].between(15, 19) &
    (~df["is_dls"]) &
    df["superover_winner"].isna()   # exclude super-over matches
].copy()

print(f"Death over deliveries: {death.shape[0]:,}")
print(f"Unique bowlers in death overs: {death['bowler'].nunique()}")

# ── BOWLER STATS IN DEATH OVERS ───────────────────────────────────────────────

bowler_stats = (
    death
    .groupby("bowler")
    .agg(
        balls        = ("valid_ball", "sum"),          # legal deliveries only
        runs_conceded= ("runs_bowler", "sum"),         # bowler-charged runs (excl. byes/leg-byes)
        wickets      = ("bowler_wicket", "sum"),       # bowler wickets (excl. run-outs)
        matches      = ("match_id", "nunique"),
    )
    .reset_index()
)

# Minimum threshold: 200 legal balls in death overs (filters small samples)
MIN_BALLS = 200
bowler_stats = bowler_stats[bowler_stats["balls"] >= MIN_BALLS].copy()
print(f"\nBowlers with >= {MIN_BALLS} death-over balls: {len(bowler_stats)}")

# Core metrics
bowler_stats["economy"]     = (bowler_stats["runs_conceded"] / bowler_stats["balls"] * 6).round(2)
bowler_stats["wpo"]         = (bowler_stats["wickets"] / (bowler_stats["balls"] / 6)).round(3)  # wickets per over
bowler_stats["dot_balls"]   = death.groupby("bowler")["runs_total"].apply(
                                  lambda x: (x == 0).sum()
                              ).reindex(bowler_stats["bowler"]).values
bowler_stats["dot_pct"]     = (bowler_stats["dot_balls"] / bowler_stats["balls"] * 100).round(1)

# ── OPPOSITION STRENGTH (controlling for quality of teams faced) ───────────────
# For each batting team, compute their average death-over RPO across the full dataset.
# A bowler who faced stronger batting teams (high RPO) deserves more credit
# for a low economy rate.

team_death_rpo = (
    death
    .groupby(["batting_team", "match_id", "innings", "over"])["runs_total"]
    .sum()
    .reset_index()
    .groupby("batting_team")
    .agg(total_runs=("runs_total", "sum"), total_overs=("over", "count"))
    .assign(team_rpo=lambda x: x["total_runs"] / x["total_overs"])
    .reset_index()[["batting_team", "team_rpo"]]
)
overall_death_rpo = team_death_rpo["team_rpo"].mean()

# Average opposition RPO for each bowler
opp_strength = (
    death
    .merge(team_death_rpo, on="batting_team")
    .groupby("bowler")["team_rpo"]
    .mean()
    .reset_index()
    .rename(columns={"team_rpo": "opp_strength"})
)
bowler_stats = bowler_stats.merge(opp_strength, on="bowler")
bowler_stats["opp_strength"] = bowler_stats["opp_strength"].round(3)

# Adjusted economy: penalise if you faced weak opposition
# adj_economy = economy - (opp_strength - overall_avg) i.e. subtract how easy the opposition was
bowler_stats["adj_economy"] = (
    bowler_stats["economy"] - (bowler_stats["opp_strength"] - overall_death_rpo)
).round(2)

# ── PRINT TOP BOWLERS ─────────────────────────────────────────────────────────

top_wpo   = bowler_stats.nsmallest(5, "economy")[["bowler", "balls", "economy", "adj_economy", "wpo", "dot_pct", "opp_strength"]]
top_econ  = bowler_stats.nlargest(5, "wpo")[["bowler", "balls", "economy", "adj_economy", "wpo", "dot_pct", "opp_strength"]]

print(f"\n--- Top 5 by Economy (death overs) ---\n{top_wpo.to_string(index=False)}")
print(f"\n--- Top 5 by Wickets Per Over (death overs) ---\n{top_econ.to_string(index=False)}")
print(f"\nOverall avg death-over RPO: {overall_death_rpo:.2f}")

# ── CHART: SCATTER — ECONOMY vs WICKET RATE ───────────────────────────────────
# X = economy (lower = better, so we want left side)
# Y = wickets per over (higher = better, so we want top)
# Bubble size = balls bowled
# Color = opposition strength (higher = faced tougher batters)
# Best bowlers: bottom-left (elite, low economy AND high wickets)
# Annotate top 8 by an "impact score" = wpo / economy (higher = better)

bowler_stats["impact_score"] = (bowler_stats["wpo"] / bowler_stats["economy"]).round(4)

# Bubble sizes: scale balls to a readable range — must be added BEFORE top8 slice
size_min, size_max = 12, 45
b_min, b_max = bowler_stats["balls"].min(), bowler_stats["balls"].max()
bowler_stats["bubble_size"] = (
    (bowler_stats["balls"] - b_min) / (b_max - b_min) * (size_max - size_min) + size_min
)

top8 = bowler_stats.nlargest(8, "impact_score")

fig = go.Figure()

# All bowlers (background, dimmed)
others = bowler_stats[~bowler_stats["bowler"].isin(top8["bowler"])]
fig.add_trace(go.Scatter(
    x=others["economy"],
    y=others["wpo"],
    mode="markers",
    name="Other bowlers",
    marker=dict(
        size=others["bubble_size"],
        color=others["opp_strength"],
        colorscale="Blues",
        opacity=0.35,
        line=dict(width=0.5, color="#aaa"),
        showscale=False,
    ),
    hovertemplate=(
        "<b>%{customdata[0]}</b><br>"
        "Economy: %{x:.2f}<br>"
        "Wickets/over: %{y:.3f}<br>"
        "Balls: %{customdata[1]}<br>"
        "Opp strength (RPO): %{customdata[2]:.2f}"
        "<extra></extra>"
    ),
    customdata=others[["bowler", "balls", "opp_strength"]].values,
))

# Top 8 (highlighted, labeled)
fig.add_trace(go.Scatter(
    x=top8["economy"],
    y=top8["wpo"],
    mode="markers+text",
    name="Top 8 (impact score)",
    text=top8["bowler"].str.split().str[-1],     # last name only for readability
    textposition="top center",
    textfont=dict(size=11, color="#1a1a2e"),
    marker=dict(
        size=top8["bubble_size"],
        color=top8["opp_strength"],
        colorscale="YlOrRd",
        colorbar=dict(
            title="Opp.<br>RPO",
            thickness=14,
            len=0.6,
            tickformat=".1f",
        ),
        opacity=0.9,
        line=dict(width=1.5, color="#333"),
    ),
    hovertemplate=(
        "<b>%{customdata[0]}</b><br>"
        "Economy: %{x:.2f}<br>"
        "Wickets/over: %{y:.3f}<br>"
        "Balls: %{customdata[1]}<br>"
        "Opp strength (RPO): %{customdata[2]:.2f}<br>"
        "Adj. economy: %{customdata[3]:.2f}"
        "<extra></extra>"
    ),
    customdata=top8[["bowler", "balls", "opp_strength", "adj_economy"]].values,
))

# Quadrant reference lines
median_econ = bowler_stats["economy"].median()
median_wpo  = bowler_stats["wpo"].median()

fig.add_vline(x=median_econ, line_dash="dot", line_color="#bbb", line_width=1)
fig.add_hline(y=median_wpo,  line_dash="dot", line_color="#bbb", line_width=1)

fig.add_annotation(x=median_econ - 0.15, y=bowler_stats["wpo"].max() * 0.96,
    text="Elite zone", font=dict(size=11, color="#59a14f"), showarrow=False)

fig.update_layout(
    title=dict(
        text="Death Over Specialists (overs 16-20) — Economy vs Wicket Rate",
        font=dict(size=17), x=0.5,
    ),
    xaxis=dict(
        title="Economy Rate (runs per over) — lower is better",
        showgrid=True, gridcolor="#e8e8e8", autorange="reversed",
    ),
    yaxis=dict(
        title="Wickets Per Over — higher is better",
        showgrid=True, gridcolor="#e8e8e8",
    ),
    plot_bgcolor="white",
    paper_bgcolor="white",
    height=540,
    margin=dict(t=80, b=75, l=65, r=120),
    legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center"),
)
fig.add_annotation(
    x=0.5, y=-0.24, xref="paper", yref="paper",
    text=(f"Source: IPL Dataset 2008-2025 | Kaggle (chaitu20) | "
          f"Min {MIN_BALLS} death-over balls | Bubble size = balls bowled | "
          f"Color = avg. opposition batting RPO"),
    showarrow=False, font=dict(size=10, color="grey"),
)

fig.write_html("outputs/q2_death_bowlers.html")
try:
    fig.write_image("outputs/q2_death_bowlers.png", scale=2, width=950, height=540)
    print("\nSaved: outputs/q2_death_bowlers.html + .png")
except Exception as e:
    print(f"\nSaved: outputs/q2_death_bowlers.html (PNG skipped: {e})")

# ── PRINT INSIGHT ─────────────────────────────────────────────────────────────

print(f"\n{'='*65}")
print("Q2 INSIGHT SUMMARY")
print("="*65)
print(f"\nTop 8 by impact score (wickets/over ÷ economy):")
print(top8[["bowler", "balls", "economy", "adj_economy", "wpo", "dot_pct", "opp_strength"]].to_string(index=False))
print(f"""
RECRUITER FRAMING:
Raw economy in death overs is noisy — a bowler facing Mumbai Indians at
Wankhede is under more pressure than one facing weaker sides at
low-scoring venues. Adjusted economy accounts for opposition strength
(avg. batting RPO of teams faced). The scatter makes the elite tier
visible at a glance: bowlers in the top-left quadrant deliver both
wicket-taking ability and containment — the rarest combination in T20
cricket and the most auction-valuable profile.
""")
