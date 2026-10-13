"""
build_cowbell_clean.py  --  TEMPLATE (about 75% yours to fill)
-------------------------------------------------------------
Reads the raw Makeover Monday file, cleans Artist/Title, writes CSVs for Tableau
into OUT (local disk) via paths_local.write_atomic.

Runs as-is: every TODO function passes the data through unchanged, so you can
run after each piece you fill in and watch the QA numbers move.

    source .venv/bin/activate
    python build_cowbell_clean.py

ORDER OF OPERATIONS MATTERS:
    load -> normalize text -> fix broken rows -> drop non-songs
         -> canonical artist names -> dedupe -> add measures -> QA -> write
Why: alias keys only match if the text is already normalized (curly vs straight
apostrophes will silently defeat a lookup), and dedupe only works AFTER artist
names are merged (Jimmy Buffet / Jimmy Buffett "Fins" are not duplicates until then).
"""
import re

import pandas as pd
from paths_local import ensure, write_atomic, SOURCE_FILE

# ======================================================================
# 1. CONFIG -- yours to fill. Keys must match the text AFTER normalize_text().
# ======================================================================

# variant -> canonical. Categories to hunt for (use value_counts on Artist,
# sorted alphabetically, and eyeball neighbors):
#   - spelling variants of one act (Buffet/Buffett, Matthews/Mathews ...)
#   - punctuation variants (B-52s vs B52s, Sleater Kinney vs Sleater-Kinney)
#   - long form vs abbreviation: "Bachman Turner Overdrive (BTO)" vs "BTO"
# DEFERRED:  - "The" prefix: pick ONE rule and apply it to everyone
#   - typos (Ritchie, Chilli, Mellisa ...)
# DECIDED (2026-10-11): leave "The" prefix and Funkadelic / Parliament Funkadelic as submitted.
# The artist keys already ignore "The"; Funkadelic stays separate (distinct credits on the Hot 100).
ARTIST_ALIASES = {
    "Jimmy Buffet": "Jimmy Buffett",
    "B’52s": "B-52s",                               # key keeps the curly apostrophe
    "The Chambers Brothers": "Chambers Brothers",   # "The" rule: strip it
    "Earth Wind and Fire": "Earth, Wind, and Fire",
    "Rage Against The Machine": "Rage Against the Machine",
    "Sleater Kinney": "Sleater-Kinney",
    "Dave Mathews Band": "Dave Matthews Band",
    "Lionel Ritchie": "Lionel Richie",
    "Lionel Ritchie and Diana Ross": "Lionel Richie and Diana Ross",
    "Simon & Garfunkle": "Simon & Garfunkel",
    "To Mnay Zooz": "Too Many Zooz",
    "Blue Suede": "Blue Swede",              # "Hooked on a Feeling", a No. 1
    "Mellisa Ethridge": "Melissa Etheridge",
    "Vanity Fair": "Vanity Fare",
    "Dee Lite": "Deee-Lite",
    "Salt n Pepper": "Salt-N-Pepa",
}

TITLE_FIXES = {
    "Happy \u2018Cause I\u2019m Going Home": "Happy \u2019Cause I\u2019m Going Home",
    "In \u2018Da Bum": "In \u2019Da Bum",
    "Don\u2019t Stop \u2018Til You Get Enough": "Don\u2019t Stop \u2019Til You Get Enough",
    "Time Has Come": "Time Has Come Today",
}

# (artist, title) exactly as it appears in the file -> corrected (artist, title).
# For rows where the source page's formatting broke the split:
#   swapped columns, or an artist that swallowed part of the title.
# Run INSPECT below first and copy the exact strings you see.
ROW_FIXES = {
    ("The Tide is high", "Blondie"): ("Blondie", "The Tide is high"),
    ("Deliverance", "You Am I"): ("You Am I", "Deliverance"),
    ("Big Mama Thorton", "Big Star Kangaroo"): ("Big Star", "Kangaroo"),
}

# One raw row that is really TWO songs -> list of replacement rows.
# Clue: look for a dash or a second song name inside Artist or Title.
# in inspect():  print(df.loc[[556]].to_dict("records"))
ROW_SPLITS = {
    ("Spencer Davis Group", "Love Is Strange — Mickey & Sylvia Gimme Some Loving"): [
        ("Mickey & Sylvia", "Love Is Strange"),
        ("Spencer Davis Group", "Gimme Some Loving"),
    ],
}

    
# Rows that are not songs (jokes, notes, placeholders). Same key shape as ROW_FIXES.
# Decide: drop them, or keep with a flag column? (a flag is reversible)
NON_SONGS = [
    ("To Mnay Zooz", "Every Song They Do Has a Klank!"),
]


