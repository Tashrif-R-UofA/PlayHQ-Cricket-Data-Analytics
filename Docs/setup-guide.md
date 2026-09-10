# Power BI setup guide

Step-by-step walk-through for building the report from the scraper CSVs.

## Prerequisites

- Six CSVs sitting in `/data`:
  `matches.csv`, `batting_lines.csv`, `bowling_lines.csv`, `dismissals.csv`, `players.csv`, `ladder.csv` (and optionally `captains.csv`)
- Power BI Desktop OR Power BI Service with a Fabric / Premium capacity workspace for advanced features

## 1 — Load the data

Power BI → **Get Data → Folder** → point at `data/`. Combine and load.

Rename the queries: `Matches`, `Batting`, `Bowling`, `Dismissals`, `Players`, `Ladder`, `Captains`.

For each CSV query, ensure **"Use First Row as Headers"** is applied.

**Set data types explicitly** (Power Query → Transform → Data type):

- Numeric on: `home_score`, `away_score`, `home_wickets`, `away_wickets` (Whole Number)
- Decimal on: `home_overs`, `away_overs`, `strike_rate`, `economy`
- Date on: `Matches[date]`
- True/False on: `Matches[vs_top_team]`

## 2 — Create the Date table

Modeling → **New table**:

```dax
Date =
ADDCOLUMNS (
    CALENDAR ( DATE ( 2025, 1, 1 ), DATE ( 2027, 12, 31 ) ),
    "Year",      YEAR ( [Date] ),
    "Month",     FORMAT ( [Date], "MMM YYYY" ),
    "MonthNum",  YEAR ( [Date] ) * 100 + MONTH ( [Date] ),
    "DayOfWeek", FORMAT ( [Date], "dddd" ),
    "Season",    IF ( MONTH ( [Date] ) >= 10, YEAR ( [Date] ) & "/" & ( YEAR ( [Date] ) + 1 ), ( YEAR ( [Date] ) - 1 ) & "/" & YEAR ( [Date] ) )
)
```

**Modeling → Mark as date table** → `Date`.

## 3 — Build relationships

Model view, drag to create these — all **one-to-many, single direction**:

| From | To |
| --- | --- |
| `Date[Date]` | `Matches[date]` |
| `Matches[game_id]` | `Batting[game_id]` |
| `Matches[game_id]` | `Bowling[game_id]` |
| `Matches[game_id]` | `Dismissals[game_id]` |
| `Players[player_id]` | `Batting[player_id]` |
| `Players[player_id]` | `Bowling[player_id]` |
| `Players[player_id]` | `Dismissals[batter_player_id]` |

Ladder does NOT need an active relationship — the scraper already enriches `Matches` with `vs_top_team`.

## 4 — Add calculated columns to Matches

From `docs/dax-measures.md`, paste each in one at a time via **New column**:
`Opponent`, `OurScore`, `TheirScore`, `OurOvers`, `TheirOvers`, `OurWickets`, `TheirWickets`, `RoundNum`.

## 5 — Add the fielder_team_final calculated column to Dismissals

```dax
fielder_team_final =
VAR pid = Dismissals[fielder_player_id]
VAR fromBat  = CALCULATE ( MAX ( Batting[team] ),  Batting[player_id] = pid )
VAR fromBowl = CALCULATE ( MAX ( Bowling[team] ), Bowling[player_id] = pid )
RETURN COALESCE ( fromBat, fromBowl )
```

Enables fielding-team attribution for catches.

## 6 — Create the _Measures holder table

Modeling → New table:

```dax
_Measures = { BLANK() }
```

Hide the `Value` column. Home-table every measure you create to this table for cleanliness.

## 7 — Create the measures

Paste each measure from `docs/dax-measures.md` — go section by section:

1. Match-level KPIs (7 measures)
2. Batting measures (12 measures)
3. Bowling measures (11 measures)
4. Fielding measures (3 measures)
5. Captaincy measures (3 measures)
6. Contextual variants — Wins + VsTop (roughly 2 per base = 40+ measures)
7. Award/leaderboard measures (9 measures)

Total: 70+ explicit measures.

**Tip:** create dependency measures first (e.g., `Bat_Runs` before `Bat_Avg` which references it).

## 8 — Create the Awards helper table

Modeling → **Enter data**:

| Matrix | SortOrder |
| --- | --- |
| Most Runs | 1 |
| Most Wickets | 2 |
| Highest Individual Score | 3 |
| Best Bowling Figure | 4 |
| Highest Strike Rate | 5 |
| Best Economy | 6 |
| Most Fours | 7 |
| Most Sixes | 8 |
| Most Catches | 9 |

Name: `Awards`. Sort `Matrix` by `SortOrder` (Column tools → Sort by column).

## 9 — Build the four report pages

### Page 1 — Overview

- Row 1 — six cards: `MatchesPlayed`, `WinPct`, `AvgRunsPerGame`, `BattingRunRate`, `AvgWicketsTakenPerGame`, `BowlingEconomyRate`
- Row 2 — clustered column: `competition` on X, `Wins` + `Losses` on Y
- Row 2 — line chart: `RoundNum` on X, `OurScore` on Y, `competition` as legend
- Row 3 — bar chart: `captain` on Y, `CaptainWinPct` on X
- Row 3 — matrix: `Awards[Matrix]` rows, `Award_Value` values → "Season Leaders" leaderboard

### Page 2 — Batting Stats

Table visual with `Batting[player_name]` filtered to Southern Strikers + all base batting measures (Bat_Runs, Bat_Innings, Bat_Avg, Bat_SR, Bat_Fours, Bat_Sixes, Bat_BoundaryPct, Bat_HS, Bat_50s, Bat_100s).

### Page 3 — Bowling Stats

Same shape as batting, but with bowling measures (Bowl_Wkts, Bowl_Overs, Bowl_Runs, Bowl_Avg, Bowl_Econ, Bowl_SR, Bowl_BestFig, Bowl_3wi, Bowl_5wi).

### Page 4 — Impact (three-column comparison)

Three side-by-side tables per discipline:
- Left: **Overall — Top 5** using base measures
- Middle: **In Winning Games — Top 5** using `_Wins` variants
- Right: **vs Teams Above Us — Top 5** using `_VsTop` variants

Apply Top N filter on `player_name` by `Bat_Runs` (or `Bowl_Wkts`).

## 10 — Format and polish

- Consistent card style — format one, copy visual → paste special → formatting only for the rest
- Alternate row colours on tables
- Southern Strikers red (`#D94848`) and blue (`#3B82F6`) as data colours
- Titles on every visual
- Add text boxes as section headers ("Batting Impacts", "Bowling Impacts") on the Impact page
- Report background: dark navy or clean white

## 11 — Publish

**Power BI Desktop → File → Publish** → pick a workspace (Fabric-capacity workspace recommended if using calculation groups).

## Refreshing

1. Re-run `python scraper/playhq_scraper.py`
2. Power BI → **Refresh** — pulls updated CSVs and recalculates every measure

Set up a schedule in Power BI Service to auto-refresh if you drop the CSVs into OneDrive / SharePoint.
