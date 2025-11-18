from pathlib import Path
import sqlite3
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "ncaa-analytics" / "db" / "ncaa_dev.db"
ROSTER_CSV = PROJECT_ROOT / "ncaa-analytics" / "data_intermediate" / \
    "sun_belt" / "2024-25" / "sun_belt_2024_25_roster_all_teams.csv"


def ensure_class_year_column(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(players);")
    cols = [row[1] for row in cur.fetchall()]
    if "class_year" not in cols:
        print("Adding players.class_year column ...")
        cur.execute("ALTER TABLE players ADD COLUMN class_year TEXT;")
        conn.commit()


def main():
    if not ROSTER_CSV.exists():
        raise FileNotFoundError(f"Roster CSV not found: {ROSTER_CSV}")

    roster_df = pd.read_csv(ROSTER_CSV)
    # Normalize
    roster_df["player"] = roster_df["player"].astype(str).str.strip()
    roster_df["team_slug"] = roster_df["team_slug"].astype(str).str.strip()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    ensure_class_year_column(conn)
    cur = conn.cursor()

    updated = 0
    missing = []

    for row in roster_df.itertuples(index=False):
        team_slug = row.team_slug
        season = int(row.season)
        player_name = row.player.strip()

        height_cm = None if pd.isna(row.height_cm) else int(row.height_cm)
        weight_kg = None if pd.isna(row.weight_kg) else int(row.weight_kg)
        class_year = None if pd.isna(
            row.class_year) else str(row.class_year).strip()

        # Find matching player_id
        cur.execute(
            """
            SELECT p.player_id
            FROM players p
            JOIN teams t ON t.team_id = p.team_id
            WHERE p.season = ?
              AND t.team_slug = ?
              AND p.full_name = ?
            """,
            (season, team_slug, player_name),
        )
        res = cur.fetchone()
        if not res:
            missing.append((player_name, team_slug))
            continue

        player_id = res[0]

        cur.execute(
            """
            UPDATE players
            SET
                height_cm = COALESCE(?, height_cm),
                weight_kg = COALESCE(?, weight_kg),
                class_year = COALESCE(?, class_year)
            WHERE player_id = ?;
            """,
            (height_cm, weight_kg, class_year, player_id),
        )
        updated += 1

    conn.commit()
    conn.close()

    print(f"Updated {updated} player rows.")
    if missing:
        print(
            f"{len(missing)} roster rows did not match any players (name/slug mismatch?):")
        for name, slug in missing[:10]:
            print(f"  - {name} ({slug})")
        if len(missing) > 10:
            print("  ...")


if __name__ == "__main__":
    main()
