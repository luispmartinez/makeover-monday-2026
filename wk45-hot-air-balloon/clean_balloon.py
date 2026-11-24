"""clean_balloon.py: wk45 hot air balloon. Raw .xlsx -> balloon_clean.csv"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "toolkit"))
import pandas as pd
from clean_toolkit import clean_text, split_range, top_repeated, write_clean

# 0. Config
INPUT_PATH     = Path(__file__).parent / "raw" / "hot_air_balloon.xlsx"
OUTPUT_FOLDER  = "~/TableauData/hot-air-balloon"             # CHANGE ME
SET_ASIDE_FOLDER = Path(__file__).parent / "set_aside"          # the week's folder, from the script's own location
DROP_FOLDER    = Path(__file__).parent / "drop"        # scanner input: clean file only
OUTPUT_FILE    = "balloon_clean.csv"
CLEAN_EXCLUDE  = ("BalloonID", "Name", "Registration", "Model", "SerialNumber")           # columns clean_text must leave alone (IDs, URLs?)
EXPECTED_RAW   = 7934                            # from my read; confirm on your first run
YEAR_MIN, YEAR_MAX = 1960, 2026        # plausible build/rebuild years
SIZE_MIN, SIZE_MAX = 12000, 600000        # plausible size in cubic feet

# 1. Read: header is row 2; take the first sheet, not its truncated name
df = pd.read_excel(INPUT_PATH, sheet_name=0, header=1)
assert len(df) == EXPECTED_RAW, "raw row count changed"

# 2. Text hygiene
# Q: should this run before or after the odd rows are removed? Why?
cleaned, log = clean_text(df, exclude=CLEAN_EXCLUDE)
print(log.to_string())

# 3. Set aside the odd rows (filter by condition, not by position)
# Q: should they be dropped or parked in their own file? 
# Set aside because one is blank rows and the other is URL rows. 
# Parked in their own file so nothing is lost
is_blank_row = cleaned.drop(columns=["BalloonID"]).isna().all(axis=1)           # every column except BalloonID is missing
is_url_row   = cleaned["Name"].str.startswith("https://", na= False)            # Name starts with "https://"
is_odd       = is_blank_row | is_url_row
odd = cleaned[is_odd]                                    # the rows set aside
d   = cleaned[~is_odd]                                    # the rows kept
print("blank:", is_blank_row.sum(), "| url:", is_url_row.sum(), "| kept:", len(d))
assert len(d) + len(odd) == EXPECTED_RAW, "rows lost in the split"
write_clean(odd, SET_ASIDE_FOLDER, "balloon_set_aside.csv")
# 4. Duplicates: expect none left
assert len(d) > 0, "no rows kept"
assert not d["Name"].str.startswith("http", na=False).any(), "URL rows left in Name"
assert d.BalloonID.is_unique, "BalloonID duplicates remain"
assert d["Manufacturer"].str.lower().ne("no").all(), "No left in Manufacturer"
assert len(d) == EXPECTED_RAW - is_blank_row.sum() - is_url_row.sum(), "mask counts overlap or rows lost"
assert not d.duplicated().any(), "exact duplicate rows remain"

# 5. Placeholders
print(top_repeated(d, "Manufacturer"))
print(top_repeated(d, "Model"))


# 6. Derived columns
# year_built, rebuilt_year from YearBuilt  (e.g. "2007, Rebuilt: 2021", "1985, Rebuilt: N/A")
# size_cuft from Size                      (e.g. "90,000 cu ft.", "110,000 cu ft")

yb = d["YearBuilt"]
d["year_built"]   = pd.to_numeric(yb.str.extract(r"^\s*(\d{4})")[0])    # four digits at the start of the cell
d["rebuilt_year"] = pd.to_numeric(yb.str.extract(r"Rebuilt: (\d{4})")[0])    # four digits right after "Rebuilt:"

# size_cuft: extract the number, strip commas, convert
size_text = d["Size"].str.extract(r"^([\d,]+)")[0]
d["size_cuft"] = pd.to_numeric(size_text.str.replace(",", ""))

# Flag everything that isn't one of the clean shapes
is_well_formed = yb.isna() | yb.str.fullmatch(r"\s*(\d{4}|N/A)(, Rebuilt: (\d{4}|N/A))?\s*")
is_plausible   = d["year_built"].between(YEAR_MIN, YEAR_MAX) | d["year_built"].isna()
d["year_built"] = d["year_built"].where(is_plausible)
flagged = d.loc[~(is_well_formed & is_plausible), ["BalloonID", "YearBuilt"]]
print("flagged:", len(flagged))
write_clean(flagged, SET_ASIDE_FOLDER, "yearbuilt_flags.csv")


# 7. Checks (each paired with a positive check, so none passes on empty)
# rows after split == 7235; BalloonID unique; no "https" left in Name; "No" gone from Manufacturer
both = d.dropna(subset=["year_built", "rebuilt_year"])
assert len(both) > 0, "no rows have both years"
assert d["Size"].notna().sum() > 0, "no Size values at all"
assert (both["rebuilt_year"] >= both["year_built"]).all(), "rebuilt before built"
assert d["size_cuft"].notna().sum() == d["Size"].notna().sum(), "a Size value did not parse"
assert d["size_cuft"].dropna().between(SIZE_MIN, SIZE_MAX).all(), "size outside plausible range"
assert d["year_built"].notna().sum() > 0, "no build years at all"
assert d["year_built"].dropna().between(YEAR_MIN, YEAR_MAX).all(), "implausible year survived"

# 8. Write
path = write_clean(d, OUTPUT_FOLDER, OUTPUT_FILE)
print("wrote", path)
path_drop = write_clean(d, DROP_FOLDER, OUTPUT_FILE)
print("wrote", path_drop)
