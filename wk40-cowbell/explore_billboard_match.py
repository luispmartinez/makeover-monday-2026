"""
explore_billboard_match.py -- Stage 2. Joins the cleaned cowbell songs to Billboard Hot 100
history (title and credit overrides reviewed by hand) and writes the hand-off CSV cowbell_stage2.csv.
"""



# FINDINGS (locked 2026-10-12) -- real songs only (Is Song), verified against this script's output
# 655 songs, 445 artists. 303 songs (46.3%) reached the Hot 100.
# Artists: 53.9% have a charted cowbell song; 71.9% appear in the Hot 100 at all.
# Top artists (6+ songs): 18 of 55 charted (32.7%); everyone else 285 of 600 (47.5%).
# Of the 303 that charted: 160 reached the Top 10 (53%), 54 reached No. 1.
# Reaper (the SNL sketch song): peak 12, 20 weeks.
# Caveat: "didn't chart" = no Hot 100 entry; match is by song, not recording.


# Step 1: load both files; collapse Hot 100 to one row per song (best peak, longest run).
import re
import pandas as pd
from paths_local import HOT100_FILE, TITLE_OVERRIDES_FILE, CREDIT_OVERRIDES_FILE, OUT, write_atomic


hot = pd.read_csv(HOT100_FILE)
cowbell = pd.read_csv(OUT / "cowbell_songs_clean.csv")
best = hot.groupby(["performer", "title"], as_index=False).agg(
    peak=("peak_pos", "min"),
    weeks=("wks_on_chart", "max"),
)
print(best.shape)   # expect ~ 30k rows

# Step 2: key functions -- casefold, strip punctuation, drop leading "The" on artists.
def _artist_key(a: str) -> str:
    return re.sub(r"[^a-z0-9]", "", re.sub(r"^the\s+", "", a.casefold().replace("’", "'").replace("&", "and")))

# Step 3: build keys on both tables; assert keys are unique.
def _title_key(t: str) -> str:
    return re.sub(r"[^a-z0-9]", "", t.casefold().replace("’", "'").replace("&", "and"))

best["akey"] = best["performer"].apply(_artist_key)
best["tkey"] = best["title"].apply(_title_key)
best = best.groupby(["akey", "tkey"], as_index=False).agg(
    performer=("performer", "first"),
    title=("title", "first"),
    peak=("peak", "min"),
    weeks=("weeks", "max"),
)
cowbell["akey"] = cowbell["Artist"].apply(_artist_key)
cowbell["tkey"] = cowbell["Title"].apply(_title_key)
assert not best.duplicated(subset=["akey", "tkey"]).any()
assert not (cowbell["akey"] == "").any() and not (cowbell["tkey"] == "").any()
print(cowbell.duplicated(subset=["akey", "tkey"]).sum())

# Step 4: apply title overrides (reviewed CSV; yes rows only) to the cowbell title key.
ov = pd.read_csv(TITLE_OVERRIDES_FILE)
ov["call"] = ov["your_call"].fillna(ov["my_call"]).str.strip().str.lower()     # your call wins; else mine
ov = ov[ov["call"] == "yes"]
ov["akey"]  = ov["Artist"].apply(_artist_key)
ov["tkey"]  = ov["cowbell_title"].apply(_title_key)
ov["tkey_hot"] = ov["hot100_title"].apply(_title_key)
fix = {(a, t): h for a, t, h in zip(ov["akey"], ov["tkey"], ov["tkey_hot"])}
print(len(ov))

cr = pd.read_csv(CREDIT_OVERRIDES_FILE)
cr["call"] = cr["your_call"].fillna(cr["my_call"]).str.strip().str.lower()     # your call wins; else mine
cr = cr[cr["call"] == "yes"]
cr["akey"]     = cr["Artist"].apply(_artist_key)
cr["tkey"]     = cr["cowbell_title"].apply(_title_key)
cr["akey_hot"] = cr["hot100_performer"].apply(_artist_key)
cr["tkey_hot"] = cr["hot100_title"].apply(_title_key)
fix2 = {(a, t): (ah, th) for a, t, ah, th in zip(cr["akey"], cr["tkey"], cr["akey_hot"], cr["tkey_hot"])}
print(len(cr))


# apply overrides to the cowbell key (Title is untouched)
keys = list(zip(cowbell["akey"], cowbell["tkey"]))
new  = [fix2.get(k, (k[0], fix.get(k, k[1]))) for k in keys]
cowbell["akey"] = [p[0] for p in new]
cowbell["tkey"] = [p[1] for p in new]
# every override target must exist in best
pairs = set(zip(best["akey"], best["tkey"]))
missing = [k for k in zip(ov["akey"], ov["tkey_hot"]) if k not in pairs]
assert not missing, f"override targets not in best: {missing}"
missing_cr = [k for k in zip(cr["akey_hot"], cr["tkey_hot"]) if k not in pairs]
assert not missing_cr, f"credit targets not in best: {missing_cr}"
assert not cowbell.duplicated(subset=["akey", "tkey"]).any()

# Step 5: left-merge on keys; assert row count unchanged; check the Reaper anchor.
m = cowbell.merge(best[["akey", "tkey", "peak", "weeks"]], on=["akey", "tkey"], how="left")
assert len(m) == len(cowbell)      # a merge must never add or drop rows
m["charted"] = m["peak"].notna()
print(m[m["Title"].str.contains("Reaper")][["Artist", "Title", "peak", "weeks"]])

# Step 6: report match rates and the unmatched list.
# Step 6: report match rates and the unmatched list (real songs only).
m["Is Top Artist"] = m["Artist Songs"] >= 6
ms = m[m["Is Song"]].copy()
assert len(ms) == 655

song_rate = ms["charted"].mean()
artist_rate = ms.groupby("Artist")["charted"].any().mean()
print(f"songs: {song_rate:.1%}   artists: {artist_rate:.1%}")
found = cowbell[cowbell["Is Song"]].drop_duplicates("Artist")["akey"].isin(best["akey"]).mean()
print(f"artists found in Hot 100: {found:.1%}")
print(ms.groupby("Is Top Artist")["charted"].agg(["mean", "sum", "count"]))

print(m[m["Is Top Artist"]].groupby("Artist")["charted"].agg(["sum", "count"]))
x = m[m["akey"].isin(best["akey"]) & ~m["charted"]]
print(len(x))
print(x[["Artist", "Title"]].to_string())

out = m[["Artist", "Title", "Artist Songs", "Artist Rank", "Is Song", "Is Top Artist", "charted", "peak", "weeks"]].copy()
out["Is No 1"]   = out["peak"] == 1
out["Is Top 10"] = out["peak"] <= 10
out["peak"]  = out["peak"].astype("Int64")
out["weeks"] = out["weeks"].astype("Int64")
assert len(out) == 656
assert out["peak"].dropna().between(1, 100).all()
reaper = out[out["Title"].str.contains("Reaper")]
assert reaper["peak"].iloc[0] == 12
write_atomic(out, "cowbell_stage2.csv")
print(f"wrote {len(out)} rows; {out['charted'].sum()} charted; {out['Is No 1'].sum()} No. 1; {out['Is Top 10'].sum()} Top 10")