# ======================================================================
# 2. STEPS -- one function each. Fill the bodies, keep the signatures.
# ======================================================================

def load() -> pd.DataFrame:
    # dtype=str on purpose: Smashing Pumpkins "1979" was being read as a number,
    # which made Title an `object` column.
    return pd.read_excel(SOURCE_FILE, dtype=str)

def _artist_key(a: str) -> str:
    return re.sub(r"[^a-z0-9]", "", re.sub(r"^the\s+", "", a.casefold().replace("’", "'")))

def inspect(df: pd.DataFrame) -> None:
    """Uncomment one at a time, run, read, re-comment."""
    # print(df.sort_values("Artist").to_string())
    # print(df[df.duplicated(keep=False)])
    # print(df[df["Artist"].str.contains(r"[^\w\s]", regex=True)])
    # print(df[df["Title"].str.contains(r"\s[-\u2014]\s")])
    # print(df["Artist"].value_counts().head(20))
    # print(df[df["Artist"].str.contains("Tide|Deliverance|Alt-J|Yamagata", case=False)])
    # print(df[df["Title"].str.contains("Blondie|You Am I|Accident", case=False)])
    # print(df.loc[[70, 162, 659]])    # row numbers from my earlier scan

    for a, t in zip(df["Artist"], df["Title"]):
        if "Tide" in a or "Deliverance" in a: print(repr(a), repr(t))
    groups = df.groupby(df["Artist"].map(_artist_key))["Artist"].unique()
    print(groups[groups.map(len) > 1])

def normalize_text(df: pd.DataFrame) -> pd.DataFrame:
    # 1. whitespace (no-op on this file, cheap insurance)
    for col in ["Artist", "Title"]:
        df[col] = df[col].str.strip()

    # 2. leading hyphen on Artist (-Alt-J). Which regex anchors to the START only?
    df["Artist"] = df["Artist"].str.replace(r"^-", "", regex=True)

    # 3. D”Angelo -> D’Angelo. Replace the whole name, not the quote character.
    df["Artist"] = df["Artist"].str.replace("D”Angelo", "D’Angelo", regex=False)

    # 4. trailing ">" on Title (Accident>). Which char do you strip, and from which end?
    df["Title"] = df["Title"].str.rstrip(">")
    
    # 5 fix elision quotes (exact titles only)
    missing = [k for k in TITLE_FIXES if k not in set(df["Title"])]
    assert not missing, f"title keys not found in data: {missing}"

    df["Title"] = df["Title"].map(lambda t: TITLE_FIXES.get(t, t))
    
    left = df["Title"][df["Title"].str.contains("\u2018")]
    assert list(left) == ["\u2018A\u2019 Bomb In Wardour Street"], f"unexpected ‘ left: {list(left)}"

    assert not df["Artist"].str.startswith("-").any()
    assert not df["Title"].str.endswith(">").any()
    print(df.loc[[12, 153, 475]])
    print(df[df["Artist"].str.contains("‘") | df["Title"].str.contains("‘")])

    return df

def fix_broken_rows(df: pd.DataFrame) -> pd.DataFrame:
    # 1. check first, while the original strings still exist
    pairs = set(zip(df["Artist"], df["Title"]))
    missing = [k for k in list(ROW_FIXES) + list(ROW_SPLITS) if k not in pairs]
    assert not missing, f"row keys not found in data: {missing}"

    # 2. then apply
    rows = []
    for key in zip(df["Artist"], df["Title"]):
        if key in ROW_SPLITS:
            rows.extend(ROW_SPLITS[key])
        else:
            rows.append(ROW_FIXES.get(key, key))
    df = pd.DataFrame(rows, columns=["Artist", "Title"])

    print(df[df["Artist"].isin(["Blondie", "You Am I", "Big Star", "Mickey & Sylvia", "Spencer Davis Group"])])   # temporary
    return df

def canonical_artists(df: pd.DataFrame) -> pd.DataFrame:
    # 1. checks: stop the script if the dict is wrong
    missing = [k for k in ARTIST_ALIASES if k not in set(df["Artist"])]
    assert not missing, f"alias keys not found in data: {missing}"
    same = [k for k, v in ARTIST_ALIASES.items() if k == v]
    assert not same, f"alias maps to itself (does nothing): {same}"

    # 2. the actual work: replace each Artist using the dict
    df["Artist"] = df["Artist"].map(lambda a: ARTIST_ALIASES.get(a, a))

    # 3. hand the result back to main()
    return df


