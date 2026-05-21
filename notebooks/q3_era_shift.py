"""
Q3 — Has the IPL become a batsman's game — and when did it shift?
Run from repo root: python notebooks/q3_era_shift.py
Outputs: outputs/q3_era_shift.html/.png
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import sys, os

sys.path.insert(0, "notebooks")
from config import load_clean

os.makedirs("outputs", exist_ok=True)

# ── LOAD & CLEAN ──────────────────────────────────────────────────────────────

df = load_clean()

# Exclude: partial 2026 season + DLS matches (incomplete innings skew RPO)
df_clean = df[
    (df["year"] <= 2025) &
    (~df["is_dls"])
].copy()

print(f"Rows after exclusions: {df_clean.shape[0]:,}  (dropped {df.shape[0]-df_clean.shape[0]:,})")
print(f"Seasons: {sorted(df_clean['year'].unique())}")

# ── COMPUTE RPO PER YEAR PER PHASE ────────────────────────────────────────────
# Method: sum runs_total per (year, match, innings, over) → get per-over totals
#         then average across all overs in that phase for the year.
# This gives the true average runs per over rather than a per-delivery mean.

PHASES = {
    "Powerplay (1-6)": (0, 5),    # 0-indexed overs 0-5
    "Middle (7-15)":   (6, 14),
    "Death (16-20)":   (15, 19),
}

PHASE_COLORS = {
    "Powerplay (1-6)": "#1f77b4",
    "Middle (7-15)":   "#ff7f0e",
    "Death (16-20)":   "#d62728",
}

records = []
for phase_name, (ov_min, ov_max) in PHASES.items():
    phase_df = df_clean[df_clean["over"].between(ov_min, ov_max)]

    # Sum runs per over-unit (one T20 over = one unit)
    over_runs = (
        phase_df
        .groupby(["year", "match_id", "innings", "over"])["runs_total"]
        .sum()
        .reset_index(name="over_runs")
    )

    # Average RPO per year across all over-units
    yearly = (
        over_runs
        .groupby("year")
        .agg(total_runs=("over_runs", "sum"), total_overs=("over_runs", "count"))
        .reset_index()
    )
    yearly["rpo"]   = (yearly["total_runs"] / yearly["total_overs"]).round(3)
    yearly["phase"] = phase_name
    records.append(yearly)

rpo_all = pd.concat(records, ignore_index=True)

# Pivot for readable console output
pivot_display = rpo_all.pivot(index="year", columns="phase", values="rpo").round(2)
pivot_display = pivot_display[list(PHASES.keys())]   # column order
print("\n--- RPO by Year and Phase ---")
print(pivot_display.to_string())

# ── FIND INFLECTION POINT ─────────────────────────────────────────────────────
# Define inflection as the year with the single largest YoY RPO increase
# across all three phases combined (sum of changes)

combined = rpo_all.pivot(index="year", columns="phase", values="rpo").sort_index()
combined["total_rpo"] = combined.sum(axis=1)
combined["total_change"] = combined["total_rpo"].diff()
inflection_year = int(combined["total_change"].idxmax())

# Also track death-over-specific inflection (most visually striking)
death_series = combined["Death (16-20)"].dropna()
death_change = death_series.diff()
death_inflection_year = int(death_change.idxmax())
death_inflection_jump = round(death_change.max(), 2)

print(f"\nCombined RPO inflection year : {inflection_year}")
print(f"Death-over inflection year   : {death_inflection_year}  (jump: +{death_inflection_jump} RPO)")

# ── SUMMARY STATS ─────────────────────────────────────────────────────────────

print("\n--- Phase RPO: 2008 vs 2025 ---")
for phase in PHASES:
    rpo_2008 = rpo_all[(rpo_all["phase"] == phase) & (rpo_all["year"] == 2008)]["rpo"].values
    rpo_2025 = rpo_all[(rpo_all["phase"] == phase) & (rpo_all["year"] == 2025)]["rpo"].values
    if len(rpo_2008) and len(rpo_2025):
        change = rpo_2025[0] - rpo_2008[0]
        print(f"  {phase:<22}: {rpo_2008[0]:.2f} (2008) -> {rpo_2025[0]:.2f} (2025)  [{change:+.2f}]")

# ── CHART: MULTI-LINE + ANNOTATIONS ──────────────────────────────────────────

fig = go.Figure()

# Era background bands
era_bands = [
    (2007.5, 2012.5, "rgba(78,121,167,0.07)",  "Era 1<br>(2008-12)"),
    (2012.5, 2017.5, "rgba(242,142,43,0.07)",  "Era 2<br>(2013-17)"),
    (2017.5, 2025.5, "rgba(89,161,79,0.07)",   "Era 3<br>(2018-25)"),
]
for x0, x1, color, label in era_bands:
    fig.add_vrect(
        x0=x0, x1=x1,
        fillcolor=color,
        layer="below",
        line_width=0,
    )
    fig.add_annotation(
        x=(x0 + x1) / 2, y=12.8,
        text=label,
        showarrow=False,
        font=dict(size=10, color="#888"),
        align="center",
    )

# Phase lines
for phase_name, color in PHASE_COLORS.items():
    phase_data = rpo_all[rpo_all["phase"] == phase_name].sort_values("year")
    fig.add_trace(go.Scatter(
        x=phase_data["year"],
        y=phase_data["rpo"],
        mode="lines+markers",
        name=phase_name,
        line=dict(color=color, width=2.5),
        marker=dict(size=6, color=color),
        hovertemplate="<b>%{fullData.name}</b><br>Year: %{x}<br>RPO: %{y:.2f}<extra></extra>",
    ))

# Inflection annotation on death overs line
death_inflection_rpo = combined.loc[death_inflection_year, "Death (16-20)"]
fig.add_annotation(
    x=death_inflection_year,
    y=death_inflection_rpo,
    text=f"<b>Inflection: {death_inflection_year}</b><br>Death over RPO<br>jumped +{death_inflection_jump}",
    showarrow=True,
    arrowhead=2,
    arrowcolor="#d62728",
    ax=50, ay=-45,
    font=dict(size=11, color="#d62728"),
    bgcolor="white",
    bordercolor="#d62728",
    borderwidth=1.5,
    borderpad=4,
)

fig.update_layout(
    title=dict(
        text="IPL Run Economy by Phase (2008-2025) — When Did Batsmen Take Over?",
        font=dict(size=17),
        x=0.5,
    ),
    xaxis=dict(
        title="Season (Year)",
        tickmode="linear",
        dtick=2,
        tickfont=dict(size=12),
        showgrid=True,
        gridcolor="#e8e8e8",
    ),
    yaxis=dict(
        title="Runs Per Over (RPO)",
        tickfont=dict(size=12),
        showgrid=True,
        gridcolor="#e8e8e8",
        range=[5.5, 13.2],
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        font=dict(size=12),
    ),
    plot_bgcolor="white",
    paper_bgcolor="white",
    height=520,
    margin=dict(t=90, b=75, l=65, r=40),
)
fig.add_annotation(
    x=0.5, y=-0.16, xref="paper", yref="paper",
    text="Source: IPL Dataset 2008-2025 | Kaggle (chaitu20) | DLS matches excluded",
    showarrow=False, font=dict(size=11, color="grey"),
)

fig.write_html("outputs/q3_era_shift.html")
try:
    fig.write_image("outputs/q3_era_shift.png", scale=2, width=950, height=520)
    print("\nSaved: outputs/q3_era_shift.html + .png")
except Exception as e:
    print(f"\nSaved: outputs/q3_era_shift.html (PNG skipped: {e})")

# ── PRINT INSIGHT ─────────────────────────────────────────────────────────────

print(f"\n{'='*65}")
print("Q3 INSIGHT SUMMARY")
print("="*65)
print(f"""
The IPL has measurably shifted toward a batsman's game across all three
phases, but the inflection was sharpest in {death_inflection_year} when death-over
scoring jumped +{death_inflection_jump} RPO in a single season. Powerplay scoring has
climbed steadily as openers became more aggressive; the death-overs spike
is more abrupt, coinciding with a strategic shift toward specialist
finishers (Pollard, Russell, Hardik era). Middle overs show the smallest
absolute change — suggesting that phase remains the most contested.

RECRUITER FRAMING:
This is not just "cricket got more batting-friendly". It shows WHEN the
shift happened, in WHICH phase, and by HOW MUCH — the kind of
decomposed, operationally-specific answer that separates analysts from
observers. The inflection year gives a concrete anchor for further
hypothesis testing: what rule change, team composition shift, or pitch
preparation trend drove it?
""")
