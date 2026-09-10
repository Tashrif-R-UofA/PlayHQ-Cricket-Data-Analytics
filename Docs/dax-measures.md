# DAX measure library

A reference of every measure used in the Power BI report. All measures assume the team of interest is Southern Strikers — replace with your own club name if reusing.

## Table of contents

- [Match-level KPIs](#match-level-kpis)
- [Batting measures](#batting-measures)
- [Bowling measures](#bowling-measures)
- [Fielding measures](#fielding-measures)
- [Captaincy measures](#captaincy-measures)
- [Contextual variants (In Wins / vs Top Teams)](#contextual-variants-in-wins--vs-top-teams)
- [Award / leaderboard measures](#award--leaderboard-measures)
- [Helper measures](#helper-measures)

## Match-level KPIs

```dax
MatchesPlayed =
CALCULATE ( DISTINCTCOUNT ( Matches[game_id] ), Matches[status] = "FINAL" )

Wins   = CALCULATE ( DISTINCTCOUNT ( Matches[game_id] ), Matches[our_result] = "WIN" )
Losses = CALCULATE ( DISTINCTCOUNT ( Matches[game_id] ), Matches[our_result] = "LOSS" )
WinPct = DIVIDE ( [Wins] * 100, [MatchesPlayed] )

AvgRunsPerGame =
CALCULATE (
    AVERAGE ( Matches[OurScore] ),
    Matches[status] = "FINAL",
    NOT ISBLANK ( Matches[OurScore] )
)

AvgWicketsTakenPerGame =
CALCULATE (
    AVERAGE ( Matches[TheirWickets] ),
    Matches[status] = "FINAL",
    NOT ISBLANK ( Matches[TheirWickets] )
)

BattingRunRate =
DIVIDE (
    CALCULATE ( SUM ( Matches[OurScore] ),  Matches[status] = "FINAL" ),
    CALCULATE ( SUM ( Matches[OurOvers] ), Matches[status] = "FINAL" )
)

BowlingEconomyRate =
DIVIDE (
    CALCULATE ( SUM ( Bowling[runs_conceded] ), Bowling[team] = "Southern Strikers" ),
    CALCULATE ( SUM ( Bowling[overs] ),         Bowling[team] = "Southern Strikers" )
)
```

## Batting measures

```dax
Bat_Runs        = CALCULATE ( SUM ( Batting[runs] ),  Batting[team] = "Southern Strikers" )
Bat_Innings     = CALCULATE ( COUNTROWS ( Batting ),  Batting[team] = "Southern Strikers" )
Bat_Balls       = CALCULATE ( SUM ( Batting[balls] ), Batting[team] = "Southern Strikers" )
Bat_Fours       = CALCULATE ( SUM ( Batting[fours] ), Batting[team] = "Southern Strikers" )
Bat_Sixes       = CALCULATE ( SUM ( Batting[sixes] ), Batting[team] = "Southern Strikers" )
Bat_Outs        = CALCULATE ( COUNTROWS ( Batting ),  Batting[team] = "Southern Strikers", Batting[status] = "OUT" )
Bat_HS          = CALCULATE ( MAX ( Batting[runs] ),  Batting[team] = "Southern Strikers" )
Bat_50s         = CALCULATE ( COUNTROWS ( Batting ),  Batting[team] = "Southern Strikers", Batting[runs] >= 50, Batting[runs] < 100 )
Bat_100s        = CALCULATE ( COUNTROWS ( Batting ),  Batting[team] = "Southern Strikers", Batting[runs] >= 100 )
Bat_Avg         = DIVIDE ( [Bat_Runs], [Bat_Outs] )
Bat_SR          = IF ( [Bat_Innings] >= 3, DIVIDE ( [Bat_Runs] * 100, [Bat_Balls] ) )
Bat_BoundaryPct = DIVIDE ( ( [Bat_Fours] + [Bat_Sixes] ) * 100, [Bat_Balls] )
```

## Bowling measures

```dax
Bowl_Wkts     = CALCULATE ( SUM ( Bowling[wickets] ),       Bowling[team] = "Southern Strikers" )
Bowl_Overs    = CALCULATE ( SUM ( Bowling[overs] ),         Bowling[team] = "Southern Strikers" )
Bowl_Runs     = CALCULATE ( SUM ( Bowling[runs_conceded] ), Bowling[team] = "Southern Strikers" )
Bowl_Innings  = CALCULATE ( COUNTROWS ( Bowling ),          Bowling[team] = "Southern Strikers" )
Bowl_BestWkts = CALCULATE ( MAX ( Bowling[wickets] ),       Bowling[team] = "Southern Strikers" )
Bowl_3wi      = CALCULATE ( COUNTROWS ( Bowling ),          Bowling[team] = "Southern Strikers", Bowling[wickets] >= 3 )
Bowl_5wi      = CALCULATE ( COUNTROWS ( Bowling ),          Bowling[team] = "Southern Strikers", Bowling[wickets] >= 5 )
Bowl_Avg      = DIVIDE ( [Bowl_Runs], [Bowl_Wkts] )
Bowl_Econ     = IF ( [Bowl_Overs] >= 5, DIVIDE ( [Bowl_Runs], [Bowl_Overs] ) )
Bowl_SR       = DIVIDE ( [Bowl_Overs] * 6, [Bowl_Wkts] )

Bowl_BestFig =
VAR MaxW = [Bowl_BestWkts]
VAR MinRunsAtMax =
    CALCULATE (
        MIN ( Bowling[runs_conceded] ),
        Bowling[team] = "Southern Strikers",
        Bowling[wickets] = MaxW
    )
RETURN
    IF (
        ISBLANK ( MaxW ) || MaxW = 0,
        BLANK (),
        MaxW & "/" & MinRunsAtMax
    )
```

## Fielding measures

```dax
fielder_team_final =                          -- Calculated column on Dismissals
VAR pid = Dismissals[fielder_player_id]
VAR fromBat  = CALCULATE ( MAX ( Batting[team] ),  Batting[player_id] = pid )
VAR fromBowl = CALCULATE ( MAX ( Bowling[team] ), Bowling[player_id] = pid )
RETURN COALESCE ( fromBat, fromBowl )

Field_Catches =
CALCULATE (
    COUNTROWS ( Dismissals ),
    Dismissals[dismissal_type] = "CAUGHT",
    Dismissals[fielder_team_final] = "Southern Strikers"
)
```

## Captaincy measures

```dax
DecidedMatches =
CALCULATE (
    DISTINCTCOUNT ( Matches[game_id] ),
    Matches[status] = "FINAL",
    Matches[our_result] IN { "WIN", "LOSS" }
)

CaptainWins =
CALCULATE (
    DISTINCTCOUNT ( Matches[game_id] ),
    Matches[status] = "FINAL",
    Matches[our_result] = "WIN"
)

CaptainWinPct = DIVIDE ( [CaptainWins] * 100, [DecidedMatches] )
```

Used with `Matches[captain]` on rows of a Matrix.

## Contextual variants (In Wins / vs Top Teams)

Every base measure gets two variants that wrap it with a filter on Matches:

```dax
Bat_Runs_Wins  = CALCULATE ( [Bat_Runs],  Matches[our_result] = "WIN" )
Bat_Runs_VsTop = CALCULATE ( [Bat_Runs],  Matches[vs_top_team] = TRUE() )

Bowl_Wkts_Wins  = CALCULATE ( [Bowl_Wkts],  Matches[our_result] = "WIN" )
Bowl_Wkts_VsTop = CALCULATE ( [Bowl_Wkts],  Matches[vs_top_team] = TRUE() )
```

...and so on for every base measure. The filter propagates via `Matches[game_id]` → the underlying Batting/Bowling fact table.

**Sort keys for tie-breaking** — bowling ties on wickets, breaks on lower average:

```dax
Bowl_SortKey       = [Bowl_Wkts]       * 10000 - [Bowl_Avg]
Bowl_SortKey_Wins  = [Bowl_Wkts_Wins]  * 10000 - [Bowl_Avg_Wins]
Bowl_SortKey_VsTop = [Bowl_Wkts_VsTop] * 10000 - [Bowl_Avg_VsTop]
```

Batting: ties on runs, breaks on higher SR:

```dax
Bat_SortKey       = [Bat_Runs]       * 10000 + [Bat_SR]
Bat_SortKey_Wins  = [Bat_Runs_Wins]  * 10000 + [Bat_SR_Wins]
Bat_SortKey_VsTop = [Bat_Runs_VsTop] * 10000 + [Bat_SR_VsTop]
```

## Award / leaderboard measures

Return a formatted string like `"Player Name — value"` for the season leader in each KPI:

```dax
Top_Run_Getter =
VAR t =
    CALCULATETABLE (
        ADDCOLUMNS (
            VALUES ( Batting[player_name] ),
            "V", CALCULATE ( SUM ( Batting[runs] ) )
        ),
        Batting[team] = "Southern Strikers"
    )
VAR top1 = TOPN ( 1, t, [V], DESC )
RETURN CONCATENATEX ( top1, [player_name] & " — " & FORMAT ( [V], "0" ) & " runs", ", " )

Top_Wicket_Taker =
VAR t =
    CALCULATETABLE (
        ADDCOLUMNS (
            VALUES ( Bowling[player_name] ),
            "V", CALCULATE ( SUM ( Bowling[wickets] ) )
        ),
        Bowling[team] = "Southern Strikers"
    )
VAR top1 = TOPN ( 1, t, [V], DESC )
RETURN CONCATENATEX ( top1, [player_name] & " — " & FORMAT ( [V], "0" ) & " wkts", ", " )

Best_Individual_Score =
VAR t =
    CALCULATETABLE (
        SUMMARIZE ( Batting, Batting[player_name], Batting[runs], Batting[balls] ),
        Batting[team] = "Southern Strikers"
    )
VAR top1 = TOPN ( 1, t, [runs], DESC )
RETURN CONCATENATEX ( top1, [player_name] & " — " & FORMAT ( [runs], "0" ) & " (" & FORMAT ( [balls], "0" ) & ")", ", " )

Best_Bowling_Figures =
VAR t =
    CALCULATETABLE (
        SUMMARIZE ( Bowling, Bowling[player_name], Bowling[wickets], Bowling[runs_conceded] ),
        Bowling[team] = "Southern Strikers"
    )
VAR top1 = TOPN ( 1, t, [wickets], DESC, [runs_conceded], ASC )
RETURN CONCATENATEX ( top1, [player_name] & " — " & FORMAT ( [wickets], "0" ) & "/" & FORMAT ( [runs_conceded], "0" ), ", " )

Best_Strike_Rate =
VAR t =
    CALCULATETABLE (
        FILTER (
            ADDCOLUMNS (
                VALUES ( Batting[player_name] ),
                "Runs",  CALCULATE ( SUM ( Batting[runs] ) ),
                "Balls", CALCULATE ( SUM ( Batting[balls] ) ),
                "Inns",  CALCULATE ( COUNTROWS ( Batting ) )
            ),
            [Inns] >= 3 && [Balls] > 0
        ),
        Batting[team] = "Southern Strikers"
    )
VAR withSR = ADDCOLUMNS ( t, "SR", DIVIDE ( [Runs] * 100, [Balls] ) )
VAR top1 = TOPN ( 1, withSR, [SR], DESC )
RETURN CONCATENATEX ( top1, [player_name] & " — SR " & FORMAT ( [SR], "0.0" ), ", " )

Best_Economy =
VAR t =
    CALCULATETABLE (
        FILTER (
            ADDCOLUMNS (
                VALUES ( Bowling[player_name] ),
                "Runs",  CALCULATE ( SUM ( Bowling[runs_conceded] ) ),
                "Overs", CALCULATE ( SUM ( Bowling[overs] ) )
            ),
            [Overs] >= 5
        ),
        Bowling[team] = "Southern Strikers"
    )
VAR withEcon = ADDCOLUMNS ( t, "Econ", DIVIDE ( [Runs], [Overs] ) )
VAR top1 = TOPN ( 1, withEcon, [Econ], ASC )
RETURN CONCATENATEX ( top1, [player_name] & " — Econ " & FORMAT ( [Econ], "0.00" ), ", " )
```

Award_Value drives the "Season Leaders" matrix by SWITCHing on a helper `Awards[Matrix]` column:

```dax
Award_Value =
SWITCH (
    SELECTEDVALUE ( Awards[Matrix] ),
    "Most Runs",                 [Top_Run_Getter],
    "Most Wickets",              [Top_Wicket_Taker],
    "Highest Individual Score",  [Best_Individual_Score],
    "Best Bowling Figure",       [Best_Bowling_Figures],
    "Highest Strike Rate",       [Best_Strike_Rate],
    "Best Economy",              [Best_Economy],
    "Most Fours",                [Most_Fours],
    "Most Sixes",                [Most_Sixes],
    "Most Catches",              [Most_Catches]
)
```

## Helper measures

Calculated columns on the Matches table:

```dax
Opponent     = SWITCH ( Matches[our_side], "HOME", Matches[away_team_name], "AWAY", Matches[home_team_name] )
OurScore     = SWITCH ( Matches[our_side], "HOME", Matches[home_score],     "AWAY", Matches[away_score] )
TheirScore   = SWITCH ( Matches[our_side], "HOME", Matches[away_score],     "AWAY", Matches[home_score] )
OurOvers     = SWITCH ( Matches[our_side], "HOME", Matches[home_overs],     "AWAY", Matches[away_overs] )
TheirOvers   = SWITCH ( Matches[our_side], "HOME", Matches[away_overs],     "AWAY", Matches[home_overs] )
OurWickets   = SWITCH ( Matches[our_side], "HOME", Matches[home_wickets],   "AWAY", Matches[away_wickets] )
TheirWickets = SWITCH ( Matches[our_side], "HOME", Matches[away_wickets],   "AWAY", Matches[home_wickets] )
RoundNum     = IFERROR ( VALUE ( SUBSTITUTE ( Matches[round_name], "Round ", "" ) ), BLANK() )
```
