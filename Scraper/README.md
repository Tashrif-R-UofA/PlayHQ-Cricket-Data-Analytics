# Scraper

Two flavours of the same scraper — pick whichever suits your workflow.

## `playhq_scraper.py`

Command-line Python script. Runs top to bottom in one command.

```bash
python playhq_scraper.py --out ../data
```

Options:
- `--out PATH` — where to write CSVs (default: `./southern-strikers-data`)
- `--sleep SECONDS` — pause between game requests (default: 0.4). Keep this in — polite rate limiting.
- `--only-team TEAMID` — process a single team only, for testing

Prints progress row by row. Finishes with a summary of CSVs written.

## `playhq_scraper.ipynb`

Same logic as `.py` but broken into 22 cells you run interactively (Shift+Enter). Between steps you get pandas DataFrames to eyeball the data. Best for exploration or debugging.

Open in Jupyter:

```bash
jupyter notebook playhq_scraper.ipynb
```

## What both do

1. Query `teamFixture` on `api.playhq.com/graphql` to get every game ID for the configured teams.
2. Query `teamLadder` for standings.
3. Query `gameViewSpectator` on `spectator.playhq.com/graphql` for each played game's full scorecard.
4. Flatten nested JSON into six CSVs: `matches`, `batting_lines`, `bowling_lines`, `dismissals`, `players`, `ladder`.
5. Enrich `matches.csv` with:
   - `our_position` / `opponent_position` from the ladder
   - `vs_top_team` boolean
   - Captain info merged from a manually-maintained `captains.csv` (auto-seeded on first run)

## Configuration

Edit the `TEAMS` list near the top of either file:

```python
TEAMS = [
    {
        "label": "Competition display name",
        "team_id": "abc12345",             # last URL segment
        "url":     "https://www.playhq.com/.../teams/your-team/abc12345",
    },
]
```

`team_id` comes from the last URL segment of the team page on PlayHQ. Everything else is auto-discovered from the API.

## GraphQL endpoints used

| Endpoint | Header | Query |
| --- | --- | --- |
| `api.playhq.com/graphql` | `tenant: cricket-australia` | `teamFixture`, `teamLadder` |
| `spectator.playhq.com/graphql` | `x-phq-tenant: ca` | `gameViewSpectator` |

The query bodies were extracted by inspecting PlayHQ's own front-end JavaScript bundles (specifically `Innings.utils.*.js`) — they're the same queries their public website makes. No auth is required.

## HTTP headers

Both scripts send browser-like headers to avoid being blocked:

- `User-Agent` — real Chrome UA string
- `Origin: https://www.playhq.com`
- `Referer: https://www.playhq.com/`

Without these, PlayHQ returns 403 for bare `python-requests/*`.

## Rate limiting

Default 0.4 s between game requests. That's ~2.5 requests per second — well below anything that would look automated to PlayHQ. Do not turn this off.

## Handling failures

Some games can't be scored electronically (forfeits, walkovers, cancelled matches). The scraper logs these as `FAILED` and moves on — they still appear in `matches.csv` (from the fixture query) with `our_result` set correctly, just without scorecard detail.
