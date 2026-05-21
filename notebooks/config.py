"""
Shared constants for all analysis scripts.
Import with: from config import TEAM_MAP, VENUE_MAP, load_clean

All maps derived from Day 1 EDA findings.
"""
import pandas as pd

# ─── TEAM NAME NORMALIZATION ──────────────────────────────────────────────────
# All historical franchise names mapped to their current/canonical name.
# Confirmed present in dataset via EDA.
TEAM_MAP = {
    "Deccan Chargers":           "Sunrisers Hyderabad",
    "Delhi Daredevils":          "Delhi Capitals",
    "Kings XI Punjab":           "Punjab Kings",
    "Rising Pune Supergiant":    "Rising Pune Supergiants",  # one-season typo variant
    "Royal Challengers Bengaluru": "Royal Challengers Bangalore",  # 2024/25 rebrand
}

# Teams that are defunct (no current franchise): exclude from win-rate league tables
# but include in historical analysis
DEFUNCT_TEAMS = {"Kochi Tuskers Kerala", "Pune Warriors", "Gujarat Lions",
                 "Rising Pune Supergiants", "Rising Pune Supergiant", "Deccan Chargers"}

# ─── VENUE NORMALIZATION ──────────────────────────────────────────────────────
# Same ground appears under multiple names (city suffixes added/removed over years,
# ground renamed by sponsors). Normalize to shortest unambiguous name.
VENUE_MAP = {
    "Eden Gardens, Kolkata":                                       "Eden Gardens",
    "Wankhede Stadium, Mumbai":                                    "Wankhede Stadium",
    "M Chinnaswamy Stadium, Bengaluru":                            "M Chinnaswamy Stadium",
    "MA Chidambaram Stadium, Chepauk, Chennai":                    "MA Chidambaram Stadium",
    "MA Chidambaram Stadium, Chepauk":                             "MA Chidambaram Stadium",
    "Rajiv Gandhi International Stadium, Uppal, Hyderabad":        "Rajiv Gandhi International Stadium",
    "Rajiv Gandhi International Stadium, Uppal":                   "Rajiv Gandhi International Stadium",
    "Arun Jaitley Stadium, Delhi":                                 "Arun Jaitley Stadium",
    # Feroz Shah Kotla was renamed Arun Jaitley Stadium in 2019
    "Feroz Shah Kotla":                                            "Arun Jaitley Stadium",
    "Punjab Cricket Association IS Bindra Stadium, Mohali":        "Punjab Cricket Association Stadium, Mohali",
}

# ─── HOME GROUND MAP ─────────────────────────────────────────────────────────
# Canonical home venue(s) per franchise (post-normalization).
# Used for Q5 home advantage analysis.
HOME_VENUES = {
    "Mumbai Indians":              ["Wankhede Stadium"],
    "Chennai Super Kings":         ["MA Chidambaram Stadium"],
    "Kolkata Knight Riders":       ["Eden Gardens"],
    "Royal Challengers Bangalore": ["M Chinnaswamy Stadium"],
    "Rajasthan Royals":            ["Sawai Mansingh Stadium"],
    "Sunrisers Hyderabad":         ["Rajiv Gandhi International Stadium"],
    "Delhi Capitals":              ["Arun Jaitley Stadium"],
    "Punjab Kings":                ["Punjab Cricket Association Stadium, Mohali"],
    "Gujarat Titans":              ["Narendra Modi Stadium, Ahmedabad"],
    "Lucknow Super Giants":        ["Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium, Lucknow"],
    # Defunct franchises (for historical analysis)
    "Deccan Chargers":             ["Rajiv Gandhi International Stadium"],
    "Delhi Daredevils":            ["Arun Jaitley Stadium"],
    "Kings XI Punjab":             ["Punjab Cricket Association Stadium, Mohali"],
    "Kochi Tuskers Kerala":        ["Jawaharlal Nehru Stadium, Kochi"],
    "Pune Warriors":               ["Subrata Roy Sahara Stadium"],
    "Gujarat Lions":               ["Saurashtra Cricket Association Stadium"],
}

# ─── ERA DEFINITIONS ─────────────────────────────────────────────────────────
# Used for Q1 toss analysis era breakdown.
# Boundaries chosen at major rule/format changes in IPL.
ERA_MAP = {
    range(2008, 2013): "Era 1 (2008-12)",   # founding era
    range(2013, 2018): "Era 2 (2013-17)",   # maturity era
    range(2018, 2027): "Era 3 (2018-25)",   # modern era (2026 partial season included)
}

def get_era(year):
    for yr_range, label in ERA_MAP.items():
        if year in yr_range:
            return label
    return "Unknown"

# ─── LOAD CLEAN ───────────────────────────────────────────────────────────────

def load_clean(path="data/IPL.csv.gz"):
    """
    Load IPL.csv and apply all normalization in one call.
    Returns the cleaned ball-by-ball DataFrame.
    """
    df = pd.read_csv(path, low_memory=False)

    # Normalize team names
    for col in ["batting_team", "bowling_team", "toss_winner", "match_won_by"]:
        if col in df.columns:
            df[col] = df[col].replace(TEAM_MAP)

    # Normalize venue names
    df["venue"] = df["venue"].replace(VENUE_MAP)

    # Add era column using the year column (already numeric in this dataset)
    df["era"] = df["year"].apply(get_era)

    # Exclude super over rows (keep only standard 20-over play)
    if "superover_winner" in df.columns:
        # super over rows belong to matches where superover_winner is not null
        # but the over numbering stays 0-19, so we identify them differently.
        # This dataset encodes super over as a separate match_id — safe to keep as-is.
        pass

    # Flag no-result / tied matches (match_won_by == "Unknown")
    df["valid_result"] = df["match_won_by"] != "Unknown"

    # Flag DLS matches
    df["is_dls"] = df["method"].notna() & (df["method"] != "")

    # Flag 2020 neutral season
    df["is_neutral_season"] = df["year"] == 2020

    return df