def dedupe(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)
    df = df.drop_duplicates(subset=["Artist", "Title"]).reset_index(drop=True)
    
    print(f"dedupe removed {before - len(df)} rows")   # expect 6
    print(df[df.duplicated(subset=["Artist", "Title"], keep="first")])
    return df

def flag_non_songs(df: pd.DataFrame) -> pd.DataFrame:
    # 1. check first: every NON_SONGS key must exist in the data
    pairs = set(zip(df["Artist"], df["Title"]))
    missing = [k for k in NON_SONGS if k not in pairs]
    assert not missing, f"non-song keys not found in data: {missing}"

    # 2. new column: True unless the row's (Artist, Title) is in NON_SONGS
    df["Is Song"] = ~df.apply(lambda row: (row["Artist"], row["Title"]) in NON_SONGS, axis=1)

    print(df[~df["Is Song"]])    # temporary
    return df

def add_measures(df: pd.DataFrame) -> pd.DataFrame:
    # Songs: 1 per real song, 0 for flagged rows.
    # Hint: a True/False column converts to 1/0 with .astype(int)
    df["Songs"] = df["Is Song"].astype(int)

    # Artist Songs: each artist's total on every one of their rows.
    # Hint: groupby("Artist") + transform. Sum the Songs column, don't count rows.
    df["Artist Songs"] = df.groupby("Artist")["Songs"].transform("sum")

    # Artist Rank: 1 = the artist with the most songs.
    # Hint: Series.rank(method=..., ascending=False)
    df["Artist Rank"] = df["Artist Songs"].rank(method="dense", ascending=False).astype(int)

    # Is Top Artist: True at or above your chosen cutoff.
    df["Is Top Artist"] = df["Artist Songs"] >= 6
    print(df["Is Top Artist"].sum())

    print(df[["Artist", "Songs", "Artist Songs", "Artist Rank"]].drop_duplicates("Artist").sort_values("Artist Rank").head(12))   # temporary
    return df


def qa(before: int, df: pd.DataFrame) -> None:
    # 1. no duplicate (Artist, Title) rows
    assert not df.duplicated(subset=["Artist", "Title"]).any(), "duplicate rows survived"

    # 2. no null or blank Artist / Title
    #    Hint: two conditions per column, .isna() and .str.strip() == ""
    for col in ["Artist", "Title"]:
        bad = df[col].isna() | (df[col].str.strip() == "")
        assert not bad.any(), f"null or blank {col}"

    # 3. every Title and Artist is a str
    assert df["Title"].map(type).eq(str).all(), "non-string values"
    assert df["Artist"].map(type).eq(str).all(), "non-string values"

    # 4. none of the known-bad names survive
    leftover = set(df["Artist"]) & set(ARTIST_ALIASES.keys())
    assert not leftover, f"alias variants still present: {leftover}"

    # 5. sanity anchors
    expected = {
        "Kiss": 9, "Beatles": 8,
        "Rush": 7, "The Allman Brothers Band": 7,
        "Van Halen": 6, "Led Zeppelin": 6, "Queen": 6, "Guns n Roses": 6,
        "Donnas": 5, "Prince": 5, "Jimi Hendrix": 5,
        "Talking Heads": 4,
    }
    actual = df.drop_duplicates("Artist").set_index("Artist")["Artist Songs"]
    wrong = {a: (n, actual.get(a)) for a, n in expected.items() if actual.get(a) != n}
    assert not wrong, f"anchor counts off (expected, actual): {wrong}"

    # 6. the flag
    assert (~df["Is Song"]).sum() == 1, "expected exactly one non-song"

    print(f"rows: {before} -> {len(df)}   unique artists: {df['Artist'].nunique()}")


# ======================================================================
# 3. RUN
# ======================================================================


def main() -> None:
    ensure()                      # creates OUT, refuses cloud-synced paths
    df = load()
    before = len(df)
    inspect(df)

    df = normalize_text(df)
    df = fix_broken_rows(df)
    df = flag_non_songs(df)
    df = canonical_artists(df)
    inspect(df)
    df = dedupe(df)
    df = add_measures(df)

    qa(before, df)

    out = write_atomic(df, "cowbell_songs_clean.csv")
    print(f"wrote {out}")

    # TODO (optional): a second, tiny CSV with one row per artist (Artist, Songs,
    #       Rank) is often easier for a bar chart than aggregating in Tableau.
    # HINT: df.groupby("Artist", as_index=False)...  then write_atomic(artists, "cowbell_artists.csv")


if __name__ == "__main__":
    main()
