# PlayHQ Cricket Data Analytics

End-to-end analytics pipeline that turns publicly-available cricket scorecard data into an interactive Power BI performance dashboard for a local T20 club side (Southern Strikers, Adelaide SA).

This project combines reverse-engineered GraphQL data extraction, Python-based ETL, star-schema modelling, and DAX-driven business intelligence.

---

## What this project does

1. **Scrapes** every fixture, scorecard, and ladder standing for the club from PlayHQ's public GraphQL endpoints (no API key required, endpoints reverse-engineered from PlayHQ's own front-end bundle).
2. **Transforms** raw match data into a normalised, Power-BI-ready star schema (six CSVs: matches, batting_lines, bowling_lines, dismissals, players, ladder).
3. **Models & analyses** the data in Power BI with 70+ DAX measures across batting, bowling, fielding, and captaincy, including three-way contextual splits (Overall / In Wins / vs Top-Half Ladder Teams).
4. **Visualises** the season in a 4-page report covering season overview, batting stats, bowling stats, and match-winning impact analysis.

---

## Season insights surfaced by the dashboard

- **20 matches played** across PASA Multicultural T20 and SACA Autumn Super Cricket T20, Winter 2026.
- **45 % win rate** overall — 8 wins from 14 in PASA (finished 9th of 15), 1 win from 6 in SACA (9th of 9).
- **Avg 130 runs scored** per game, **avg 6.3 wickets taken** per game.
- **Top run-scorer**: A. Hameed (260 runs @ SR 135)
- **Top wicket-taker**: R. Kahlon (11 wickets)
- **Best bowling figures**: A. Jiffry (4/12)
- **Captaincy split**: T. Rayhan 64 % win rate (9 games), N. Kataria 33 % (3 games), A. Bansod 17 % (6 games).
- **Impact-in-wins leaders** vs overall leaders diverge, i.e. a batter averages 41.3 in winning games (vs 20.9 overall), showing who steps up when it matters.

The full 4-page PDF report lives in the 'Report' folder.

---

## Tech stack

| Layer | Tools |
| --- | --- |
| Data extraction | Python 3, `requests`, PlayHQ public GraphQL |
| Transformation & modelling | Pandas, custom flattening logic, CSV output |
| Data warehouse | Star schema (5 fact/dim tables + calendar) |
| Business intelligence | Microsoft Power BI Service |
| Analytics language | DAX (measures, calculated columns, calculation groups, SWITCH-based context) |
| Notebook / documentation | Jupyter |
| Version control | Git |

---

## Architecture

```
                         ┌──────────────────────────┐
                         │  PlayHQ Public GraphQL   │
                         │  ─ api.playhq.com        │
                         │  ─ spectator.playhq.com  │
                         └────────────┬─────────────┘
                                      │  x-phq-tenant header
                                      ▼
                         ┌──────────────────────────┐
                         │  playhq_scraper.py       │
                         │  ─ teamFixture query     │
                         │  ─ gameViewSpectator     │
                         │  ─ teamLadder query      │
                         │  ─ Custom flattener      │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │  data/*.csv              │
                         │  matches, batting_lines, │
                         │  bowling_lines,          │
                         │  dismissals, players,    │
                         │  ladder, captains        │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │  Power BI semantic model │
                         │  ─ Star schema           │
                         │  ─ 70+ DAX measures      │
                         │  ─ Context calc group    │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │  4-page interactive      │
                         │  report                  │
                         └──────────────────────────┘
```

---

## Skills demonstrated

**Python & data engineering**
- Reverse-engineering third-party GraphQL APIs by inspecting front-end JavaScript bundles
- Building resilient HTTP clients with realistic browser headers, pagination, and rate limiting
- Nested JSON → flat relational CSV transformation
- Idempotent ETL: manually-maintained overrides (`captains.csv`) survive every refresh
- Both script (`.py`) and notebook (`.ipynb`) delivery for automation vs. interactive exploration

**Data modelling**
- Star schema design with clear fact and dimension separation
- Composite keys, cardinality, and cross-filter direction planning
- Custom calendar (date table) with fiscal season logic
- Handling many-to-many workarounds (fielder → team via double LOOKUPVALUE)

**Advanced analytics in DAX**
- Filter context manipulation with `CALCULATE`, `CALCULATETABLE`, `SUMMARIZE`, `ADDCOLUMNS`
- Ranking and top-N logic (`TOPN`, `RANKX`, `CONCATENATEX`)
- Multi-context measure library — same KPI evaluated across Overall / Winning / High-Stakes contexts
- Composite sort keys for tie-breaking in leaderboards
- Percentile qualifications (min-innings, min-overs) baked into rate metrics
- Award-string measures (`"Player — value"`) for at-a-glance leaderboards

**Business intelligence & reporting**
- 4-page report design with hierarchy: overview → discipline detail → impact
- Card, matrix, clustered column, and line chart selection for the message being told
- Cross-visual interactivity (filters, drill-through, cross-highlighting)
- Report theming and consistent visual formatting

**Domain modelling**
- Cricket-specific KPIs: SR, economy, boundary %, best figures (M/W notation), 3wi/5wi hauls
- Contextual splits — performance in wins vs against top-of-ladder teams — surface who *drives* results vs who beats weaker opposition

