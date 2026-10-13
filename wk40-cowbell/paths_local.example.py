"""
Copy this file to paths_local.py and edit. paths_local.py is gitignored.
Machine-specific paths: every pipeline script imports from here.
"""
from pathlib import Path

RAW = Path(__file__).parent

# Tableau extracts. MUST be local disk, not iCloud/Dropbox/OneDrive: cloud sync
# evicts idle files and leaves zero-byte placeholders that Tableau refreshes into
# blank extracts without an error.
OUT = Path.home() / "TableauData" / "Cowbell"

SOURCE_FILE           = RAW / "drop" / "MM2026_wk40.xlsx"             # Makeover Monday week 40 list
HOT100_FILE           = RAW / "drop" / "hot-100-current.csv"          # utdata/rwd-billboard-data (CC BY)
TITLE_OVERRIDES_FILE  = RAW / "lookups" / "title_match_overrides.csv"
CREDIT_OVERRIDES_FILE = RAW / "lookups" / "credit_match_overrides.csv"
FONTS_DIR             = RAW / "fonts"                                 # Anton, Barlow Condensed, Open Sans (all OFL)

_CLOUD = ("icloud", "com~apple~clouddocs", "dropbox", "onedrive", "google drive")


def ensure():
    """Create the output dir. Refuse to write extracts anywhere cloud-synced."""
    low = str(OUT.resolve()).lower()
    for token in _CLOUD:
        if token in low:
            raise RuntimeError(f"OUT resolves to a cloud-synced path ({OUT}). Move it to local disk.")
    OUT.mkdir(parents=True, exist_ok=True)
    for f in [SOURCE_FILE, HOT100_FILE, TITLE_OVERRIDES_FILE, CREDIT_OVERRIDES_FILE]:
        if not f.exists():
            raise FileNotFoundError(f"source file not found: {f}")
    return OUT


def write_atomic(df, name, **kwargs):
    """Write via temp-file rename so a crashed run never leaves a partial file
    that Tableau will happily refresh from."""
    final = OUT / name
    tmp = final.with_suffix(final.suffix + ".tmp")
    df.to_csv(tmp, index=False, **kwargs)
    tmp.replace(final)
    return final
