from pathlib import Path
import sqlite3

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "ncaa-analytics" / "db" / "ncaa_dev.db"

STATS_TABLE = "player_per_game_sun_belt_2024_25"


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    cur = conn.cursor()

    # ----------------------------------
    # 1. Create player_season_stats
    # ----------------------------------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS player_season_stats (
            player_season_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER NOT NULL,
            team_id   INTEGER NOT NULL,
            season    INTEGER NOT NULL,

            pos TEXT,
            g   INTEGER,
            gs  INTEGER,
            mp  REAL,

            fg   REAL,
            fga  REAL,
            fg_pct REAL,
            fg3  REAL,
            fg3a REAL,
            fg3_pct REAL,
            fg2  REAL,
            fg2a REAL,
            fg2_pct REAL,
            efg_pct REAL,
            ft   REAL,
            fta  REAL,
            ft_pct REAL,

            orb REAL,
            drb REAL,
            trb REAL,
            ast REAL,
            stl REAL,
            blk REAL,
            tov REAL,
            pf  REAL,
            pts REAL,

            ts_pct REAL,   -- derived metric
            awards TEXT,

            UNIQUE (player_id, team_id, season),

            FOREIGN KEY (player_id) REFERENCES players(player_id),
            FOREIGN KEY (team_id) REFERENCES teams(team_id)
        );
        """
    )

    # ----------------------------------
    # 2. Populate from per-game table
    # ----------------------------------
    # Note: TS% = PTS / (2 * (FGA + 0.44 * FTA)) if denominator > 0
    cur.execute(
        f"""
        INSERT OR REPLACE INTO player_season_stats (
            player_id, team_id, season,
            pos, g, gs, mp,
            fg, fga, fg_pct,
            fg3, fg3a, fg3_pct,
            fg2, fg2a, fg2_pct,
            efg_pct,
            ft, fta, ft_pct,
            orb, drb, trb,
            ast, stl, blk,
            tov, pf, pts,
            ts_pct,
            awards
        )
        SELECT
            p.player_id,
            t.team_id,
            s.season,

            s.pos,
            s.g, s.gs, s.mp,
            s.fg, s.fga, s.fg_pct,
            s.fg3, s.fg3a, s.fg3_pct,
            s.fg2, s.fg2a, s.fg2_pct,
            s.efg_pct,
            s.ft, s.fta, s.ft_pct,
            s.orb, s.drb, s.trb,
            s.ast, s.stl, s.blk,
            s.tov, s.pf, s.pts,
            CASE
                WHEN (s.fga + 0.44 * s.fta) > 0
                THEN s.pts / (2.0 * (s.fga + 0.44 * s.fta))
                ELSE NULL
            END AS ts_pct,
            s.awards
        FROM {STATS_TABLE} AS s
        JOIN teams   AS t ON t.team_slug = s.team_slug
        JOIN players AS p
          ON p.full_name = s.player
         AND p.team_id   = t.team_id
         AND p.season    = s.season;
        """
    )

    # ----------------------------------
    # 3. Convenience view for Sun Belt 24–25
    # ----------------------------------
    cur.execute(
        """
        CREATE VIEW IF NOT EXISTS v_sun_belt_player_season_2024_25 AS
        SELECT
            pss.*,
            pl.full_name,
            t.team_slug,
            t.conference
        FROM player_season_stats AS pss
        JOIN players AS pl ON pl.player_id = pss.player_id
        JOIN teams   AS t  ON t.team_id   = pss.team_id
        WHERE pss.season = 2025;
        """
    )

    conn.commit()

    # Sanity prints
    cur.execute("SELECT COUNT(*) FROM player_season_stats WHERE season = 2025;")
    print("player_season_stats rows (2025):", cur.fetchone()[0])

    conn.close()


if __name__ == "__main__":
    main()