**Soft & workflow skills**
- Requirements gathering & scope negotiation with stakeholders
- Iterative refinement based on feedback (11+ measure revisions)
- Debugging under uncertainty — ID namespace mismatches, tie-breaking, licensing limits, circular dependencies

---

## Project structure

```
southern-strikers-analytics/
├── README.md                        ← this file
├── LICENSE
├── requirements.txt
├── .gitignore
│
├── scraper/
│   ├── playhq_scraper.py            ← standalone CLI scraper
│   └── playhq_scraper.ipynb         ← interactive Jupyter version
│
├── data/                            ← output folder for CSVs (gitignored)
│   ├── matches.csv                  ← one row per fixture
│   ├── batting_lines.csv            ← one row per innings batted
│   ├── bowling_lines.csv            ← one row per innings bowled
│   ├── dismissals.csv               ← one row per wicket event
│   ├── players.csv                  ← player roster
│   ├── ladder.csv                   ← standings per competition
│   └── captains.csv                 ← manual captain-per-match log
│
├── report/
│   └── Southern-Strikers-Winter26-Report.pdf   ← final BI deliverable
│
└── docs/
    ├── data-model.md                ← star schema documentation
    ├── dax-measures.md              ← measure library reference
    └── setup-guide.md               ← Power BI setup walk-through
```

---

## Getting started

### Prerequisites

- Python 3.10+
- `pip` or Anaconda
- Power BI Desktop (Windows) or Power BI Service account (any OS)

### 1 — Clone and install

```bash
git clone https://github.com/<your-handle>/southern-strikers-analytics.git
cd southern-strikers-analytics
pip install -r requirements.txt
```

### 2 — Configure the target teams

Open `scraper/playhq_scraper.py` and edit the `TEAMS` list at the top:

```python
TEAMS = [
    {
        "label": "Your Competition Name",
        "team_id": "abc12345",           # last segment of the team page URL
        "url": "https://www.playhq.com/.../teams/your-team/abc12345",
    },
]
```

### 3 — Run the scraper

```bash
python scraper/playhq_scraper.py --out ./data
```

Takes ~30 seconds for a full season. Produces the six CSVs under `data/`.

Or open `scraper/playhq_scraper.ipynb` in Jupyter for a cell-by-cell walk-through.

### 4 — Load into Power BI

Power BI Desktop → **Get Data → Folder** → point at `./data`. Follow [`Docs/setup-guide.md`](Docs/setup-guide.md) for the model relationships and DAX measure library.

---

## Data model

The scraper produces a clean star schema:

```
                     ┌──────────────┐
                     │  Date        │
                     └──────┬───────┘
                            │
                     ┌──────▼───────┐
                     │  Matches     │◄─── Ladder (competition, team, position)
                     │  (fact)      │
                     └──┬───┬───┬───┘
                        │   │   │
              ┌─────────┘   │   └─────────┐
              ▼             ▼             ▼
       ┌──────────┐  ┌──────────┐  ┌──────────┐
       │ Batting  │  │ Bowling  │  │Dismissals│
       │ (fact)   │  │ (fact)   │  │ (fact)   │
       └────┬─────┘  └────┬─────┘  └────┬─────┘
            └─────────────┼─────────────┘
                          ▼
                   ┌──────────────┐
                   │  Players     │
                   │  (dim)       │
                   └──────────────┘
```

Full schema documentation in [`Docs/data-model.md`](Docs/data-model.md).

---

## Report preview

The final Power BI report has four pages:

| Page | Focus |
| --- | --- |
| **Overview** | Season KPI cards, win/loss by competition, run-rate & wickets by round, captain win %, season leaders matrix |
| **Batting Stats** | Full team batting leaderboard: runs, average, SR, boundaries, 50s/100s |
| **Bowling Stats** | Full team bowling leaderboard: wickets, economy, average, best figures, 3wi/5wi |
| **Impact Analysis** | Three-column comparison — Overall vs In Winning Games vs vs Top-Half Ladder Teams — for batting and bowling |

See [`Report/Southern-Strikers-Winter26-Report.pdf`](Report/Southern-Strikers-Winter26-Report.pdf) for the full export.

---

## Notes on PlayHQ terms of service

This scraper hits PlayHQ's public GraphQL endpoints (the same ones their own public website uses) with polite rate limiting and no auth-required data. It's used for **internal club analytics only**. For anything at scale, redistribution, or commercial use, please request formal API access through your association: [PlayHQ API docs](https://docs.playhq.com/tech/).

---

## Roadmap

- [ ] Ball-by-ball scraping (partnership/over-by-over analysis)
- [ ] Weather + toss context columns
- [ ] Automated weekly refresh via GitHub Actions
- [ ] Public Power BI embed
- [ ] Extend to multiple seasons + career-view measures
- [ ] Video-highlight linking per match

---

## License

MIT — see [`LICENSE`](LICENSE).

Use freely for non-commercial club analytics. Attribution appreciated.

---

## Acknowledgments

- **Southern Strikers CC** for being the guinea pig club and letting me test everything on live data.
- **PlayHQ** for building a clean public GraphQL layer that made this achievable without an approved API key.
- **The Power BI DAX community** for solving every edge case I hit.

---

**Contact**: [tashrif.rayhan@gmail.com](mailto:tashrif.rayhan@gmail.com) · [LinkedIn](https://www.linkedin.com/in/md-tashrif-ibn-rayhan/)
