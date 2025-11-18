from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = PROJECT_ROOT / "ncaa-analytics" / "data_raw" / "sun_belt" / "2024-25"
INTERMEDIATE_DIR = PROJECT_ROOT / "ncaa-analytics" / \
    "data_intermediate" / "sun_belt" / "2024-25"
INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)

OUT_CSV = INTERMEDIATE_DIR / "sun_belt_2024_25_roster_all_teams.csv"


def parse_height_to_cm(ht):
    if not isinstance(ht, str):
        return None
    ht = ht.strip()
    if "-" not in ht:
        return None
    feet, inches = ht.split("-", 1)
    if not (feet.isdigit() and inches.isdigit()):
        return None
    total_inches = int(feet) * 12 + int(inches)
    return round(total_inches * 2.54)


def parse_weight_to_kg(wt):
    try:
        lbs = int(str(wt).strip())
    except (ValueError, TypeError):
        return None
    return round(lbs * 0.45359237)


def find_roster_table(html_path: Path) -> pd.DataFrame:
    """
    Find the roster-like table: one that has a 'Player' column and either
    'Class' or 'Pos' in the headers. This is more robust than relying on id='roster'.
    """
    tables = pd.read_html(html_path, flavor="bs4")
    for tbl in tables:
        cols_lower = [str(c).strip().lower() for c in tbl.columns]
        if "player" in cols_lower and ("class" in cols_lower or "pos" in cols_lower):
            return tbl
    raise ValueError(
        f"Could not find roster table in {html_path.name} (columns tried: {tables[0].columns if tables else []})")


def parse_roster_file(html_path: Path) -> pd.DataFrame:
    # stem looks like "arkansas-state_2025"
    stem = html_path.stem
    team_slug, season_str = stem.rsplit("_", 1)
    season = int(season_str)

    df = find_roster_table(html_path)

    # Build a dynamic rename map based on lowercase column names
    rename_map = {}
    for col in df.columns:
        low = str(col).strip().lower()
        if low == "player":
            rename_map[col] = "player"
        elif low in ("class", "cl", "yr", "year"):
            rename_map[col] = "class_year"
        elif low in ("pos", "position"):
            rename_map[col] = "pos"
        elif low in ("ht", "height", "hgt"):
            rename_map[col] = "height_raw"
        elif low in ("wt", "weight"):
            rename_map[col] = "weight_lbs"

    df = df.rename(columns=rename_map)

    # Required columns
    required = ["player"]
    for col in required:
        if col not in df.columns:
            raise ValueError(
                f"Roster table in {html_path.name} missing required column '{col}'. Got columns: {df.columns.tolist()}")

    # Start with required columns and add any optional ones that exist
    base_cols = ["player"]
    optional_cols = []
    for col in ("class_year", "pos", "height_raw", "weight_lbs"):
        if col in df.columns:
            optional_cols.append(col)

    keep_cols = base_cols + optional_cols
    df = df[keep_cols].copy()

    # Attach context
    df["team_slug"] = team_slug
    df["season"] = season

    # Height / weight conversions if present
    if "height_raw" in df.columns:
        df["height_cm"] = df["height_raw"].apply(parse_height_to_cm)
    else:
        df["height_cm"] = None

    if "weight_lbs" in df.columns:
        df["weight_kg"] = df["weight_lbs"].apply(parse_weight_to_kg)
    else:
        df["weight_kg"] = None

    # Normalize player name
    df["player"] = df["player"].astype(str).str.strip()

    # Drop rows with blank player names (sometimes header rows get repeated)
    df = df[df["player"] != ""]

    return df


def main():
    all_rows = []

    html_files = sorted(RAW_DIR.glob("*_2025.html"))
    if not html_files:
        print(f"No HTML files found in {RAW_DIR}")
        return

    for html_path in html_files:
        print(f"Parsing roster from {html_path.name} ...")
        try:
            df_team = parse_roster_file(html_path)
            print(f"  -> parsed {len(df_team)} rows")
            all_rows.append(df_team)
        except Exception as e:
            print(f"  !! ERROR on {html_path.name}: {e}")

    if not all_rows:
        print("No roster data parsed.")
        return

    roster_df = pd.concat(all_rows, ignore_index=True)
    roster_df.to_csv(OUT_CSV, index=False)
    print(f"\nWrote combined roster CSV: {OUT_CSV} ({len(roster_df)} rows)")


if __name__ == "__main__":
    main()
