-- ============================================================
-- IPL Analytics Dashboard — Q1 Toss Analysis (SQL Equivalent)
-- Author : Angajala Gautam Raju
-- Source : IPL Dataset 2008-2025 (Kaggle: chaitu20)
-- ============================================================
-- Assumed schema (two normalized tables):
--
--   matches(
--       match_id        INTEGER PRIMARY KEY,
--       date            DATE,
--       year            INTEGER,
--       season          TEXT,
--       venue           TEXT,
--       toss_winner     TEXT,
--       toss_decision   TEXT,      -- 'bat' or 'field'
--       match_won_by    TEXT,      -- team name or 'Unknown'
--       result_type     TEXT,      -- NULL for normal results
--       method          TEXT       -- 'D/L' if Duckworth-Lewis applied
--   )
--
--   deliveries(
--       id              INTEGER PRIMARY KEY,
--       match_id        INTEGER REFERENCES matches(match_id),
--       innings         INTEGER,
--       over            INTEGER,   -- 0-indexed (0=first over, 19=last over)
--       ball            INTEGER,
--       batting_team    TEXT,
--       bowling_team    TEXT,
--       batter          TEXT,
--       bowler          TEXT,
--       runs_total      INTEGER,
--       runs_bowler     INTEGER,
--       valid_ball      INTEGER,   -- 1 = legal delivery, 0 = wide/no-ball
--       bowler_wicket   INTEGER,   -- 1 = bowler dismissed batter
--       wicket_kind     TEXT
--   )
--
-- NOTE: Run each labeled block independently or as a full script.
-- ============================================================


-- ============================================================
-- STEP 1: Normalize team names
-- Franchise renames across IPL history must be unified before
-- any win-rate calculation, or old/new names split the counts.
-- ============================================================

-- Inline normalization function (use a VIEW or CTE in practice).
-- Mapping applied everywhere toss_winner and match_won_by are used:
--   Deccan Chargers        -> Sunrisers Hyderabad
--   Delhi Daredevils       -> Delhi Capitals
--   Kings XI Punjab        -> Punjab Kings
--   Rising Pune Supergiant -> Rising Pune Supergiants
--   Royal Challengers Bengaluru -> Royal Challengers Bangalore

-- ============================================================
-- STEP 2: Base CTE — clean matches only
-- Excludes: ties / no-results (match_won_by = 'Unknown')
--           DLS-affected matches (method = 'D/L')
-- ============================================================

WITH

normalized AS (
    -- Apply team name normalization in one place; reused below.
    SELECT
        match_id,
        year,
        venue,
        toss_decision,
        CASE toss_winner
            WHEN 'Deccan Chargers'              THEN 'Sunrisers Hyderabad'
            WHEN 'Delhi Daredevils'             THEN 'Delhi Capitals'
            WHEN 'Kings XI Punjab'              THEN 'Punjab Kings'
            WHEN 'Rising Pune Supergiant'       THEN 'Rising Pune Supergiants'
            WHEN 'Royal Challengers Bengaluru'  THEN 'Royal Challengers Bangalore'
            ELSE toss_winner
        END AS toss_winner,
        CASE match_won_by
            WHEN 'Deccan Chargers'              THEN 'Sunrisers Hyderabad'
            WHEN 'Delhi Daredevils'             THEN 'Delhi Capitals'
            WHEN 'Kings XI Punjab'              THEN 'Punjab Kings'
            WHEN 'Rising Pune Supergiant'       THEN 'Rising Pune Supergiants'
            WHEN 'Royal Challengers Bengaluru'  THEN 'Royal Challengers Bangalore'
            ELSE match_won_by
        END AS match_won_by
    FROM matches
),

clean_matches AS (
    SELECT
        match_id,
        year,
        venue,
        toss_winner,
        toss_decision,
        match_won_by,
        -- Era classification (boundaries at major IPL structural changes)
        CASE
            WHEN year BETWEEN 2008 AND 2012 THEN 'Era 1 (2008-12)'
            WHEN year BETWEEN 2013 AND 2017 THEN 'Era 2 (2013-17)'
            WHEN year BETWEEN 2018 AND 2025 THEN 'Era 3 (2018-25)'
        END AS era,
        -- Core flag: did the toss winner also win the match?
        CASE
            WHEN toss_winner = match_won_by THEN 1
            ELSE 0
        END AS toss_win
    FROM normalized
    WHERE
        match_won_by != 'Unknown'   -- exclude ties and no-result matches
        AND method IS NULL          -- exclude DLS-affected matches
        AND year <= 2025            -- exclude partial 2026 season
),

-- ============================================================
-- STEP 3: Overall toss win rate
-- Baseline — is the toss winner winning more than 50% of games?
-- ============================================================

overall AS (
    SELECT
        'Overall'                            AS breakdown,
        'All'                                AS category,
        COUNT(*)                             AS total_matches,
        SUM(toss_win)                        AS toss_wins,
        ROUND(AVG(toss_win) * 100.0, 1)     AS toss_win_pct
    FROM clean_matches
),

