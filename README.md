# itpr-ncaa-database-v0

V0 slice of an NCAA men’s basketball data stack focused on the **Sun Belt Conference, 2024–25 season**.

This repo builds a small but realistic pipeline:

> Sports-Reference HTML → cleaned per-game CSVs → SQLite warehouse → stats + similarity + enriched player profiles

It’s meant as a scrappy, solo-founder friendly foundation for future work (portal scouting, similarity search, coach-facing reports, etc.).

---

## Current Scope (V0)

* **Conference:** Sun Belt (men’s basketball)
* **Season:** 2024–25 (Sports-Reference’s `2025` season pages)
* **Data source:**

  * `https://www.sports-reference.com/cbb/` (scraped HTML pages)
* **Storage:**

  * Local SQLite DB at `ncaa-analytics/db/ncaa_dev.db`

What we have right now:

1. **Raw HTML snapshots** of each Sun Belt team’s 2024–25 page.
2. **Per-game player stats** (per-team CSVs + one combined CSV).
3. **SQLite fact table** with per-game stats for all Sun Belt players.
4. **Dim tables**: `teams` and `players`.
5. **Season-level box-score + TS%** in `player_season_stats` and a Sun Belt view.
6. **Simple player similarity table** using box-score features.
7. **Roster-driven enrichment** of players (class year, height, weight) + a joined **player profile view**.

---

## Repo Layout

```text
itpr-ncaa-database-v0/
├── configs/
│   └── sunbelt_2024_25.yml              # Team slugs + paths for Sun Belt 2024–25
├── ncaa-analytics/
│   ├── data_raw/
│   │   └── sun_belt/2024-25/            # Raw Sports-Reference HTML pages
│   ├── data_intermediate/
│   │   └── sun_belt/2024-25/            # Per-team + combined per-game CSVs + roster CSV
│   └── db/
│       └── ncaa_dev.db                  # SQLite dev database
├── scripts/
│   ├── scrape_sunbelt_2024_25.py        # STEP 1: download raw HTML for all Sun Belt teams
│   ├── parse_sportsref_sunbelt_2024_25.py
│   │                                     # STEP 2: HTML -> per-game CSVs + combined CSV
│   ├── load_sunbelt_2024_25_sqlite.py   # STEP 3: load combined CSV into SQLite fact table
│   ├── init_sun_belt_v0_schema.py       # STEP 4: create teams + players dim tables
│   ├── init_sunbelt_v0_season_stats.py  # STEP 5: build season stats + TS% + Sun Belt view
│   ├── compute_sunbelt_2024_25_similarity.py
│   │                                     # STEP 6: build player-to-player similarity table
│   ├── parse_sportsref_sunbelt_2024_25_rosters.py
│   │                                     # STEP 7a: parse roster tables (height, weight, class)
│   ├── update_players_from_sunbelt_rosters_2024_25.py
│   │                                     # STEP 7b: enrich players table from roster CSV
│   └── init_sunbelt_v0_player_profile_view.py
│                                         # STEP 7c: create joined player profile view
├── requirements.txt
├── .gitignore
├── LICENSE
└── README.md
```

---

## Environment Setup

Requires **Python 3.10+**.

