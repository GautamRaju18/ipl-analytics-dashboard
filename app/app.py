"""
IPL Cricket Analytics Dashboard
Run locally:  streamlit run app/app.py
"""

import sys, os
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from notebooks.config import load_clean, HOME_VENUES

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="IPL Analytics Dashboard",
    page_icon="cricket",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_PATH = ROOT / "data" / "IPL.csv.gz"

SOURCE_NOTE = "Source: IPL Dataset 2008-2025 | Kaggle (chaitu20)"

# ── CHART STYLING HELPER ──────────────────────────────────────────────────────
# Forces dark, readable text on all axes regardless of Streamlit theme.

def _style(fig):
    fig.update_layout(font=dict(color="#1a1a1a", family="Arial, sans-serif"))
    fig.update_xaxes(
        tickfont=dict(color="#1a1a1a", size=12),
        title_font=dict(color="#1a1a1a", size=13),
    )
    fig.update_yaxes(
        tickfont=dict(color="#1a1a1a", size=12),
        title_font=dict(color="#1a1a1a", size=13),
    )
    return fig

# ── DATA LOADING ──────────────────────────────────────────────────────────────

@st.cache_data
def load_data():
    if not DATA_PATH.exists():
        st.error(
            f"Data file not found at `{DATA_PATH}`. "
            "Run: python notebooks/eda.py (after placing IPL.csv in data/) "
            "or see README for setup instructions."
        )
        st.stop()
    return load_clean(str(DATA_PATH))


# ── Q1: TOSS ANALYSIS ─────────────────────────────────────────────────────────

@st.cache_data
def q1_compute(_df):
    ERA_ORDER = ["Era 1 (2008-12)", "Era 2 (2013-17)", "Era 3 (2018-25)"]
    matches = _df.drop_duplicates("match_id")[
        ["match_id", "year", "era", "venue", "toss_winner",
         "toss_decision", "match_won_by", "valid_result"]
    ].copy()
    matches = matches[matches["valid_result"]].copy()
    matches["toss_win"] = (matches["toss_winner"] == matches["match_won_by"]).astype(int)

    overall_pct = round(matches["toss_win"].mean() * 100, 1)

    era_stats = (
        matches.groupby("era")["toss_win"]
        .agg(win_rate="mean", n="count").reset_index()
    )
    era_stats["win_pct"] = (era_stats["win_rate"] * 100).round(1)
    era_stats = era_stats[era_stats["era"].isin(ERA_ORDER)]
    era_stats["era"] = pd.Categorical(era_stats["era"], ERA_ORDER, ordered=True)
    era_stats = era_stats.sort_values("era")

    venue_counts = matches["venue"].value_counts()
    top_venues   = venue_counts[venue_counts >= 20].head(10).index.tolist()
    venue_era = (
        matches[matches["venue"].isin(top_venues)]
        .groupby(["venue", "era"])["toss_win"]
        .agg(win_rate="mean", n="count").reset_index()
    )
    venue_era["win_pct"] = (venue_era["win_rate"] * 100).round(1)
    pivot = venue_era.pivot(index="venue", columns="era", values="win_pct")
    pivot = pivot.reindex(columns=[c for c in ERA_ORDER if c in pivot.columns])
    row_means = venue_era.groupby("venue")["win_pct"].mean()
    pivot = pivot.loc[row_means.sort_values(ascending=False).index]

    return overall_pct, era_stats, pivot, ERA_ORDER


