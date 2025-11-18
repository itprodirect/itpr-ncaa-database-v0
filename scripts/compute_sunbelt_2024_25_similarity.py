from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "ncaa-analytics" / "db" / "ncaa_dev.db"

VIEW_NAME = "v_sun_belt_player_season_2024_25"
SIM_TABLE = "player_similarity_sun_belt_2024_25"


def main():
    conn = sqlite3.connect(DB_PATH)

    # 1. Load player-season data from the view
    df = pd.read_sql_query(
        f"""
        SELECT
            player_id,
            team_id,
            season,
            full_name,
            team_slug,
            pts,
            ast,
            trb,
            stl,
            blk,
            mp,
            ts_pct
        FROM {VIEW_NAME};
        """,
        conn,
    )

    # --- feature matrix ---
    feature_cols = ["pts", "ast", "trb", "stl", "blk", "mp", "ts_pct"]
    X = df[feature_cols].fillna(0.0).to_numpy(dtype=float)

    # 2. Standardize (z-score)
    means = X.mean(axis=0)
    stds = X.std(axis=0)
    stds[stds == 0] = 1.0  # avoid divide-by-zero

    X_norm = (X - means) / stds

    # 3. Compute nearest neighbours (Euclidean distance)
    records = []
    n = X_norm.shape[0]
    k = 5  # top-5 comps per player

    for i in range(n):
        diffs = X_norm - X_norm[i]
        dists = np.sqrt((diffs ** 2).sum(axis=1))
        dists[i] = np.inf  # ignore self

        nn_idx = np.argsort(dists)[:k]

        for rank, j in enumerate(nn_idx, start=1):
            records.append(
                {
                    "player_id": int(df.loc[i, "player_id"]),
                    "season": int(df.loc[i, "season"]),
                    "comp_player_id": int(df.loc[j, "player_id"]),
                    "comp_season": int(df.loc[j, "season"]),
                    "distance": float(dists[j]),
                    "rank": rank,
                }
            )

    sim_df = pd.DataFrame(records)
    print(f"Computed {len(sim_df)} similarity rows for {n} players.")

    # 4. Create / replace similarity table
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {SIM_TABLE} (
            player_id      INTEGER NOT NULL,
            season         INTEGER NOT NULL,
            comp_player_id INTEGER NOT NULL,
            comp_season    INTEGER NOT NULL,
            distance       REAL    NOT NULL,
            rank           INTEGER NOT NULL,

            PRIMARY KEY (player_id, season, comp_player_id, comp_season),
            FOREIGN KEY (player_id)      REFERENCES players(player_id),
            FOREIGN KEY (comp_player_id) REFERENCES players(player_id)
        );
        """
    )
    conn.execute(f"DELETE FROM {SIM_TABLE};")
    sim_df.to_sql(SIM_TABLE, conn, if_exists="append", index=False)
    conn.commit()

    # 5. Print a quick sample for sanity
    sample = df.sample(1, random_state=42).iloc[0]
    pid = int(sample["player_id"])
    name = sample["full_name"]
    print(f"\nSimilar players to {name} (player_id={pid}):")

    query = f"""
    SELECT s.rank,
           p2.full_name AS comp_name,
           s.distance
    FROM {SIM_TABLE} AS s
    JOIN players p2 ON p2.player_id = s.comp_player_id
    WHERE s.player_id = ?
    ORDER BY s.rank;
    """
    for row in conn.execute(query, (pid,)):
        print(row)

    conn.close()


if __name__ == "__main__":
    main()
