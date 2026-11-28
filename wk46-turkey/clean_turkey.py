"""clean_turkey.py: wk46 turkey. Raw .xlsx -> four clean csv files """
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "toolkit"))
import pandas as pd
from clean_toolkit import clean_text, top_repeated, write_clean, NA_STRINGS

# 0. Config
INPUT_PATH     = Path(__file__).parent / "raw" / "minnesota_turkey_fact_sheet.xlsx"
OUTPUT_FOLDER = "~/TableauData/minnesota-turkey/clean"
DROP_FOLDER    = Path(__file__).parent / "drop"        # scanner input: clean file only
CLEAN_EXCLUDE = ("Category", "Metric", "Poultry Sector",
                 "State / Category", "Market / Country", "Unit / Context",
                 "State Code")          # columns clean_text must leave alone (IDs, URLs?)
SHARE_MIN, SHARE_MAX = 0, 1.01

# (sheet, skiprows, nrows, usecols, output name)
TABLES = [
    ("Overview & Key Metrics",     4,  9, "A:D", "key_metrics"),
    ("Overview & Key Metrics",    16,  3, "A:B", "poultry_mix"),
    ("US Top Producing States",    3, 11, "A:D", "us_states"),
    ("MN Export Top Markets",      3,  8, "A:D", "mn_exports"),
]                   # the four entries
EXPECTED_ROWS = {"key_metrics": 9, "poultry_mix": 3, "us_states": 11, "mn_exports": 8}             # keyed by the output name


# 1. Read: loop over TABLES
tables = {}
for sheet, skip, n, cols, name in TABLES:
    t = pd.read_excel(INPUT_PATH, sheet_name=sheet, skiprows=skip, nrows=n, usecols=cols)
    print(t.columns.tolist())
    assert len(t) == EXPECTED_ROWS[name], f"{name}: row count changed"
    tables[name] = t

assert tables["us_states"].iloc[-1, 1] == "All other"
assert tables["mn_exports"].iloc[-1, 1] == "All other"

# 2. Text hygiene
clean, logs = {}, {}
for name, t in tables.items():
    clean[name], logs[name] = clean_text(t, na_strings=NA_STRINGS| {"-"}, exclude=CLEAN_EXCLUDE)
    print(name); print(logs[name].to_string())
assert pd.api.types.is_numeric_dtype(clean["us_states"]["Rank"]), "Rank is not numeric"
assert clean["us_states"]["Rank"].isna().sum() == 1
us  = clean["us_states"]["Share of U.S. Production"]
ex  = clean["mn_exports"]
pm  = clean["poultry_mix"]["Share of MN Poultry Production"]
assert abs(us.sum() - 1.01) < 0.001            # source says 1.01
assert abs(ex["Estimated Export Value (USD)"].sum() - 104000000) < 1
assert abs(pm.sum() - 1.0) < 0.001
assert us.between(SHARE_MIN, SHARE_MAX).all()
assert abs(ex["Market Share (%)"].sum() - 1.0) < 0.001

# states: shares sum to ~1.0; exports: values sum to 104,000,000
for name, df in clean.items():
    write_clean(df, OUTPUT_FOLDER, f"{name}.csv")
    write_clean(df, DROP_FOLDER, f"{name}.csv")
    print("wrote", name)