def q1_era_fig(overall_pct, era_stats):
    ERA_COLORS = {
        "Era 1 (2008-12)": "#4e79a7",
        "Era 2 (2013-17)": "#f28e2b",
        "Era 3 (2018-25)": "#59a14f",
    }
    fig = go.Figure()
    for _, row in era_stats.iterrows():
        era = str(row["era"])
        fig.add_trace(go.Bar(
            x=[era], y=[row["win_pct"]], name=era,
            marker_color=ERA_COLORS.get(era, "#aaa"),
            text=f"<b>{row['win_pct']}%</b><br>({int(row['n'])} matches)",
            textposition="outside", width=0.5, showlegend=False,
        ))
    fig.add_shape(type="line", x0=-0.5, x1=2.5, y0=50, y1=50,
                  line=dict(color="crimson", width=2, dash="dash"))
    fig.add_annotation(x=2.4, y=50.7, text="50% — pure chance",
                       font=dict(color="crimson", size=12), showarrow=False)
    fig.add_annotation(
        x=0.5, y=57.5, xref="paper",
        text=f"Overall: <b>{overall_pct}%</b> of toss winners win the match",
        font=dict(size=13, color="#333"), showarrow=False,
        bgcolor="rgba(255,255,220,0.9)", bordercolor="#999", borderwidth=1,
    )
    fig.update_layout(
        title=dict(text="Toss Win Rate by Era", font_size=16, x=0.5),
        xaxis=dict(title="Era"),
        yaxis=dict(title="Match Win Rate (%)", range=[42, 62], ticksuffix="%"),
        plot_bgcolor="white", paper_bgcolor="white", height=420,
        margin=dict(t=80, b=60, l=60, r=40),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#e8e8e8")
    fig.add_annotation(x=0.5, y=-0.18, xref="paper", yref="paper",
                       text=SOURCE_NOTE, showarrow=False,
                       font=dict(size=10, color="grey"))
    return _style(fig)


def q1_heatmap_fig(pivot):
    VENUE_SHORT = {
        "Eden Gardens":                               "Eden Gardens (KOL)",
        "Wankhede Stadium":                           "Wankhede (MUM)",
        "M Chinnaswamy Stadium":                      "Chinnaswamy (BLR)",
        "MA Chidambaram Stadium":                     "Chepauk (CHE)",
        "Arun Jaitley Stadium":                       "Arun Jaitley (DEL)",
        "Rajiv Gandhi International Stadium":         "RGIS (HYD)",
        "Sawai Mansingh Stadium":                     "Sawai Mansingh (JAI)",
        "Punjab Cricket Association Stadium, Mohali": "PCA Stadium (MOH)",
        "Narendra Modi Stadium, Ahmedabad":           "NM Stadium (AHM)",
        "Dubai International Cricket Stadium":        "Dubai (UAE)",
        "Maharashtra Cricket Association Stadium":    "MCA Stadium (PUN)",
    }
    z    = pivot.values.tolist()
    text = [[f"{v:.0f}%" if not pd.isna(v) else "—" for v in row] for row in pivot.values]
    y_labels = [VENUE_SHORT.get(v, v) for v in pivot.index]
    fig = go.Figure(data=go.Heatmap(
        z=z, x=list(pivot.columns), y=y_labels,
        text=text, texttemplate="<b>%{text}</b>", textfont=dict(size=13),
        colorscale=[
            [0.0, "#d73027"], [0.35, "#fc8d59"], [0.5, "#ffffbf"],
            [0.65, "#91cf60"], [1.0, "#1a9850"],
        ],
        zmid=50, zmin=35, zmax=65,
        colorbar=dict(title="Toss Win %", ticksuffix="%", tickvals=[35,42,50,58,65]),
    ))
    fig.update_layout(
        title=dict(text="Toss Advantage by Venue & Era", font_size=16, x=0.5),
        xaxis=dict(title="Era"),
        yaxis=dict(title="", autorange="reversed"),
        plot_bgcolor="white", paper_bgcolor="white", height=460,
        margin=dict(t=80, b=60, l=200, r=120),
    )
    fig.add_annotation(x=0.5, y=-0.16, xref="paper", yref="paper",
                       text=SOURCE_NOTE + " | Venues with <20 matches excluded",
                       showarrow=False, font=dict(size=10, color="grey"))
    return _style(fig)


# ── Q2: DEATH BOWLERS ─────────────────────────────────────────────────────────

@st.cache_data
def q2_compute(_df):
    death = _df[
        _df["over"].between(15, 19) &
        (~_df["is_dls"]) &
        _df["superover_winner"].isna()
    ].copy()

    bs = (
        death.groupby("bowler")
        .agg(balls=("valid_ball","sum"), runs=("runs_bowler","sum"),
             wickets=("bowler_wicket","sum"), matches=("match_id","nunique"))
        .reset_index()
    )
    bs = bs[bs["balls"] >= 200].copy()
    bs["economy"] = (bs["runs"] / bs["balls"] * 6).round(2)
    bs["wpo"]     = (bs["wickets"] / (bs["balls"] / 6)).round(3)

    team_rpo = (
        death.groupby(["batting_team","match_id","innings","over"])["runs_total"]
        .sum().reset_index()
        .groupby("batting_team")
        .agg(tr=("runs_total","sum"), to=("over","count"))
        .assign(rpo=lambda x: x["tr"]/x["to"])
        .reset_index()[["batting_team","rpo"]]
    )
    opp = (
        death.merge(team_rpo, on="batting_team")
        .groupby("bowler")["rpo"].mean().reset_index()
        .rename(columns={"rpo":"opp_strength"})
    )
    bs = bs.merge(opp, on="bowler")
    bs["impact_score"] = (bs["wpo"] / bs["economy"]).round(4)

    b_min, b_max = bs["balls"].min(), bs["balls"].max()
    bs["bubble_size"] = (bs["balls"] - b_min) / (b_max - b_min) * 30 + 10

    top8 = bs.nlargest(8, "impact_score").copy()
    return bs, top8


def q2_fig(bs, top8):
    others = bs[~bs["bowler"].isin(top8["bowler"])]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=others["economy"], y=others["wpo"], mode="markers", name="Other bowlers",
        marker=dict(size=others["bubble_size"], color="#cccccc", opacity=0.5,
                    line=dict(width=0.5, color="#aaa")),
        hovertemplate="<b>%{customdata}</b><br>Economy: %{x:.2f}<br>Wkt/over: %{y:.3f}<extra></extra>",
        customdata=others["bowler"].values,
    ))
    fig.add_trace(go.Scatter(
        x=top8["economy"], y=top8["wpo"], mode="markers+text", name="Top 8",
        text=top8["bowler"].str.split().str[-1],
        textposition="top center", textfont=dict(size=11),
        marker=dict(
            size=top8["bubble_size"], color=top8["opp_strength"],
            colorscale="YlOrRd", opacity=0.9,
            colorbar=dict(title="Opp. RPO", thickness=14, len=0.5),
            line=dict(width=1.5, color="#333"),
        ),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>Economy: %{x:.2f}<br>"
            "Wkt/over: %{y:.3f}<br>Balls: %{customdata[1]}<extra></extra>"
        ),
        customdata=top8[["bowler","balls"]].values,
    ))
    med_e = bs["economy"].median()
    med_w = bs["wpo"].median()
    fig.add_vline(x=med_e, line_dash="dot", line_color="#bbb", line_width=1)
    fig.add_hline(y=med_w, line_dash="dot", line_color="#bbb", line_width=1)
    fig.add_annotation(x=med_e - 0.25, y=bs["wpo"].max() * 0.96,
                       text="Elite zone", font=dict(size=11, color="#59a14f"), showarrow=False)
    fig.update_layout(
        title=dict(text="Death Over Specialists — Economy vs Wicket Rate", font_size=16, x=0.5),
        xaxis=dict(title="Economy Rate (lower = better)", autorange="reversed",
                   showgrid=True, gridcolor="#e8e8e8"),
        yaxis=dict(title="Wickets Per Over (higher = better)",
                   showgrid=True, gridcolor="#e8e8e8"),
        plot_bgcolor="white", paper_bgcolor="white", height=500,
        margin=dict(t=80, b=70, l=65, r=120),
        legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center"),
    )
    fig.add_annotation(x=0.5, y=-0.25, xref="paper", yref="paper",
                       text=SOURCE_NOTE + " | Min 200 death-over balls | Bubble = balls bowled | Color = avg opp. RPO",
                       showarrow=False, font=dict(size=10, color="grey"))
    return _style(fig)


