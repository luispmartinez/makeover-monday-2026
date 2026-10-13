"""
scan_and_profile.py
--------------------
The "drop a file, get a report" layer. This script has almost no logic of
its own — it just finds CSV and XLSX files and hands each one to DatasetProfiler. That's
intentional: if this script grows real analysis logic, that logic stops
being reusable. Keep the smarts in eda_toolkit.py.

Usage:
    python3 scan_and_profile.py

Folder layout this expects, sitting next to this script:
    drop/       <- put CSV and/or XLSX files here
    reports/    <- one <name>_eda.md appears here per CSV or XLSX, after a run

Run it again after dropping a new file and only the new file's report
changes (existing reports for unchanged files aren't rewritten unless you
delete them first — see SKIP_EXISTING below).
"""

from pathlib import Path
import pandas as pd
import json




from eda_toolkit import DatasetProfiler

HERE = Path(__file__).parent
REGION_LOOKUP_PATH = HERE / "region_lookup.json"
DROP_FOLDER = HERE / "drop"
REPORT_FOLDER = HERE / "reports"

SKIP_EXISTING = True  # set False to force re-profiling every CSV every run

# Dataset-specific column exclusions, keyed by filename stem.
# Most CSVs won't need an entry here — .get() falls back to None for those.
EXCLUDE_COLUMNS_BY_FILE = {
    "gen_z_sports_betting_investing": ["Birth Years"],
    "Taylor_Swift_Spotify_Data": ["Playlist ID","Time Signature"],
    "Taylor_Swift_Genius_Data": ["Index"],
    "chatgpt-animal-stories": ["response", "prompt", "full_date"],
    "kids-book-animals": ["ISBN", "description"],
    "survey-animal-stories": ["response"],
    "hot-100-current": ["title", "performer", "chart_week"],
}
MIN_CATEGORY_SIZE_BY_FILE = {
    "cfb_roster_budgets_2026": 6,
}
METADATA_BY_FILE = {
    "gen_z_sports_betting_investing": {
        "group": "Generation",
        "metric": "Metric",
        "percent": "Percent",
        "n": "Respondents",
        "is_overall": "Is Overall",
    },
}

EXTS = {".csv", ".xls", ".xlsx"}

READ_OPTIONS_BY_FILE = {
    "World-Population": {"sheet_name": "Data"},
}


def main() -> None:
    DROP_FOLDER.mkdir(exist_ok=True)
    REPORT_FOLDER.mkdir(exist_ok=True)

    data_paths = sorted(p for p in DROP_FOLDER.iterdir() if p.suffix.lower() in EXTS)

    if not data_paths:
        print(f"No data files found in {DROP_FOLDER}. Drop one in and re-run.")
        return

    for data_path in data_paths:
        report_path = REPORT_FOLDER / f"{data_path.stem}_eda.md"

        if SKIP_EXISTING and report_path.exists():
            print(f"Skipping {data_path.name} (report already exists)")
            continue

        print(f"Profiling {data_path.name} ...")
        
        opts = READ_OPTIONS_BY_FILE.get(data_path.stem, {})
        if data_path.suffix.lower() == ".csv":
            df = pd.read_csv(data_path, **opts)
        else:  # .xls / .xlsx, already filtered by EXTS
            df = pd.read_excel(data_path, **opts)
        
        # inside main(), after df = pd.read_csv(csv_path):
        if REGION_LOOKUP_PATH.exists() and data_path.stem == "IMF GDP":
            with open(REGION_LOOKUP_PATH) as f:
                region_by_code = json.load(f)
            df["region"] = df["code"].map(region_by_code)
        
        exclude_columns = EXCLUDE_COLUMNS_BY_FILE.get(data_path.stem)
        metadata = METADATA_BY_FILE.get(data_path.stem, {})
        min_cat = MIN_CATEGORY_SIZE_BY_FILE.get(data_path.stem, 32)
        DatasetProfiler(df, name=data_path.stem, exclude_columns=exclude_columns, min_category_size = min_cat, **metadata).run().write_report(report_path)
        print(f"  -> {report_path.name}")


if __name__ == "__main__":
    main()