-- ============================================================
-- STEP 4: Toss win rate by era
-- Does the toss-match correlation change over time?
-- If the effect were growing, we'd see Era 3 >> Era 1.
-- If it's flat at ~50%, era doesn't matter.
-- ============================================================

by_era AS (
    SELECT
        'By Era'                             AS breakdown,
        era                                  AS category,
        COUNT(*)                             AS total_matches,
        SUM(toss_win)                        AS toss_wins,
        ROUND(AVG(toss_win) * 100.0, 1)     AS toss_win_pct
    FROM clean_matches
    WHERE era IS NOT NULL
    GROUP BY era
    ORDER BY era
),

-- ============================================================
-- STEP 5: Toss win rate by decision (bat vs field)
-- The key split: teams increasingly choose to field.
-- Does that choice actually pay off — and is the edge shrinking?
-- ============================================================

by_decision AS (
    SELECT
        'By Decision'                        AS breakdown,
        toss_decision                        AS category,
        COUNT(*)                             AS total_matches,
        SUM(toss_win)                        AS toss_wins,
        ROUND(AVG(toss_win) * 100.0, 1)     AS toss_win_pct
    FROM clean_matches
    GROUP BY toss_decision
),

-- ============================================================
-- STEP 6: Toss decision preference trend by era
-- How has the bat/field split shifted across IPL history?
-- ============================================================

decision_preference AS (
    SELECT
        era,
        toss_decision,
        COUNT(*)                                          AS match_count,
        ROUND(
            COUNT(*) * 100.0 /
            SUM(COUNT(*)) OVER (PARTITION BY era),
        1)                                                AS pct_of_era_matches
    FROM clean_matches
    WHERE era IS NOT NULL
    GROUP BY era, toss_decision
    ORDER BY era, toss_decision
),

-- ============================================================
-- STEP 7: Venue-level toss win rate
-- Segment by venue to find where toss actually matters.
-- Dew-factor venues (evening games) tend to favour chasing.
-- ============================================================

venue_counts AS (
    -- Pre-filter to venues with sufficient sample (>= 20 matches).
    -- Venues with fewer matches produce statistically noisy rates.
    SELECT venue, COUNT(*) AS n
    FROM clean_matches
    GROUP BY venue
    HAVING COUNT(*) >= 20
),

by_venue AS (
    SELECT
        'By Venue'                           AS breakdown,
        c.venue                              AS category,
        COUNT(*)                             AS total_matches,
        SUM(c.toss_win)                      AS toss_wins,
        ROUND(AVG(c.toss_win) * 100.0, 1)   AS toss_win_pct
    FROM clean_matches c
    INNER JOIN venue_counts vc ON c.venue = vc.venue
    GROUP BY c.venue
    ORDER BY toss_win_pct DESC
),

-- ============================================================
-- STEP 8: Era × venue interaction
-- The nuanced finding: toss advantage is venue-specific AND
-- era-specific. A venue that showed strong toss advantage in
-- Era 1 may show none in Era 3 (different pitch/dew conditions,
-- different team strategies).
-- ============================================================

era_venue AS (
    SELECT
        c.era,
        c.venue,
        COUNT(*)                             AS total_matches,
        SUM(c.toss_win)                      AS toss_wins,
        ROUND(AVG(c.toss_win) * 100.0, 1)   AS toss_win_pct
    FROM clean_matches c
    INNER JOIN venue_counts vc ON c.venue = vc.venue
    WHERE c.era IS NOT NULL
    GROUP BY c.era, c.venue
    HAVING COUNT(*) >= 10   -- need at least 10 matches per era-venue cell
    ORDER BY c.era, toss_win_pct DESC
)

-- ============================================================
-- FINAL OUTPUT: Union all breakdowns into a single result set.
-- Run this block to get the full toss analysis summary.
-- ============================================================

SELECT breakdown, category, total_matches, toss_wins, toss_win_pct
FROM overall

UNION ALL

SELECT breakdown, category, total_matches, toss_wins, toss_win_pct
FROM by_era

UNION ALL

SELECT breakdown, category, total_matches, toss_wins, toss_win_pct
FROM by_decision

UNION ALL

SELECT breakdown, category, total_matches, toss_wins, toss_win_pct
FROM by_venue

ORDER BY breakdown, toss_win_pct DESC;


-- ============================================================
-- BONUS QUERY: Decision preference trend (separate SELECT)
-- Run this independently to see bat vs field shift by era.
-- ============================================================
/*
SELECT
    era,
    toss_decision,
    match_count,
    pct_of_era_matches
FROM decision_preference;
*/


-- ============================================================
-- BONUS QUERY: Era x venue interaction matrix
-- Shows where toss advantage is real vs negligible by era.
-- ============================================================
/*
SELECT era, venue, total_matches, toss_win_pct
FROM era_venue
ORDER BY era, toss_win_pct DESC;
*/