# ── Q3: ERA SHIFT ─────────────────────────────────────────────────────────────

@st.cache_data
def q3_compute(_df):
    df_c = _df[(_df["year"] <= 2025) & (~_df["is_dls"])].copy()
    PHASES = {
        "Powerplay (1-6)": (0, 5),
        "Middle (7-15)":   (6, 14),
        "Death (16-20)":   (15, 19),
    }
    records = []
    for phase_name, (ov_min, ov_max) in PHASES.items():
        phase_df = df_c[df_c["over"].between(ov_min, ov_max)]
        over_runs = (
            phase_df.groupby(["year","match_id","innings","over"])["runs_total"]
            .sum().reset_index(name="over_runs")
        )
        yearly = (
            over_runs.groupby("year")
            .agg(total_runs=("over_runs","sum"), total_overs=("over_runs","count"))
            .reset_index()
        )
        yearly["rpo"]   = (yearly["total_runs"] / yearly["total_overs"]).round(3)
        yearly["phase"] = phase_name
        records.append(yearly)

    rpo_all = pd.concat(records, ignore_index=True)
    combined = rpo_all.pivot(index="year", columns="phase", values="rpo").sort_index()
    death_inflection = int(combined["Death (16-20)"].diff().idxmax())
    death_jump       = round(combined["Death (16-20)"].diff().max(), 2)
    return rpo_all, death_inflection, death_jump


