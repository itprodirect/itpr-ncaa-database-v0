from pathlib import Path
import sqlite3

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "ncaa-analytics" / "db" / "ncaa_dev.db"

DDL = """
DROP VIEW IF EXISTS sun_belt_player_profile_2024_25;

CREATE VIEW sun_belt_player_profile_2024_25 AS
SELECT
    p.player_id,
    p.full_name,
    t.team_slug,
    p.season,
    p.class_year,
    p.height_cm,
    p.weight_kg,
    s.g,
    s.mp,
    s.pts,
    s.ts_pct
FROM player_season_stats AS s
JOIN players AS p
  ON s.player_id = p.player_id
 AND s.season    = p.season
JOIN teams AS t
  ON s.team_id   = t.team_id
WHERE t.conference = 'Sun Belt'
  AND s.season     = 2025;
"""


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(DDL)
    conn.commit()
    conn.close()
    print(f"Created view sun_belt_player_profile_2024_25 on {DB_PATH}")


if __name__ == "__main__":
    main()
