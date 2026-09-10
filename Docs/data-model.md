# Data model

The scraper produces six CSVs that form a clean star schema for Power BI. This document describes each table and the relationships between them.

## Tables

### matches.csv (fact)

One row per scheduled game. Central fact table — every other table joins to this via `game_id`.

| Column | Type | Description |
| --- | --- | --- |
| `competition` | text | Label for the competition (e.g. "PASA Multicultural T20 Winter 2026") |
| `our_team_id` | text | PlayHQ ID for Southern Strikers within this competition |
| `our_team_name` | text | Always "Southern Strikers" |
| `our_side` | text | `HOME` or `AWAY` — which side we batted/fielded first |
| `our_result` | text | `WIN`, `LOSS`, `DRAW`, `TIE`, `NO_RESULT` |
| `grade_name`, `grade_type` | text | Competition grade info |
| `round_name` | text | e.g. "Round 1" |
| `game_id` | text | Primary key |
| `date` | date | Match date (ISO) |
| `time` | text | Start time |
| `venue_name`, `venue_suburb`, `court_name` | text | Venue details |
| `game_type` | text | e.g. "T20" |
| `status` | text | `FINAL`, `CANCELLED`, `UPCOMING`, `FORFEIT` |
| `home_team_id`, `home_team_name` | text | Home side |
| `away_team_id`, `away_team_name` | text | Away side |
| `home_score`, `home_wickets`, `home_overs` | numeric | Home total |
| `away_score`, `away_wickets`, `away_overs` | numeric | Away total |
| `winner_side` | text | `HOME`, `AWAY`, or null |
| `outcome` | text | Description ("Team A won by points", "Forfeit", etc.) |
| `our_position` | int | Southern Strikers' final ladder position for the competition |
| `opponent_position` | int | Opposition's ladder position |
| `vs_top_team` | bool | `TRUE` if opposition finished above us |

Once loaded, three calculated columns are typically derived in Power BI:
- `Opponent`, `OurScore`, `OurOvers` — perspective-aware pivots of the home/away fields

### batting_lines.csv (fact)

One row per player-innings-batted. Joins to `matches` via `game_id`, to `players` via `player_id`.

| Column | Type | Description |
| --- | --- | --- |
| `game_id` | text | FK → matches |
| `competition`, `date`, `round_name` | text | Denormalised for convenient filtering |
| `team` | text | Which team the batter was on for this game |
| `innings` | text | `FIRST_INNINGS`, `SECOND_INNINGS`, etc. |
| `player_id`, `profile_id`, `player_name` | text | Batter identity |
| `lineup_order`, `batting_position` | int | Batting order |
| `status` | text | `OUT`, `NOT_OUT`, `DID_NOT_BAT`, `RETIRED` |
| `runs`, `balls`, `fours`, `sixes`, `strike_rate` | numeric | Innings stats |

### bowling_lines.csv (fact)

One row per player-innings-bowled.

| Column | Type | Description |
| --- | --- | --- |
| `game_id` | text | FK → matches |
| `competition`, `date`, `round_name` | text | Filtering aids |
| `team` | text | Which team the bowler was on |
| `innings` | text | Innings identifier |
| `player_id`, `profile_id`, `player_name` | text | Bowler identity |
| `overs`, `maidens`, `runs_conceded`, `wickets`, `economy`, `wides`, `no_balls` | numeric | Bowling figures |

### dismissals.csv (fact)

One row per wicket event.

| Column | Type | Description |
| --- | --- | --- |
| `game_id` | text | FK → matches |
| `competition`, `date`, `round_name` | text | Filtering aids |
| `innings` | text | |
| `batter_player_id` | text | Who got out |
| `batter_team_id` | text | Their team |
| `dismissal_type` | text | `CAUGHT`, `BOWLED`, `LBW`, `RUN_OUT`, `STUMPED`, `RUN_OUT_PRIOR_TO_BALL_DELIVERY` |
| `bowler_player_id` | text | Who took the wicket (nullable — no bowler for run-outs) |
| `fielder_player_id` | text | Fielder involved (catcher, keeper, run-out effector; nullable) |

### players.csv (dim)

Unique player registry — one row per player_id observed across any competition.

| Column | Type | Description |
| --- | --- | --- |
| `player_id` | text | PK |
| `profile_id` | text | PlayHQ profile ID |
| `player_name` | text | Display name |
| `teams` | text | Pipe-separated list of teams they've played for |

### ladder.csv (dim)

Final standings per competition — one row per (competition, team).

| Column | Type | Description |
| --- | --- | --- |
| `competition` | text | Competition label |
| `position` | int | 1 = top of ladder |
| `team_id`, `team_name` | text | |
| `played`, `won`, `lost`, `drawn`, `ties`, `no_results`, `byes`, `forfeits` | int | Match counts |
| `competition_points`, `points_for`, `points_against`, `points_difference` | numeric | Standings math |
| `percentage`, `net_run_rate` | numeric | Tiebreakers |
| `runs_for`, `overs_faced`, `wickets_lost` | numeric | Team batting totals |
| `runs_against`, `overs_bowled`, `wickets_taken` | numeric | Team bowling totals |

### captains.csv (manually maintained)

Because PlayHQ's public GraphQL doesn't expose the captain flag, this is a hand-maintained lookup that the scraper reads on every refresh and joins into `matches.csv`.

| Column | Type | Description |
| --- | --- | --- |
| `game_id` | text | FK → matches |
| `captain_player_id` | text | Which player captained (from players.csv) |
| `captain_player_name` | text | Human-readable name |

The scraper seeds this file on first run with all played game_ids and blank captain fields — you fill it in once, and it persists across every future scrape.

## Relationships

| From | To | Cardinality | Cross-filter | Notes |
| --- | --- | --- | --- | --- |
| `Date[Date]` | `Matches[date]` | 1 → * | Single | Standard calendar |
| `Matches[game_id]` | `Batting[game_id]` | 1 → * | Single | |
| `Matches[game_id]` | `Bowling[game_id]` | 1 → * | Single | |
| `Matches[game_id]` | `Dismissals[game_id]` | 1 → * | Single | |
| `Players[player_id]` | `Batting[player_id]` | 1 → * | Single | Active |
| `Players[player_id]` | `Bowling[player_id]` | 1 → * | Single | Active |
| `Players[player_id]` | `Dismissals[batter_player_id]` | 1 → * | Single | Active |
| `Players[player_id]` | `Dismissals[fielder_player_id]` | 1 → * | Single | Inactive (use `USERELATIONSHIP` when counting catches) |

Ladder connects to Matches only informationally (via team_name / competition) — no active relationship because the composite key is unusual. Instead, the scraper enriches `matches.csv` with `opponent_position`, `our_position`, and `vs_top_team` directly.