def q3_fig(rpo_all, death_inflection, death_jump):
    COLORS = {"Powerplay (1-6)": "#1f77b4", "Middle (7-15)": "#ff7f0e", "Death (16-20)": "#d62728"}
    fig = go.Figure()
    for x0, x1, color, label in [
        (2007.5, 2012.5, "rgba(78,121,167,0.07)",  "Era 1\n(2008-12)"),
        (2012.5, 2017.5, "rgba(242,142,43,0.07)",  "Era 2\n(2013-17)"),
        (2017.5, 2025.5, "rgba(89,161,79,0.07)",   "Era 3\n(2018-25)"),
    ]:
        fig.add_vrect(x0=x0, x1=x1, fillcolor=color, layer="below", line_width=0)
        fig.add_annotation(x=(x0+x1)/2, y=13.2, text=label, showarrow=False,
                           font=dict(size=9, color="#888"), align="center")
    for phase, color in COLORS.items():
        d = rpo_all[rpo_all["phase"] == phase].sort_values("year")
        fig.add_trace(go.Scatter(
            x=d["year"], y=d["rpo"], mode="lines+markers", name=phase,
            line=dict(color=color, width=2.5), marker=dict(size=6),
            hovertemplate="<b>%{fullData.name}</b><br>%{x}: %{y:.2f} RPO<extra></extra>",
        ))
    d_rpo = rpo_all[(rpo_all["phase"]=="Death (16-20)") & (rpo_all["year"]==death_inflection)]["rpo"].values[0]
    fig.add_annotation(
        x=death_inflection, y=d_rpo,
        text=f"<b>Inflection: {death_inflection}</b><br>+{death_jump} RPO",
        showarrow=True, arrowhead=2, arrowcolor="#d62728", ax=55, ay=-40,
        font=dict(size=11, color="#d62728"), bgcolor="white",
        bordercolor="#d62728", borderwidth=1.5, borderpad=4,
    )
    fig.update_layout(
        title=dict(text="IPL Run Economy by Phase (2008-2025)", font_size=16, x=0.5),
        xaxis=dict(title="Season", tickmode="linear", dtick=2,
                   showgrid=True, gridcolor="#e8e8e8"),
        yaxis=dict(title="Runs Per Over", showgrid=True, gridcolor="#e8e8e8", range=[5.5, 13.8]),
        legend=dict(orientation="h", y=1.02, x=1, xanchor="right"),
        plot_bgcolor="white", paper_bgcolor="white", height=480,
        margin=dict(t=80, b=60, l=65, r=40),
    )
    fig.add_annotation(x=0.5, y=-0.16, xref="paper", yref="paper",
                       text=SOURCE_NOTE + " | DLS matches excluded",
                       showarrow=False, font=dict(size=10, color="grey"))
    return _style(fig)


# ── Q4: TEAM OUTPERFORMANCE ───────────────────────────────────────────────────

@st.cache_data
def q4_compute(_df):
    df_c = _df[
        _df["innings"].isin([1, 2]) &
        (~_df["is_dls"]) &
        _df["superover_winner"].isna()
    ].copy()

    innings_scores = (
        df_c.groupby(["match_id","innings","batting_team","venue","era","year"])
        ["runs_total"].sum().reset_index(name="actual_runs")
    )
    venue_exp = (
        innings_scores.groupby(["venue","innings","era"])
        .agg(expected_runs=("actual_runs","mean"), n=("actual_runs","count"))
        .reset_index()
    )
    venue_exp = venue_exp[venue_exp["n"] >= 10]
    merged = innings_scores.merge(
        venue_exp[["venue","innings","era","expected_runs"]],
        on=["venue","innings","era"], how="inner"
    )
    merged["outperformance"] = merged["actual_runs"] - merged["expected_runs"]

    team_perf = (
        merged.groupby("batting_team")
        .agg(
            avg_op    = ("outperformance","mean"),
            innings   = ("outperformance","count"),
            avg_act   = ("actual_runs","mean"),
            avg_exp   = ("expected_runs","mean"),
        )
        .reset_index()
    )
    team_perf = team_perf[team_perf["innings"] >= 50].copy()
    team_perf = team_perf.sort_values("avg_op", ascending=False).reset_index(drop=True)
    team_perf["avg_op"] = team_perf["avg_op"].round(1)

    top3 = team_perf.head(3)["batting_team"].tolist()
    yearly = (
        merged[merged["batting_team"].isin(top3)]
        .groupby(["batting_team","year"])["outperformance"]
        .mean().reset_index()
    )
    yearly["outperformance"] = yearly["outperformance"].round(1)
    return team_perf, yearly, top3


