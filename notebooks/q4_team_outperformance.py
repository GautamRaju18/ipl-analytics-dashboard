"""
Q4 — Which teams consistently outperform expected runs? (Strategy/Coaching Alpha)
Run from repo root: python notebooks/q4_team_outperformance.py
Outputs: outputs/q4_outperformance_bar.html/.png
         outputs/q4_outperformance_trend.html/.png
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import sys, os

sys.path.insert(0, "notebooks")
from config import load_clean

os.makedirs("outputs", exist_ok=True)

# ── LOAD ──────────────────────────────────────────────────────────────────────

df = load_clean()

# Only innings 1 and 2 (exclude super over innings), no DLS, no super-over matches
df_clean = df[
    df["innings"].isin([1, 2]) &
    (~df["is_dls"]) &
    df["superover_winner"].isna()
].copy()

# ── INNINGS-LEVEL SCORES ──────────────────────────────────────────────────────
# Each row = one innings in one match.
# actual_runs = total runs scored in that innings (sum of runs_total across all deliveries)

innings_scores = (
    df_clean
    .groupby(["match_id", "innings", "batting_team", "venue", "era", "year"])
    ["runs_total"]
    .sum()
    .reset_index(name="actual_runs")
)

print(f"Total innings records: {len(innings_scores):,}")
print(f"Season range: {innings_scores['year'].min()} - {innings_scores['year'].max()}")

# ── EXPECTED RUNS ─────────────────────────────────────────────────────────────
# Expected = mean runs scored by ALL teams at the same venue, in the same innings
# position (1st or 2nd), in the same era.
# Min 10 innings per cell — cells below this threshold are too noisy to be reliable.

venue_expected = (
    innings_scores
    .groupby(["venue", "innings", "era"])
    .agg(
        expected_runs = ("actual_runs", "mean"),
        sample_size   = ("actual_runs", "count"),
    )
    .reset_index()
)

MIN_CELL = 10
venue_expected = venue_expected[venue_expected["sample_size"] >= MIN_CELL].copy()
print(f"\nVenue-innings-era cells with >= {MIN_CELL} innings: {len(venue_expected)}")

# ── MERGE & COMPUTE OUTPERFORMANCE ────────────────────────────────────────────

merged = innings_scores.merge(
    venue_expected[["venue", "innings", "era", "expected_runs"]],
    on=["venue", "innings", "era"],
    how="inner",   # inner = only keep innings where we have reliable expected
)
merged["outperformance"] = merged["actual_runs"] - merged["expected_runs"]

print(f"Innings with matched expected: {len(merged):,} / {len(innings_scores):,}")

# ── AGGREGATE BY TEAM ─────────────────────────────────────────────────────────

MIN_INNINGS = 50    # filter to teams with meaningful sample

team_perf = (
    merged
    .groupby("batting_team")
    .agg(
        avg_outperformance = ("outperformance", "mean"),
        innings_count      = ("outperformance", "count"),
        avg_actual         = ("actual_runs",     "mean"),
        avg_expected       = ("expected_runs",   "mean"),
        std_outperformance = ("outperformance", "std"),
    )
    .reset_index()
)

team_perf = team_perf[team_perf["innings_count"] >= MIN_INNINGS].copy()
team_perf = team_perf.sort_values("avg_outperformance", ascending=False).reset_index(drop=True)
team_perf["avg_outperformance"] = team_perf["avg_outperformance"].round(1)
team_perf["avg_actual"]         = team_perf["avg_actual"].round(1)
team_perf["avg_expected"]       = team_perf["avg_expected"].round(1)
team_perf["std_outperformance"] = team_perf["std_outperformance"].round(1)

print(f"\n--- Team Outperformance (min {MIN_INNINGS} innings) ---")
print(team_perf[["batting_team","avg_outperformance","innings_count","avg_actual","avg_expected"]].to_string(index=False))

# ── SEASON-BY-SEASON FOR TOP 3 ────────────────────────────────────────────────

top3 = team_perf.head(3)["batting_team"].tolist()
print(f"\nTop 3 teams: {top3}")

yearly = (
    merged[merged["batting_team"].isin(top3)]
    .groupby(["batting_team", "year"])["outperformance"]
    .mean()
    .reset_index()
)
yearly["outperformance"] = yearly["outperformance"].round(1)

print("\n--- Season-by-season outperformance (top 3 teams) ---")
print(yearly.pivot(index="year", columns="batting_team", values="outperformance").round(1).to_string())

# ── CHART 1: BAR — AVG OUTPERFORMANCE PER TEAM ───────────────────────────────

colors = ["#2ca02c" if v >= 0 else "#d62728" for v in team_perf["avg_outperformance"]]

fig1 = go.Figure(go.Bar(
    x=team_perf["avg_outperformance"],
    y=team_perf["batting_team"],
    orientation="h",
    marker_color=colors,
    text=[f"{v:+.1f}" for v in team_perf["avg_outperformance"]],
    textposition="outside",
    hovertemplate=(
        "<b>%{y}</b><br>"
        "Avg outperformance: %{x:+.1f} runs<br>"
        "Innings: %{customdata[0]}<br>"
        "Avg actual: %{customdata[1]}<br>"
        "Avg expected: %{customdata[2]}"
        "<extra></extra>"
    ),
    customdata=team_perf[["innings_count","avg_actual","avg_expected"]].values,
))

fig1.add_vline(x=0, line_color="#333", line_width=1.5)

fig1.update_layout(
    title=dict(
        text="Team Outperformance vs Venue Average (Strategy / Coaching Alpha)",
        font=dict(size=17), x=0.5,
    ),
    xaxis=dict(
        title="Avg Runs Above Venue Expectation per Innings",
        showgrid=True, gridcolor="#e8e8e8",
    ),
    yaxis=dict(title="", autorange="reversed", tickfont=dict(size=12)),
    plot_bgcolor="white",
    paper_bgcolor="white",
    height=max(400, len(team_perf) * 40 + 140),
    margin=dict(t=80, b=70, l=200, r=80),
)
fig1.add_annotation(
    x=0.5, y=-0.16, xref="paper", yref="paper",
    text=(f"Source: IPL Dataset 2008-2025 | Kaggle (chaitu20) | "
          f"Expected = avg innings score at same venue, innings, era (min {MIN_INNINGS} innings per team)"),
    showarrow=False, font=dict(size=10, color="grey"),
)

fig1.write_html("outputs/q4_outperformance_bar.html")
try:
    fig1.write_image("outputs/q4_outperformance_bar.png", scale=2, width=900,
                     height=max(400, len(team_perf) * 40 + 140))
    print("\nSaved: outputs/q4_outperformance_bar.html + .png")
except Exception as e:
    print(f"\nSaved: outputs/q4_outperformance_bar.html (PNG skipped: {e})")

# ── CHART 2: LINE — SEASON-BY-SEASON TOP 3 ───────────────────────────────────

TEAM_COLORS = {"Mumbai Indians": "#4e79a7", "Chennai Super Kings": "#f28e2b",
               "Kolkata Knight Riders": "#59a14f", "Rajasthan Royals": "#e15759",
               "Royal Challengers Bangalore": "#b07aa1"}
DEFAULT_COLORS = ["#4e79a7", "#f28e2b", "#59a14f"]

fig2 = go.Figure()

for i, team in enumerate(top3):
    d = yearly[yearly["batting_team"] == team].sort_values("year")
    color = TEAM_COLORS.get(team, DEFAULT_COLORS[i % len(DEFAULT_COLORS)])
    fig2.add_trace(go.Scatter(
        x=d["year"], y=d["outperformance"],
        mode="lines+markers", name=team,
        line=dict(color=color, width=2.5),
        marker=dict(size=7, color=color),
        hovertemplate=f"<b>{team}</b><br>%{{x}}: %{{y:+.1f}} runs<extra></extra>",
    ))

fig2.add_hline(y=0, line_dash="dash", line_color="#aaa", line_width=1.5,
               annotation_text="Venue average", annotation_position="top right")

fig2.update_layout(
    title=dict(
        text="Outperformance Trend — Top 3 Teams, Season by Season",
        font=dict(size=16), x=0.5,
    ),
    xaxis=dict(title="Season", tickmode="linear", dtick=2,
               showgrid=True, gridcolor="#e8e8e8"),
    yaxis=dict(title="Runs Above Venue Expectation",
               showgrid=True, gridcolor="#e8e8e8"),
    legend=dict(orientation="h", y=-0.16, x=0.5, xanchor="center"),
    plot_bgcolor="white",
    paper_bgcolor="white",
    height=420,
    margin=dict(t=70, b=70, l=65, r=40),
)
fig2.add_annotation(
    x=0.5, y=-0.22, xref="paper", yref="paper",
    text="Source: IPL Dataset 2008-2025 | Kaggle (chaitu20) | DLS matches and super overs excluded",
    showarrow=False, font=dict(size=10, color="grey"),
)

fig2.write_html("outputs/q4_outperformance_trend.html")
try:
    fig2.write_image("outputs/q4_outperformance_trend.png", scale=2, width=900, height=420)
    print("Saved: outputs/q4_outperformance_trend.html + .png")
except Exception as e:
    print(f"Saved: outputs/q4_outperformance_trend.html (PNG skipped: {e})")

# ── PRINT INSIGHT ─────────────────────────────────────────────────────────────

best  = team_perf.iloc[0]
worst = team_perf.iloc[-1]

print(f"\n{'='*65}")
print("Q4 INSIGHT SUMMARY")
print("="*65)
print(f"Best outperformer : {best['batting_team']}  ({best['avg_outperformance']:+.1f} runs/innings, n={int(best['innings_count'])})")
print(f"Lowest performer  : {worst['batting_team']} ({worst['avg_outperformance']:+.1f} runs/innings, n={int(worst['innings_count'])})")
print(f"""
RECRUITER FRAMING:
"Expected runs" controls for the venue and era context so we're
comparing teams on a level playing field. A franchise that consistently
scores above expectation isn't just lucky — they're getting more out
of their batting lineup than the venue history predicts. That delta
is the measurable fingerprint of coaching, squad selection, and
batting strategy. {best['batting_team']}'s lead is the most defensible
signal of strategic alpha in the dataset.
""")
