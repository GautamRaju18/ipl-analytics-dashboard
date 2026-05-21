"""
IPL Analytics Dashboard — Day 1 EDA
Dataset: IPL.csv (single pre-merged CSV, 2008-2025)
Run from repo root:  python notebooks/eda.py
Save output:         python notebooks/eda.py > outputs/eda_report.txt
"""

import pandas as pd
import numpy as np
import os, sys

SEP = "=" * 72

def section(title):
    print(f"\n{SEP}\n  {title}\n{SEP}")

# ─── LOAD ─────────────────────────────────────────────────────────────────────

def load_data():
    path = "data/IPL.csv"
    if not os.path.exists(path):
        print(f"ERROR: {path} not found.")
        print("Download via: kaggle datasets download -d chaitu20/ipl-dataset2008-2025 -p data/ --unzip")
        sys.exit(1)
    df = pd.read_csv(path, low_memory=False)
    print(f"Loaded: {df.shape[0]:,} rows × {df.shape[1]} columns")
    return df

# ─── BASIC INSPECTION ─────────────────────────────────────────────────────────

def inspect(df):
    section("SHAPE & COLUMNS")
    print(f"Shape: {df.shape[0]:,} rows × {df.shape[1]} columns\n")
    print("All columns:")
    for i, c in enumerate(df.columns, 1):
        print(f"  {i:>2}. {c}")

    section("DTYPES")
    print(df.dtypes.to_string())

    section("NULL COUNTS (columns with any nulls)")
    nulls = df.isnull().sum()
    null_cols = nulls[nulls > 0].sort_values(ascending=False)
    if len(null_cols) > 0:
        pct = (null_cols / len(df) * 100).round(2)
        summary = pd.DataFrame({"null_count": null_cols, "null_%": pct})
        print(summary.to_string())
        print(f"\nTotal null cells : {nulls.sum():,}")
        print(f"Columns with nulls: {len(null_cols)} / {df.shape[1]}")
    else:
        print("No null values — perfectly clean dataset.")

    section("SAMPLE — first 3 rows (key columns only)")
    key_cols = [c for c in [
        "match_id", "date", "season", "year", "batting_team", "bowling_team",
        "over", "ball", "batter", "bowler", "runs_total", "runs_batter",
        "wicket_kind", "toss_winner", "toss_decision", "match_won_by", "venue"
    ] if c in df.columns]
    print(df[key_cols].head(3).to_string())

# ─── VALUE COUNTS ─────────────────────────────────────────────────────────────

def value_counts_report(df):
    section("VALUE COUNTS — season")
    print(df["season"].value_counts().sort_index().to_string())

    section("VALUE COUNTS — year")
    print(df["year"].value_counts().sort_index().to_string())

    section("VALUE COUNTS — toss_decision")
    print(df["toss_decision"].value_counts().to_string())

    section("VALUE COUNTS — venue (top 20)")
    print(df["venue"].value_counts().head(20).to_string())

    section("VALUE COUNTS — match_won_by (top 20, who won each match)")
    if "match_won_by" in df.columns:
        print(df["match_won_by"].value_counts().head(20).to_string())

    section("VALUE COUNTS — result_type / method")
    for col in ["result_type", "method", "win_outcome"]:
        if col in df.columns:
            print(f"\n--- {col} ---")
            print(df[col].value_counts().head(15).to_string())

# ─── OVER NUMBERING ───────────────────────────────────────────────────────────

def over_check(df):
    section("OVER NUMBERING — 0-indexed or 1-indexed?")
    mn, mx = df["over"].min(), df["over"].max()
    print(f"Min over : {mn}")
    print(f"Max over : {mx}")
    if mn == 0:
        print("\nCONFIRMED: Overs are 0-indexed (0–19).")
        print("ACTION REQUIRED: Add +1 in all phase filters.")
        print("  Powerplay  (overs 1-6)   -> filter: over.between(0, 5)")
        print("  Middle     (overs 7-15)  -> filter: over.between(6, 14)")
        print("  Death      (overs 16-20) -> filter: over.between(15, 19)")
    else:
        print(f"\nOvers are 1-indexed (1–{mx}). No transform needed.")
    # Distribution
    print(f"\nOver distribution (count of delivery rows per over):")
    print(df["over"].value_counts().sort_index().to_string())

# ─── MATCH-LEVEL EXTRACTION ───────────────────────────────────────────────────

def match_level(df):
    section("MATCH-LEVEL EXTRACTION — one row per match")
    # Deduplicate to match level using first occurrence per match_id
    match_cols = [c for c in [
        "match_id", "date", "season", "year", "venue", "city",
        "toss_winner", "toss_decision", "match_won_by", "win_outcome",
        "result_type", "method", "player_of_match", "stage",
        "superover_winner", "batting_team", "bowling_team"
    ] if c in df.columns]

    matches = df.drop_duplicates(subset=["match_id"])[match_cols].copy()
    print(f"Unique matches: {len(matches):,}")
    print(f"Date range    : {df['date'].min()} → {df['date'].max()}")

    section("MATCH-LEVEL — matches per season")
    per_season = matches.groupby("season").size().reset_index(name="matches")
    print(per_season.to_string(index=False))

    return matches

# ─── ANOMALY FLAGS ────────────────────────────────────────────────────────────

