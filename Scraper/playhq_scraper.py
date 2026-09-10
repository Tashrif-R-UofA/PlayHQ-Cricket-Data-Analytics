#!/usr/bin/env python3
"""
PlayHQ Scraper for Southern Strikers.

Pulls the fixture + full scorecards for the configured teams from PlayHQ's
public GraphQL endpoints (no API key required) and writes flat CSVs suitable
for loading into Power BI.

Usage:
    pip install requests
    python playhq_scraper.py                       # writes to ./southern-strikers-data
    python playhq_scraper.py --out C:/path/to/dir  # custom output folder

Add or replace teams in the TEAMS list below to cover future seasons.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

TEAMS: list[dict] = [
    {
        "label": "PASA Multicultural T20 Winter 2026",
        "team_id": "33d20e37",
        "url": "https://www.playhq.com/cricket-australia/org/pashtun-association-of-sa/pasa-multicultural-cricket-wintert20-winter-2026/teams/southern-strikers/33d20e37",
    },
    {
        "label": "SACA Autumn Super Cricket T20 Winter 2026",
        "team_id": "57c57ec5",
        "url": "https://www.playhq.com/cricket-australia/org/saca-super-cricket/saca-autumn-super-cricket-t20-winter-2026/teams/southern-strikers/57c57ec5",
    },
]

DISCOVER_ENDPOINT = "https://api.playhq.com/graphql"
SPECTATOR_ENDPOINT = "https://spectator.playhq.com/graphql"
DISCOVER_TENANT = "cricket-australia"
SPECTATOR_TENANT = "ca"

# ---------------------------------------------------------------------------
# GraphQL queries (extracted from PlayHQ's own front-end bundles)
# ---------------------------------------------------------------------------

TEAM_FIXTURE_QUERY = """
query teamFixture($teamID: ID!) {
  discoverTeam(teamID: $teamID) {
    id name
    season { id name }
    grade { id name }
    organisation { id name }
  }
  discoverTeamFixture(teamID: $teamID) {
    id name
    grade {
      id name type
      season { id name competition { id name organisation { id name } type } }
    }
    fixture {
      games {
        id
        away {
          ... on ProvisionalTeam { name __typename }
          ... on DiscoverTeam { id name __typename }
        }
        home {
          ... on ProvisionalTeam { name __typename }
          ... on DiscoverTeam { id name __typename }
        }
        result {
          winner { name value }
          outcome { name value }
          home {
            statistics { count type { value } }
            periods { period { value } type closureStatus statistics { count type { value } } }
          }
          away {
            statistics { count type { value } }
            periods { period { value } type closureStatus statistics { count type { value } } }
          }
        }
        status { name value }
        date
        allocation {
          time
          court { name venue { name suburb } }
        }
        gameType { name value }
      }
    }
  }
}
"""

TEAM_LADDER_QUERY = """
query teamLadder($teamID: ID!) {
  discoverTeam(teamID: $teamID) {
    id name
    grade {
      id name ladderType
      ladder(filter: {teamID: $teamID}) {
        pool { id name }
        standings {
          team { id name }
          played won lost drawn byes
          pointsFor pointsAgainst pointsDifference percentage netRunRate
          competitionPoints noResults ties
          runsFor oversFaced wicketsLost
          runsAgainst oversBowled wicketsTaken
          forfeits
        }
        gameTypeValue
      }
    }
  }
}
"""

GAME_VIEW_QUERY = """
query gameViewSpectator($id: ID!) {
  game(id: $id) {
    id status updatedAt lastEventRecordedAt
    statistics {
      home {
        coinTossWinningResult { preference }
        statisticsV2 { type { value } count }
        players {
          id profileID name playerNumber lineupOrder permitType
          periodStatistics {
            period { value } side type
            statistics { type { value } count }
            status displayOrder
          }
          statistics { type { value } count }
        }
      }
      away {
        coinTossWinningResult { preference }
        statisticsV2 { type { value } count }
        players {
          id profileID name playerNumber lineupOrder permitType
          periodStatistics {
            period { value } side type
            statistics { type { value } count }
            status displayOrder
          }
          statistics { type { value } count }
        }
      }
      shared {
        period { value }
        players { playerID teamID role }
        dismissalType side status type
      }
    }
  }
}
"""

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


def post_graphql(
    endpoint: str,
    tenant_header_key: str,
    tenant_header_value: str,
    operation: str,
    query: str,
    variables: dict,
) -> dict:
    resp = requests.post(
        endpoint,
        headers={
            "content-type": "application/json",
            tenant_header_key: tenant_header_value,
            "accept": "*/*",
            "user-agent": BROWSER_UA,
            "origin": "https://www.playhq.com",
            "referer": "https://www.playhq.com/",
        },
        data=json.dumps({"operationName": operation, "variables": variables, "query": query}),
        timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("errors"):
        raise RuntimeError(f"GraphQL errors from {operation}: {payload['errors']}")
    return payload["data"]


def fetch_team_fixture(team_id: str) -> dict:
    return post_graphql(
        DISCOVER_ENDPOINT, "tenant", DISCOVER_TENANT,
        "teamFixture", TEAM_FIXTURE_QUERY, {"teamID": team_id},
    )


def fetch_game_view(game_id: str) -> dict:
    return post_graphql(
        SPECTATOR_ENDPOINT, "x-phq-tenant", SPECTATOR_TENANT,
        "gameViewSpectator", GAME_VIEW_QUERY, {"id": game_id},
    )


def fetch_team_ladder(team_id: str) -> dict:
    return post_graphql(
        DISCOVER_ENDPOINT, "tenant", DISCOVER_TENANT,
        "teamLadder", TEAM_LADDER_QUERY, {"teamID": team_id},
    )


def extract_ladder(team_meta: dict, ladder_data: dict) -> list[dict]:
    """Flatten ladder standings into one row per team, ordered by position."""
    rows: list[dict] = []
    team = ladder_data.get("discoverTeam") or {}
    grade = team.get("grade") or {}
    for ladder in grade.get("ladder") or []:
        pool = ladder.get("pool") or {}
        for i, s in enumerate(ladder.get("standings") or [], start=1):
            tm = s.get("team") or {}
            rows.append({
                "competition": team_meta["label"],
                "grade_name": grade.get("name"),
                "pool": pool.get("name"),
                "position": i,
                "team_id": tm.get("id"),
                "team_name": tm.get("name"),
                "played": s.get("played"),
                "won": s.get("won"),
                "lost": s.get("lost"),
                "drawn": s.get("drawn"),
                "ties": s.get("ties"),
                "no_results": s.get("noResults"),
                "byes": s.get("byes"),
                "forfeits": s.get("forfeits"),
                "competition_points": s.get("competitionPoints"),
                "points_for": s.get("pointsFor"),
                "points_against": s.get("pointsAgainst"),
                "points_difference": s.get("pointsDifference"),
                "percentage": s.get("percentage"),
                "net_run_rate": s.get("netRunRate"),
                "runs_for": s.get("runsFor"),
                "overs_faced": s.get("oversFaced"),
                "wickets_lost": s.get("wicketsLost"),
                "runs_against": s.get("runsAgainst"),
                "overs_bowled": s.get("oversBowled"),
                "wickets_taken": s.get("wicketsTaken"),
            })
    return rows

# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def stat_get(stats: list[dict] | None, key: str) -> Any:
    for s in stats or []:
        t = (s or {}).get("type") or {}
        if t.get("value") == key:
            return s.get("count")
    return None


def score_from_statistics(stats: list[dict] | None) -> dict:
    """Extract totals from the flat statistics array (rarely populated on PlayHQ)."""
    return {
        "total_score": stat_get(stats, "TOTAL_SCORE"),
        "total_wickets": stat_get(stats, "TOTAL_OUTS"),
        "total_overs": stat_get(stats, "TOTAL_OVERS"),
    }


def score_from_periods(periods: list[dict] | None) -> dict:
    """Sum runs and wickets across every innings; total overs as sum of innings overs."""
    total_score = None
    total_wickets = None
    total_overs = None
    for p in periods or []:
        p_stats = p.get("statistics") or []
        for key, target in (("TOTAL_SCORE", "total_score"),
                            ("TOTAL_OUTS", "total_wickets"),
                            ("TOTAL_OVERS", "total_overs")):
            v = stat_get(p_stats, key)
            if v is None:
                continue
            current = {"total_score": total_score, "total_wickets": total_wickets, "total_overs": total_overs}[target]
            new = (current or 0) + v
            if target == "total_score":
                total_score = new
            elif target == "total_wickets":
                total_wickets = new
            else:
                total_overs = new
    return {"total_score": total_score, "total_wickets": total_wickets, "total_overs": total_overs}


def extract_matches(team_meta: dict, fixture_data: dict) -> list[dict]:
    rows: list[dict] = []
    team = fixture_data["discoverTeam"]
    for round_ in fixture_data["discoverTeamFixture"]:
        grade = round_.get("grade") or {}
        for game in round_["fixture"]["games"]:
            result = game.get("result") or {}
            home_periods = ((result.get("home") or {}).get("periods")) or []
            away_periods = ((result.get("away") or {}).get("periods")) or []
            home_score = score_from_periods(home_periods)
            away_score = score_from_periods(away_periods)
            allocation = game.get("allocation") or {}
            court = allocation.get("court") or {}
            venue = court.get("venue") or {}
            home = game.get("home") or {}
            away = game.get("away") or {}
            winner = result.get("winner") or {}
            outcome = result.get("outcome") or {}

            # W/L for our team (Southern Strikers)
            our_team_id = team["id"]
            our_side = "HOME" if home.get("id") == our_team_id else ("AWAY" if away.get("id") == our_team_id else None)
            if winner.get("value") is None:
                our_result = None
            elif our_side is None:
                our_result = None
            elif winner.get("value") == our_side:
                our_result = "WIN"
            elif winner.get("value") in ("HOME", "AWAY"):
                our_result = "LOSS"
            else:
                our_result = winner.get("value")  # DRAW, TIE, NO_RESULT etc.

            rows.append({
                "competition": team_meta["label"],
                "our_team_id": our_team_id,
                "our_team_name": team["name"],
                "our_side": our_side,
                "our_result": our_result,
                "grade_name": grade.get("name"),
                "grade_type": grade.get("type"),
                "round_name": round_.get("name"),
                "game_id": game["id"],
                "date": game.get("date"),
                "time": allocation.get("time"),
                "venue_name": venue.get("name"),
                "venue_suburb": venue.get("suburb"),
                "court_name": court.get("name"),
                "game_type": (game.get("gameType") or {}).get("name"),
                "status": (game.get("status") or {}).get("value"),
                "home_team_id": home.get("id"),
                "home_team_name": home.get("name"),
                "away_team_id": away.get("id"),
                "away_team_name": away.get("name"),
                "home_score": home_score["total_score"],
                "home_wickets": home_score["total_wickets"],
                "home_overs": home_score["total_overs"],
                "away_score": away_score["total_score"],
                "away_wickets": away_score["total_wickets"],
                "away_overs": away_score["total_overs"],
                "winner_side": winner.get("value"),
                "outcome": outcome.get("name"),
            })
    return rows


def extract_player_lines(
    game_id: str,
    competition: str,
    date: str,
    round_name: str,
    team_side: str,
    team_name: str,
    players: list[dict],
) -> tuple[list[dict], list[dict]]:
    """
    For each player on the given team, split their periodStatistics into
    batting (side == team_side) and bowling (side != team_side) rows.
    """
    batting: list[dict] = []
    bowling: list[dict] = []

    for p in players:
        for period in p.get("periodStatistics") or []:
            stats = period.get("statistics") or []
            side = period.get("side")
            innings_num = (period.get("period") or {}).get("value")

            if side == team_side:
                runs = stat_get(stats, "TOTAL_RUNS")
                balls = stat_get(stats, "BALLS_FACED")
                fours = stat_get(stats, "FOURS")
                sixes = stat_get(stats, "SIXES")
                sr = stat_get(stats, "STRIKE_RATE")
                current_runs = stat_get(stats, "CURRENT_RUNS")
                current_balls = stat_get(stats, "CURRENT_BALLS_FACED")
                if any(v is not None for v in (runs, balls, fours, sixes, current_runs)):
                    batting.append({
                        "game_id": game_id,
                        "competition": competition,
                        "date": date,
                        "round_name": round_name,
                        "team": team_name,
                        "innings": innings_num,
                        "player_id": p["id"],
                        "profile_id": p.get("profileID"),
                        "player_name": p["name"],
                        "lineup_order": p.get("lineupOrder"),
                        "batting_position": period.get("displayOrder"),
                        "status": period.get("status"),  # OUT, NOT_OUT, DID_NOT_BAT, RETIRED etc.
                        "runs": runs if runs is not None else current_runs,
                        "balls": balls if balls is not None else current_balls,
                        "fours": fours,
                        "sixes": sixes,
                        "strike_rate": sr,
                    })
            else:
                overs = stat_get(stats, "OVERS")
                runs_conc = stat_get(stats, "RUNS")
                wickets = stat_get(stats, "WICKETS")
                economy = stat_get(stats, "ECONOMY")
                wides = stat_get(stats, "WIDES")
                no_balls = stat_get(stats, "NO_BALLS")
                maidens = stat_get(stats, "MAIDENS")
                if any(v is not None for v in (overs, runs_conc, wickets)):
                    bowling.append({
                        "game_id": game_id,
                        "competition": competition,
                        "date": date,
                        "round_name": round_name,
                        "team": team_name,
                        "innings": innings_num,
                        "player_id": p["id"],
                        "profile_id": p.get("profileID"),
                        "player_name": p["name"],
                        "overs": overs,
                        "maidens": maidens,
                        "runs_conceded": runs_conc,
                        "wickets": wickets,
                        "economy": economy,
                        "wides": wides,
                        "no_balls": no_balls,
                    })

    return batting, bowling


def extract_dismissals(
    game_id: str,
    competition: str,
    date: str,
    round_name: str,
    shared: list[dict] | None,
) -> list[dict]:
    rows: list[dict] = []
    for s in shared or []:
        players = s.get("players") or []
        batter = next((p for p in players if p.get("role") == "BATTING"), None)
        bowler = next((p for p in players if p.get("role") == "BOWLING"), None)
        fielder = next((p for p in players if p.get("role") == "FIELDING"), None)
        if not batter:
            continue
        rows.append({
            "game_id": game_id,
            "competition": competition,
            "date": date,
            "round_name": round_name,
            "innings": (s.get("period") or {}).get("value"),
            "batter_player_id": batter.get("playerID"),
            "batter_team_id": batter.get("teamID"),
            "dismissal_type": s.get("dismissalType"),
            "bowler_player_id": (bowler or {}).get("playerID"),
            "fielder_player_id": (fielder or {}).get("playerID"),
        })
    return rows

# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------

def write_csv(path: Path, rows: list[dict], preferred_order: list[str] | None = None) -> None:
    if not rows:
        # Still write an empty file with headers so Power BI schemas are stable
        if preferred_order:
            with path.open("w", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=preferred_order).writeheader()
            print(f"  wrote    0 rows -> {path}")
        return

    if preferred_order:
        fieldnames = list(preferred_order)
        for r in rows:
            for k in r.keys():
                if k not in fieldnames:
                    fieldnames.append(k)
    else:
        fieldnames = []
        for r in rows:
            for k in r.keys():
                if k not in fieldnames:
                    fieldnames.append(k)

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)
    print(f"  wrote {len(rows):>4d} rows -> {path}")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Scrape Southern Strikers scorecards from PlayHQ into CSVs.")
    ap.add_argument("--out", default="./southern-strikers-data", help="Output folder for CSVs.")
    ap.add_argument("--sleep", type=float, default=0.4, help="Seconds to pause between game requests (default 0.4).")
    ap.add_argument("--only-team", help="Optional: process just one team by team_id.", default=None)
    args = ap.parse_args()

    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    all_matches: list[dict] = []
    all_batting: list[dict] = []
    all_bowling: list[dict] = []
    all_dismissals: list[dict] = []
    all_ladder: list[dict] = []
    roster: dict[str, dict] = {}

    for team_meta in TEAMS:
        if args.only_team and team_meta["team_id"] != args.only_team:
            continue

        print(f"\n=== {team_meta['label']} ===")
        try:
            fx = fetch_team_fixture(team_meta["team_id"])
        except Exception as e:
            print(f"  ! failed to fetch fixture for {team_meta['team_id']}: {e}", file=sys.stderr)
            continue

        matches = extract_matches(team_meta, fx)

        # Fetch ladder for the same team/season and enrich matches with
        # opponent position + a "vs teams above us" flag.
        try:
            ladder_data = fetch_team_ladder(team_meta["team_id"])
            ladder_rows = extract_ladder(team_meta, ladder_data)
            all_ladder.extend(ladder_rows)
            position_by_team = {r["team_name"]: r["position"] for r in ladder_rows}
            our_team_name = (ladder_data.get("discoverTeam") or {}).get("name")
            our_position = position_by_team.get(our_team_name)
            for m in matches:
                opp_name = m["home_team_name"] if m["our_side"] == "AWAY" else m["away_team_name"]
                opp_pos = position_by_team.get(opp_name)
                m["our_position"] = our_position
                m["opponent_position"] = opp_pos
                m["vs_top_team"] = (
                    opp_pos is not None and our_position is not None and opp_pos < our_position
                )
        except Exception as e:
            print(f"  ! failed to fetch ladder for {team_meta['team_id']}: {e}", file=sys.stderr)
            for m in matches:
                m["our_position"] = None
                m["opponent_position"] = None
                m["vs_top_team"] = None

        all_matches.extend(matches)
        played = [m for m in matches if m["status"] == "FINAL"]
        print(f"  {len(matches)} scheduled games total, {len(played)} FINAL")

        for m in matches:
            if m["status"] != "FINAL":
                continue
            time.sleep(args.sleep)
            try:
                gv = fetch_game_view(m["game_id"])
            except Exception as e:
                print(f"  ! failed to fetch game {m['game_id']}: {e}", file=sys.stderr)
                continue

            game = gv["game"]
            stats = game["statistics"]

            for side_key, side_val, team_name in [
                ("home", "HOME", m["home_team_name"]),
                ("away", "AWAY", m["away_team_name"]),
            ]:
                players = stats[side_key].get("players") or []
                for p in players:
                    pid = p["id"]
                    if pid not in roster:
                        roster[pid] = {
                            "player_id": pid,
                            "profile_id": p.get("profileID"),
                            "player_name": p.get("name"),
                            "teams": set(),
                        }
                    if team_name:
                        roster[pid]["teams"].add(team_name)

                bat, bowl = extract_player_lines(
                    m["game_id"], m["competition"], m["date"], m["round_name"],
                    side_val, team_name, players,
                )
                all_batting.extend(bat)
                all_bowling.extend(bowl)

            all_dismissals.extend(extract_dismissals(
                m["game_id"], m["competition"], m["date"], m["round_name"],
                stats.get("shared"),
            ))

            print(f"  processed {m['game_id']} ({m['round_name']}: {m['home_team_name']} v {m['away_team_name']})")

    roster_rows = [
        {
            "player_id": p["player_id"],
            "profile_id": p["profile_id"],
            "player_name": p["player_name"],
            "teams": " | ".join(sorted(t for t in p["teams"] if t)),
        }
        for p in roster.values()
    ]

    print("\n=== Writing CSVs ===")
    # Merge captain info from a hand-maintained captains.csv if present.
    # Expected columns: game_id, captain_player_id, captain_player_name
    captains_path = out_dir / "captains.csv"
    if captains_path.exists():
        with captains_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            captain_by_game = {row["game_id"]: row for row in reader if row.get("game_id")}
        for m in all_matches:
            row = captain_by_game.get(m["game_id"])
            m["captain_player_id"] = row.get("captain_player_id") if row else None
            m["captain"] = row.get("captain_player_name") if row else None
        print(f"  merged captain info from {captains_path} ({len(captain_by_game)} rows)")
    else:
        # Ensure columns exist even without a captains file
        for m in all_matches:
            m.setdefault("captain_player_id", None)
            m.setdefault("captain", None)

    write_csv(out_dir / "matches.csv", all_matches)

    # Seed captains.csv with all played game_ids so the user has a template to fill in
    if not captains_path.exists():
        with captains_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["game_id", "captain_player_id", "captain_player_name"])
            w.writeheader()
            for m in all_matches:
                if m["status"] == "FINAL":
                    w.writerow({"game_id": m["game_id"], "captain_player_id": "", "captain_player_name": ""})
        print(f"  seeded template {captains_path} — fill it in and rerun to have captain info in matches.csv")

    write_csv(out_dir / "batting_lines.csv", all_batting)
    write_csv(out_dir / "bowling_lines.csv", all_bowling)
    write_csv(out_dir / "dismissals.csv", all_dismissals)
    write_csv(out_dir / "players.csv", roster_rows)
    write_csv(out_dir / "ladder.csv", all_ladder)

    print(f"\nDone. CSVs saved to {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