```bash
git clone https://github.com/itprodirect/itpr-ncaa-database-v0.git
cd itpr-ncaa-database-v0

# Create and activate virtualenv (Windows + Git Bash)
python -m venv .venv
source .venv/Scripts/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Pipeline: Step-by-Step

You only need to run these in order once to build the V0 Sun Belt warehouse from scratch.

### 1. Scrape Sun Belt HTML

Downloads each Sun Belt team’s Sports-Reference page for the 2025 season and stores the HTML.

```bash
python scripts/scrape_sunbelt_2024_25.py
```

Outputs (example):

* `ncaa-analytics/data_raw/sun_belt/2024-25/arkansas-state_2025.html`
* `.../appalachian-state_2025.html`
* etc. (14 teams)

---

### 2. Parse per-game stats from HTML

Extracts the **per-game player stats table** for each team, writes per-team CSVs, and then one combined file.

```bash
python scripts/parse_sportsref_sunbelt_2024_25.py
```

Outputs:

* `ncaa-analytics/data_intermediate/sun_belt/2024-25/*_2025_per_game.csv`
* `ncaa-analytics/data_intermediate/sun_belt/2024-25/sun_belt_2024_25_per_game_all_teams.csv`

Each row ≈ one player’s per-game line on their team’s Sports-Reference page.

---

### 3. Load into SQLite

Creates a dev SQLite DB and loads the combined per-game CSV into a fact table.

```bash
python scripts/load_sunbelt_2024_25_sqlite.py
```

Creates:

* DB: `ncaa-analytics/db/ncaa_dev.db`
* Table: `player_per_game_sun_belt_2024_25`

Each row = player × team × season per-game stats.

---

### 4. Initialize dim tables (teams, players)

Creates basic `teams` and `players` tables and seeds them from the Sun Belt per-game table.

```bash
python scripts/init_sun_belt_v0_schema.py
```

Creates:

* `teams` (team_id, team_slug, conference, etc.)
* `players` (player_id, full_name, team_id, season, …)

---

### 5. Build season stats + TS% view

Aggregates per-game stats into a season-level table and calculates true shooting percentage (TS%). Also provides a Sun Belt-only convenience view.

```bash
python scripts/init_sunbelt_v0_season_stats.py
```

Creates:

* `player_season_stats` (player_id, team_id, season, pts, trb, ast, stl, blk, FGA, FTA, 3PA, etc. + `ts_pct`)
* View: `sun_belt_player_season_2024_25`
  (joins players, teams, and `player_season_stats` for Sun Belt 2024–25)

Example query:

```sql
SELECT full_name, team_slug, pts, ts_pct
FROM sun_belt_player_season_2024_25
ORDER BY pts DESC
LIMIT 10;
```

---

### 6. Player similarity (box-score based)

Computes a simple similarity engine using standardized box-score features (e.g., PTS, TRB, AST, STL, BLK, TS%) and writes a table of “top K comps” for each player.

```bash
python scripts/compute_sunbelt_2024_25_similarity.py
```

Creates:

* `player_similarity_sun_belt_2024_25`
  (columns: `player_id`, `comp_player_id`, `distance`, `rank`, plus indexes)

Example usage in SQLite (find comps for a specific player):

```sql
SELECT
  p.full_name      AS player,
  t.team_slug      AS team,
  cp.full_name     AS comp_player,
  ct.team_slug     AS comp_team,
  s.rank,
  s.distance
FROM player_similarity_sun_belt_2024_25 s
JOIN players p    ON s.player_id      = p.player_id
JOIN teams   t    ON p.team_id        = t.team_id
JOIN players cp   ON s.comp_player_id = cp.player_id
JOIN teams   ct   ON cp.team_id       = ct.team_id
WHERE p.full_name = 'Taryn Todd'
ORDER BY s.rank;
```

---

### 7. Roster-driven enrichment (height, weight, class year)

#### 7a. Parse roster tables from HTML

Extracts the roster table from each team’s Sports-Reference page (name, position, height, weight, class year, etc.) and writes a combined roster CSV.

```bash
python scripts/parse_sportsref_sunbelt_2024_25_rosters.py
```

Outputs:

* `ncaa-analytics/data_intermediate/sun_belt/2024-25/sun_belt_2024_25_roster_all_teams.csv`

Contains one row per roster player, including:

* `team_slug`
* `full_name`
* `class_year` (FR, SO, JR, SR, GR, etc.)
* `height_cm`
* `weight_kg`
* (plus raw strings used to derive those fields)

#### 7b. Update `players` table with roster info

Matches roster rows to existing players and updates their bio fields. Logs any names that failed to match.

```bash
python scripts/update_players_from_sunbelt_rosters_2024_25.py
```

Effects:

* Adds `class_year`, `height_cm`, `weight_kg` columns to `players` (if missing).
* Fills those columns for the vast majority of Sun Belt 2024–25 players.
* Prints a short list of unmatched roster rows (name/slug mismatches for manual follow-up).

#### 7c. Create a player profile view

Creates a Sun Belt-specific view joining players, teams and season stats into a single “profile” row per player.

```bash
python scripts/init_sunbelt_v0_player_profile_view.py
```

Creates:

* View: `sun_belt_player_profile_2024_25`

Columns (simplified):

* `player_id`
* `full_name`
* `team_slug`
* `class_year`
* `height_cm`
* `weight_kg`
* `pts`
* `ts_pct`

Example query:

```sql
SELECT full_name,
       team_slug,
       class_year,
       height_cm,
       weight_kg,
       pts,
       ts_pct
FROM sun_belt_player_profile_2024_25
ORDER BY pts DESC
LIMIT 10;
```

This gives a quick “who are the top scorers, how big are they, and what class are they in?” snapshot for the entire Sun Belt.

---

## Dev Notes / Next Ideas (not yet implemented)

* Add age and/or DOB to players (from recruiting sites) and plug that into similarity.
* Extend the pipeline to additional conferences (SEC/ACC/etc.) using the same pattern.
* Add a small Jupyter notebook front-end for interactive scouting queries.

---

## License

MIT – see `LICENSE` for details.

---

## Quick Session Summary (for future Nick)

* Built a full Sun Belt 2024–25 pipeline: scrape → parse → CSV → SQLite.
* Created `teams`, `players`, `player_season_stats`, and a Sun Belt season view.
* Implemented a basic player-to-player similarity table from box-score stats.
* Parsed roster tables, enriched players with class/height/weight, and added a `sun_belt_player_profile_2024_25` view.
* All code and schema for this V0 are checked into:
  `https://github.com/itprodirect/itpr-ncaa-database-v0`