def anomalies(df, matches):
    section("ANOMALY FLAGS — null / tied / no-result matches")
    null_winner = matches[matches["match_won_by"].isnull()]
    print(f"Matches with null match_won_by : {len(null_winner)}")
    if len(null_winner) > 0:
        show = [c for c in ["match_id","season","date","venue","result_type","method"] if c in null_winner.columns]
        print(null_winner[show].to_string(index=False))

    if "result_type" in matches.columns:
        print(f"\nresult_type breakdown:")
        print(matches["result_type"].value_counts().to_string())

    section("ANOMALY FLAGS — Super Overs")
    if "superover_winner" in df.columns:
        so_matches = matches[matches["superover_winner"].notna()]
        print(f"Matches that went to Super Over : {len(so_matches)}")
        if len(so_matches) > 0:
            print(so_matches[["match_id","season","date","venue","superover_winner"]].to_string(index=False))

    section("ANOMALY FLAGS — DLS / Reduced-over matches")
    if "method" in df.columns:
        dls = matches[matches["method"].notna() & (matches["method"] != "")]
        print(f"Matches with a method (DLS etc.): {len(dls)}")
        if len(dls) > 0:
            print(dls["method"].value_counts().to_string())

    section("ANOMALY FLAGS — 2020 season venues (COVID neutral venues)")
    m2020 = matches[matches["season"].astype(str).str.contains("2020")]
    print(f"2020 season matches : {len(m2020)}")
    if len(m2020) > 0:
        print("Venues used in 2020:")
        all_2020_venues = df[df["season"].astype(str).str.contains("2020")]["venue"].value_counts()
        print(all_2020_venues.to_string())

# ─── TEAM NAME INVENTORY ──────────────────────────────────────────────────────

def team_names(df):
    section("UNIQUE TEAM NAMES — all team columns")
    all_teams = set()
    for col in ["batting_team", "bowling_team", "toss_winner", "match_won_by"]:
        if col in df.columns:
            all_teams.update(df[col].dropna().unique())
    print(f"Total unique team names across all columns: {len(all_teams)}\n")
    for t in sorted(all_teams):
        print(f"  {t}")

    section("TEAM NAME NORMALIZATION MAP")
    name_map = {
        "Deccan Chargers":        "Sunrisers Hyderabad",
        "Delhi Daredevils":       "Delhi Capitals",
        "Kings XI Punjab":        "Punjab Kings",
        "Rising Pune Supergiant": "Rising Pune Supergiants",
    }
    print("name_map = {")
    for old, new in name_map.items():
        in_data = old in all_teams
        print(f'    "{old}": "{new}",  # in dataset: {in_data}')
    print("}")
    print("\nVerify the 'in dataset' flags above — only apply renames that exist.")
    print("Usage: df['col'] = df['col'].replace(name_map)")

    section("DELIVERIES PER TEAM (batting_team) — quick sanity check")
    print(df["batting_team"].value_counts().to_string())

# ─── PHASE FILTERS SANITY CHECK ───────────────────────────────────────────────

def phase_check(df):
    section("PHASE FILTER SANITY CHECK (0-indexed overs)")
    phases = {
        "Powerplay  (overs 1-6,  filter 0-5) ": df["over"].between(0, 5),
        "Middle     (overs 7-15, filter 6-14)": df["over"].between(6, 14),
        "Death      (overs 16-20,filter 15-19)": df["over"].between(15, 19),
    }
    total = len(df)
    for label, mask in phases.items():
        count = mask.sum()
        print(f"  {label}: {count:>7,} rows ({count/total*100:.1f}%)")

    # Verify no gaps or overlaps
    covered = sum(m.sum() for m in phases.values())
    print(f"\n  Total covered : {covered:>7,}")
    print(f"  Total rows    : {total:>7,}")
    leftover = total - covered
    print(f"  Uncovered rows: {leftover:>7,}  ← should be 0 or only super-over overs")

# ─── RUNS DISTRIBUTION ────────────────────────────────────────────────────────

def runs_check(df):
    section("RUNS PER BALL DISTRIBUTION (runs_total)")
    print(df["runs_total"].value_counts().sort_index().to_string())

    section("WICKET TYPES DISTRIBUTION (wicket_kind)")
    if "wicket_kind" in df.columns:
        print(df["wicket_kind"].value_counts().to_string())

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{SEP}")
    print("  IPL ANALYTICS DASHBOARD — DAY 1 EDA (Single-CSV format)")
    print(f"{SEP}")

    df = load_data()

    inspect(df)
    value_counts_report(df)
    over_check(df)

    matches = match_level(df)

    anomalies(df, matches)
    team_names(df)
    phase_check(df)
    runs_check(df)

    section("EDA COMPLETE — PRE-DAY 2 CHECKLIST")
    checklist = [
        "[ ] Over filter confirmed: 0-indexed → use .between(0,5) for powerplay etc.",
        "[ ] name_map verified: check 'in dataset: True' flags above, add any missing renames",
        "[ ] Null match_won_by count noted → exclude from all win-rate calculations",
        "[ ] Super over matches noted → exclude from economy/run-rate analysis",
        "[ ] DLS matches noted → exclude from Q3 (run-rate era analysis)",
        "[ ] 2020 season flagged → exclude from Q5 (home advantage)",
        "[ ] season format confirmed as '2007/08' → use 'year' column for numeric era splits",
        "[ ] Toss columns confirmed: toss_winner, toss_decision, match_won_by all present",
        "[ ] Venue column clean → check top 8 venues by match count for Q1 heatmap",
        "[ ] runs_total column verified as ball-level total (batter + extras) for Q3/Q4",
    ]
    for item in checklist:
        print(f"  {item}")
    print(f"\nSave this output: python notebooks/eda.py > outputs/eda_report.txt")

if __name__ == "__main__":
    main()