def q4_bar_fig(team_perf):
    colors = ["#2ca02c" if v >= 0 else "#d62728" for v in team_perf["avg_op"]]
    fig = go.Figure(go.Bar(
        x=team_perf["avg_op"], y=team_perf["batting_team"],
        orientation="h", marker_color=colors,
        text=[f"{v:+.1f}" for v in team_perf["avg_op"]],
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>Avg outperformance: %{x:+.1f} runs<br>"
            "Innings: %{customdata[0]}<br>Avg actual: %{customdata[1]:.0f}"
            "<extra></extra>"
        ),
        customdata=team_perf[["innings","avg_act"]].values,
    ))
    fig.add_vline(x=0, line_color="#333", line_width=1.5)
    fig.update_layout(
        title=dict(text="Team Outperformance vs Venue Average", font_size=16, x=0.5),
        xaxis=dict(title="Avg Runs Above Venue Expectation per Innings",
                   showgrid=True, gridcolor="#e8e8e8"),
        yaxis=dict(title="", autorange="reversed", tickfont=dict(size=12)),
        plot_bgcolor="white", paper_bgcolor="white",
        height=max(380, len(team_perf) * 42 + 130),
        margin=dict(t=80, b=60, l=210, r=80),
    )
    fig.add_annotation(x=0.5, y=-0.18, xref="paper", yref="paper",
                       text=SOURCE_NOTE + " | Expected = avg score at same venue, innings, era",
                       showarrow=False, font=dict(size=10, color="grey"))
    return _style(fig)


def q4_trend_fig(yearly, top3):
    TEAM_COLORS = {
        "Mumbai Indians": "#4e79a7", "Chennai Super Kings": "#f28e2b",
        "Kolkata Knight Riders": "#59a14f", "Gujarat Titans": "#e15759",
        "Rajasthan Royals": "#b07aa1",
    }
    DEFAULT = ["#4e79a7", "#f28e2b", "#59a14f"]
    fig = go.Figure()
    for i, team in enumerate(top3):
        d = yearly[yearly["batting_team"] == team].sort_values("year")
        color = TEAM_COLORS.get(team, DEFAULT[i % len(DEFAULT)])
        fig.add_trace(go.Scatter(
            x=d["year"], y=d["outperformance"],
            mode="lines+markers", name=team,
            line=dict(color=color, width=2.5), marker=dict(size=7),
            hovertemplate=f"<b>{team}</b><br>%{{x}}: %{{y:+.1f}} runs<extra></extra>",
        ))
    fig.add_hline(y=0, line_dash="dash", line_color="#aaa", line_width=1.5,
                  annotation_text="Venue average", annotation_position="top right")
    fig.update_layout(
        title=dict(text="Outperformance Trend — Top 3 Teams", font_size=15, x=0.5),
        xaxis=dict(title="Season", tickmode="linear", dtick=2,
                   showgrid=True, gridcolor="#e8e8e8"),
        yaxis=dict(title="Runs Above Venue Expectation",
                   showgrid=True, gridcolor="#e8e8e8"),
        legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center"),
        plot_bgcolor="white", paper_bgcolor="white", height=380,
        margin=dict(t=70, b=70, l=65, r=40),
    )
    return _style(fig)


# ── Q5: HOME ADVANTAGE ────────────────────────────────────────────────────────

