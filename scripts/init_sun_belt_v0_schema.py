from pathlib import Path
import sqlite3

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "ncaa-analytics" / "db" / "ncaa_dev.db"

STATS_TABLE = "player_per_game_sun_belt_2024_25"


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    cur = conn.cursor()

    # -------------------------
    # 1. Create teams table
    # -------------------------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS teams (
            team_id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_slug TEXT NOT NULL UNIQUE,
            conference TEXT NOT NULL,
            conference_division TEXT,
            is_d1 INTEGER NOT NULL DEFAULT 1
        );
        """
    )

    # -------------------------
    # 2. Create players table
    # -------------------------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS players (
            player_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            height_cm INTEGER,
            weight_kg INTEGER,
            birth_date TEXT,
            UNIQUE (full_name, team_id, season),
            FOREIGN KEY (team_id) REFERENCES teams(team_id)
        );
        """
    )

    # -------------------------
    # 3. Populate teams from stats table
    # -------------------------
    cur.execute(
        f"""
        INSERT OR IGNORE INTO teams (team_slug, conference)
        SELECT DISTINCT team_slug, 'Sun Belt'
        FROM {STATS_TABLE};
        """
    )

    # -------------------------
    # 4. Populate players from stats table
    # -------------------------
    cur.execute(
        f"""
        INSERT OR IGNORE INTO players (full_name, team_id, season)
        SELECT
            p.player AS full_name,
            t.team_id,
            p.season
        FROM {STATS_TABLE} AS p
        JOIN teams AS t
          ON t.team_slug = p.team_slug;
        """
    )

    conn.commit()

    # Simple sanity prints
    cur.execute("SELECT COUNT(*) FROM teams;")
    print("teams:", cur.fetchone()[0])

    cur.execute("SELECT COUNT(*) FROM players;")
    print("players:", cur.fetchone()[0])

    conn.close()


if __name__ == "__main__":
    main()
