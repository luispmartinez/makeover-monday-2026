"""
build_tourism.py
----------------
Reshape Tourism_2025.xlsx (Eurostat, wide: one column per month) into a long
CSV for Tableau: one row per geo x month.

Paths come from paths_local.py, so this script holds no machine-specific paths.
"""
import pandas as pd

import paths_local

import numpy as np

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


EU27 = ["Belgium", "Bulgaria", "Czechia", "Denmark", "Germany", "Estonia",
        "Ireland", "Greece", "Spain", "France", "Croatia", "Italy", "Cyprus",
        "Latvia", "Lithuania", "Luxembourg", "Hungary", "Malta", "Netherlands",
        "Austria", "Poland", "Portugal", "Romania", "Slovenia", "Slovakia",
        "Finland", "Sweden"]
EU_NAME = "European Union - 27 countries (from 2020)"
NON_EU = ["Iceland", "Liechtenstein", "Norway", "Switzerland"]



def load_wide(path) -> pd.DataFrame:
    df = pd.read_excel(path)

    # 1. Eurostat puts an empty flag column after every value column
    #    ("Unnamed: N"). Drop them.
    df = df[[c for c in df.columns if not str(c).startswith("Unnamed")]]
    df = df.rename(columns={"GEO (Labels)": "geo"})

    # 2. Footer ("Special value" / ": not available") sits below a blank row.
    #    Cut at the first blank geo.
    first_blank = df["geo"].isna().idxmax()
    if df["geo"].isna().any():
        df = df.loc[: first_blank - 1]

    # 3. Eurostat repeats single-region countries at several NUTS levels
    #    (e.g. Luxembourg x3, Berlin x2) with identical numbers. Drop exact
    #    duplicates. Nord-Est (Italy vs Romania) differs in values, so it
    #    correctly survives.
    df = df.drop_duplicates().reset_index(drop=True)
    return df


def to_long(df: pd.DataFrame) -> pd.DataFrame:
    # Months only. "Total" is the sum of the 12 months, so melting it in would
    # double-count the moment anyone sums in Tableau. Keep it separately.
    long = df.melt(
        id_vars="geo",
        value_vars=MONTHS,
        var_name="month",
        value_name="nights",
    )

    # ":" is Eurostat's "not available". Coerce to NaN -> empty cell/Null in
    # Tableau, rather than a string that forces the whole column to text.
    long["nights"] = pd.to_numeric(long["nights"], errors="coerce")

    long["month_num"] = long["month"].map({m: i + 1 for i, m in enumerate(MONTHS)})
    long["date"] = pd.to_datetime(
        {"year": 2025, "month": long["month_num"], "day": 1}
    )

    # Stable order: geo as in source, then calendar month.
    long["_geo_order"] = long["geo"].map(
        {g: i for i, g in enumerate(df["geo"].drop_duplicates())}
    )
    long = (
        long.sort_values(["_geo_order", "month_num"])
        .drop(columns="_geo_order")
        .reset_index(drop=True)
    )
    return long[["geo", "date", "month", "month_num", "nights"]]

def add_level(long):
    conditions = [long["geo"] == EU_NAME, long["geo"].isin(EU27), long["geo"].isin(NON_EU)]
    labels = ["eu", "country", "non_eu_country"]
    long["level"] = np.select(conditions, labels, default="region")
    counts = long.groupby("level")["geo"].nunique()
    assert counts["country"] == 27
    assert counts["non_eu_country"] == 4
    assert counts["eu"] == 1
    return long
    

def main() -> None:
    paths_local.ensure()
    wide = load_wide(paths_local.SOURCE_FILE)
    long = to_long(wide)
    long = add_level(long)
    out = paths_local.write_atomic(long, "tourism_2025_long.csv")
    print(f"{len(wide)} geos x 12 months -> {len(long)} rows")
    print(f"{long['nights'].isna().sum()} null (':' not available) rows")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