@st.cache_data
def q5_compute(_df):
    venue_to_home_team = {
        v: team for team, venues in HOME_VENUES.items() for v in venues
    }
    matches = _df.drop_duplicates("match_id")[
        ["match_id","year","venue","match_won_by","valid_result","is_neutral_season"]
    ].copy()
    innings_teams = (
        _df[_df["innings"].isin([1,2])]
        .groupby(["match_id","innings"])["batting_team"].first()
        .unstack().rename(columns={1:"team1",2:"team2"}).reset_index()
    )
    matches = matches.merge(innings_teams, on="match_id", how="left")
    matches = matches[matches["valid_result"]].copy()

    records = []
    for _, row in matches.iterrows():
        home_team = venue_to_home_team.get(row["venue"])
        for team in [row["team1"], row["team2"]]:
            if pd.isna(team):
                continue
            won = 1 if row["match_won_by"] == team else 0
            if row["is_neutral_season"]:
                vtype = "Neutral (2020)"
            elif home_team == team:
                vtype = "Home"
            elif home_team is not None:
                vtype = "Away"
            else:
                vtype = "Neutral"
            records.append({"team": team, "venue_type": vtype, "won": won})

    tr = pd.DataFrame(records)
    ha = tr[tr["venue_type"].isin(["Home","Away"])].copy()
    team_ha = (
        ha.groupby(["team","venue_type"])
        .agg(matches=("won","count"), wins=("won","sum")).reset_index()
    )
    team_ha["win_pct"] = (team_ha["wins"] / team_ha["matches"] * 100).round(1)
    pivot = team_ha.pivot(index="team", columns="venue_type", values="win_pct").reset_index()
    pivot.columns.name = None
    cnt = team_ha.pivot(index="team", columns="venue_type", values="matches").reset_index()
    cnt.columns.name = None
    pivot = pivot.merge(cnt[["team","Home","Away"]], on="team", suffixes=("","_n"))
    pivot = pivot.rename(columns={"Home_n":"home_n","Away_n":"away_n"})
    pivot = pivot[(pivot["home_n"] >= 20) & (pivot["away_n"] >= 20)].copy()
    pivot["differential"] = (pivot["Home"] - pivot["Away"]).round(1)
    pivot = pivot.sort_values("differential", ascending=False).reset_index(drop=True)
    return pivot


def q5_fig(pivot):
    teams    = pivot["team"].tolist()
    home_pct = pivot["Home"].tolist()
    away_pct = pivot["Away"].tolist()
    diff     = pivot["differential"].tolist()

    fig = go.Figure()
    for i, (_, h, a) in enumerate(zip(teams, home_pct, away_pct)):
        fig.add_trace(go.Scatter(
            x=[a, h], y=[i, i], mode="lines",
            line=dict(color="#cccccc", width=2),
            showlegend=False, hoverinfo="skip",
        ))
    fig.add_trace(go.Scatter(
        x=away_pct, y=list(range(len(teams))), mode="markers",
        name="Away Win %",
        marker=dict(color="#e15759", size=13, symbol="circle",
                    line=dict(width=1.5, color="white")),
        hovertemplate="<b>%{customdata}</b><br>Away: %{x:.1f}%<extra></extra>",
        customdata=teams,
    ))
    fig.add_trace(go.Scatter(
        x=home_pct, y=list(range(len(teams))), mode="markers",
        name="Home Win %",
        marker=dict(color="#4e79a7", size=13, symbol="diamond",
                    line=dict(width=1.5, color="white")),
        hovertemplate="<b>%{customdata[0]}</b><br>Home: %{x:.1f}%<br>Diff: %{customdata[1]:+.1f}pp<extra></extra>",
        customdata=list(zip(teams, diff)),
    ))
    x_max = max(home_pct + away_pct)
    for i, (d, _) in enumerate(zip(diff, home_pct)):
        color = "#2ca02c" if d >= 0 else "#d62728"
        fig.add_annotation(x=x_max + 4.5, y=i,
                           text=f"<b>{d:+.1f}pp</b>",
                           showarrow=False, font=dict(size=11, color=color), xanchor="left")
    fig.add_vline(x=50, line_dash="dot", line_color="#aaa", line_width=1.5)
    fig.update_layout(
        title=dict(text="Home Ground Advantage — Win % at Home vs Away", font_size=16, x=0.5),
        xaxis=dict(title="Win Rate (%)", range=[20, x_max + 12],
                   showgrid=True, gridcolor="#e8e8e8", ticksuffix="%"),
        yaxis=dict(tickmode="array", tickvals=list(range(len(teams))), ticktext=teams,
                   showgrid=False, autorange="reversed"),
        plot_bgcolor="white", paper_bgcolor="white",
        height=max(420, len(teams) * 46 + 160),
        margin=dict(t=80, b=60, l=200, r=110),
        legend=dict(orientation="h", y=-0.14, x=0.5, xanchor="center"),
    )
    fig.add_annotation(x=0.5, y=-0.18, xref="paper", yref="paper",
                       text=SOURCE_NOTE + " | 2020 UAE season excluded | Min 20 home + 20 away matches",
                       showarrow=False, font=dict(size=10, color="grey"))
    return _style(fig)


# ── PAGES ─────────────────────────────────────────────────────────────────────

def page_home():
    st.markdown(
        "<h1 style='text-align:center;font-size:2.3rem;margin-bottom:4px;'>"
        "IPL Cricket Analytics Dashboard</h1>"
        "<p style='text-align:center;color:#666;font-size:1.05rem;margin-top:0;'>"
        "Five data questions. One consistent finding: the game rewards strategy, not luck.</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    st.markdown("""
### The Toss Trap — Lead Finding
> IPL teams invest heavily in toss strategy, yet toss winners convert to match winners
> only **51.8%** of the time — statistically indistinguishable from a coin flip.
> The story sharpens when segmented: Jaipur shows **>70% toss win rate** in Era 3
> while Dubai shows **<42%**. Teams are optimising hard for the wrong KPI — the IPL's
> version of over-indexing on a metric that doesn't drive outcomes.
""")
    st.divider()

    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown("### The Five Questions")
        for qid, qtxt in [
            ("Q1", "Does winning the toss actually win matches — and has this changed across IPL eras?"),
            ("Q2", "Which bowlers are most destructive in death overs (16-20), controlling for opposition quality?"),
            ("Q3", "Has the IPL become a batsman's game — and when exactly did the inflection point happen?"),
            ("Q4", "Which teams consistently outperform their expected runs based on venue context?"),
            ("Q5", "Is there a home ground advantage in IPL — and which franchises exploit it most vs. least?"),
        ]:
            st.markdown(f"**{qid}** &nbsp; {qtxt}")

    with col2:
        st.markdown("### About")
        st.markdown("""
**Dataset:** IPL 2008–2025 &nbsp;·&nbsp; 283,678 deliveries &nbsp;·&nbsp; 1,193 matches

**Stack:** Python &nbsp;·&nbsp; Pandas &nbsp;·&nbsp; Plotly &nbsp;·&nbsp; Streamlit

**Author:** Angajala Gautam Raju
B.Tech CSE (2026) &nbsp;·&nbsp; CGPA 8.17
[LinkedIn](https://linkedin.com/in/gautamraju18)
        """, unsafe_allow_html=True)

        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("Matches",    "1,193")
        c2.metric("Deliveries", "283K")
        c3.metric("Seasons",    "18")


def page_q1(df):
    st.title("Q1 — The Toss Trap")
    st.caption("Does winning the toss actually win matches — and has this changed across IPL eras?")

    overall_pct, era_stats, pivot, ERA_ORDER = q1_compute(df)

    st.plotly_chart(q1_era_fig(overall_pct, era_stats), width="stretch")
    st.info(
        f"**Finding:** Toss winners convert to match winners only **{overall_pct}%** of the time "
        f"across 1,169 valid matches — barely above the 50% coin-flip baseline. "
        f"Teams have shifted heavily toward choosing to field (50% in Era 1 → 76% in Era 3), "
        f"yet the fielding-first win rate is *declining* (55.7% → 53.7%). "
        f"Teams are piling into a crowded trade that's losing edge."
    )
    st.divider()

    st.plotly_chart(q1_heatmap_fig(pivot), width="stretch")
    st.info(
        "**The nuance:** Toss advantage is venue-specific. Sawai Mansingh (Jaipur) shows >70% "
        "toss win rate in Era 3 — a genuine dew-factor edge. Dubai shows <42% — toss winners "
        "actually *lose* more often there. Blanket statements about toss are wrong; "
        "the answer depends on where you're playing."
    )


def page_q2(df):
    st.title("Q2 — Death Over Specialists")
    st.caption("Which bowlers are most destructive in overs 16-20, controlling for opposition quality?")

    bs, top8 = q2_compute(df)
    st.plotly_chart(q2_fig(bs, top8), width="stretch")

    best = top8.iloc[0]
    st.info(
        f"**Finding:** Among 89 bowlers with ≥200 death-over balls, the elite tier sits in the "
        f"top-left (low economy, high wicket rate). **{best['bowler']}** leads by impact score "
        f"({best['economy']:.2f} economy, {best['wpo']:.3f} wkt/over). "
        f"Bubble size = experience; color = opposition batting strength. "
        f"Bowlers who dominate here while facing strong opposition deserve the most credit."
    )

    st.markdown("**Top 8 by Impact Score** (wickets/over ÷ economy, min 200 balls)")
    st.dataframe(
        top8[["bowler","balls","economy","wpo","opp_strength"]]
        .rename(columns={"bowler":"Bowler","balls":"Balls","economy":"Economy",
                         "wpo":"Wkt/Over","opp_strength":"Opp RPO"})
        .reset_index(drop=True),
        width="stretch", hide_index=True,
    )


def page_q3(df):
    st.title("Q3 — The Run Rate Revolution")
    st.caption("Has the IPL become a batsman's game — and when exactly did the shift happen?")

    rpo_all, death_inflection, death_jump = q3_compute(df)
    st.plotly_chart(q3_fig(rpo_all, death_inflection, death_jump), width="stretch")

    pp_rows = rpo_all[rpo_all["phase"] == "Powerplay (1-6)"].set_index("year")["rpo"]
    pp_change = round(pp_rows[2025] - pp_rows[2008], 2)
    st.info(
        f"**Finding:** All three phases have become more batting-friendly since 2008. "
        f"Powerplay scoring climbed **+{pp_change} RPO** (2008→2025) as openers became "
        f"increasingly aggressive — a gradual revolution. Death-over scoring spiked sharply "
        f"in **{death_inflection}** (+{death_jump} RPO in a single season), coinciding with "
        f"the rise of specialist finishers. Middle overs show the smallest change — "
        f"that phase remains the most contested battleground in T20 cricket."
    )


def page_q4(df):
    st.title("Q4 — Team Strategy Alpha")
    st.caption(
        "Which teams consistently outperform their expected runs based on venue context? "
        "A proxy for coaching and strategic quality."
    )

    team_perf, yearly, top3 = q4_compute(df)

    st.plotly_chart(q4_bar_fig(team_perf), width="stretch")
    st.info(
        '**Methodology:** "Expected runs" = average innings score at the same venue, innings '
        "(1st or 2nd), and era. Outperformance = actual minus expected. A franchise that "
        "consistently scores above expectation isn't just talented — they're extracting more "
        "from their lineup than the venue history predicts. That delta is the measurable "
        "fingerprint of coaching, squad selection, and batting strategy."
    )
    st.divider()

    st.plotly_chart(q4_trend_fig(yearly, top3), width="stretch")
    best = team_perf.iloc[0]
    st.info(
        f"**Finding:** **{best['batting_team']}** leads with "
        f"**{best['avg_op']:+.1f} runs/innings** above venue expectation "
        f"across {int(best['innings'])} innings. The season-by-season view shows which "
        f"teams have sustained this edge consistently vs. those who peaked in specific eras."
    )


def page_q5(df):
    st.title("Q5 — Home Ground Advantage")
    st.caption(
        "Is there a home advantage in IPL — and which franchises exploit it most vs. least? "
        "(2020 UAE season excluded as a controlled neutral environment.)"
    )

    pivot = q5_compute(df)
    st.plotly_chart(q5_fig(pivot), width="stretch")

    best  = pivot.iloc[0]
    worst = pivot.iloc[-1]
    st.info(
        f"**Finding:** Home advantage is real but unequal. **{best['team']}** shows the "
        f"strongest edge ({best['Home']:.1f}% home vs {best['Away']:.1f}% away, "
        f"**+{best['differential']:.1f}pp**) — driven by their spin-friendly venue and crowd. "
        f"**{worst['team']}** shows the smallest differential ({worst['differential']:+.1f}pp), "
        f"suggesting their competitive quality travels — a different kind of moat. "
        f"The 2020 UAE season functions as a natural experiment: teams that thrived in a "
        f"neutral environment demonstrate quality independent of venue familiarity."
    )


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    df = load_data()

    st.sidebar.title("IPL Analytics")
    st.sidebar.caption("2008 – 2025 · 1,193 Matches")
    st.sidebar.divider()

    page = st.sidebar.radio(
        "Navigate",
        options=[
            "Home",
            "Q1 — The Toss Trap",
            "Q2 — Death Over Bowlers",
            "Q3 — Era Shift",
            "Q4 — Team Outperformance",
            "Q5 — Home Advantage",
        ],
        label_visibility="collapsed",
    )

    if   page == "Home":                       page_home()
    elif page == "Q1 — The Toss Trap":         page_q1(df)
    elif page == "Q2 — Death Over Bowlers":    page_q2(df)
    elif page == "Q3 — Era Shift":             page_q3(df)
    elif page == "Q4 — Team Outperformance":   page_q4(df)
    elif page == "Q5 — Home Advantage":        page_q5(df)

    st.sidebar.divider()
    st.sidebar.caption(
        "Data: Kaggle · chaitu20  \n"
        "Built with Streamlit + Plotly"
    )


if __name__ == "__main__":
    main()
