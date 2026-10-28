"""
explore_us_pop.py   (Stage 2)
US Census 1790 - 1990: prepare the hand-off files the canvas script reads.

Explores the preliminary findings in report/.
Writes 2 Stage 2 CSVs to ~/TableauData/wk42-us-pop/.
Tableau never reads these; build_us_pop_canvas.py turns them into geometry.


"""
# 1 Load libraries
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).parent
OUT = Path.home() / "TableauData" / "wk42-us-pop"   # local disk, never iCloud

def write_atomic(df, name):
    """Write via temp file + rename so a crashed run never leaves a half-written extract."""
    OUT.mkdir(parents=True, exist_ok=True)
    low = str(OUT.resolve()).lower()
    assert not any(t in low for t in ("icloud", "clouddocs", "dropbox", "onedrive")), \
        "OUT is cloud-synced; Tableau can refresh blank extracts from evicted files"
    final = OUT / name
    tmp = final.with_suffix(".csv.tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(final)
    return final

# 2 Load data
us_pop = pd.read_csv(HERE / "raw" / "us_state_population_1790_1990.csv", encoding="utf-8-sig")
assert len(us_pop) == 886, f"expected 886 rows but got {len(us_pop)}"
total_1990 = us_pop.loc[us_pop["Year"] == 1990, "Population"].sum()
assert total_1990 == 248709873, f"expected 248709873 but got {total_1990}"

# 3 State populations counts by census year
pop_wide = us_pop.pivot(index="State", columns="Year", values="Population")
assert pop_wide.notna().sum().sum() == 886      # filled cells, must equal the row count
assert pop_wide.isna().sum().sum() == 185      # 51 * 21 minus the above

# 4 State population growth by census year
growth = pop_wide.pct_change(axis=1, fill_method=None) * 100

# 5 Which states drove country popualtion growth?
pop_filled = pop_wide.fillna(0)
pop_count_all = pop_filled.diff(axis=1)
assert (pop_count_all.sum(axis=0).iloc[1:] == pop_wide.sum(axis=0).diff().iloc[1:]).all()
print(pop_count_all.loc["California", 1850])

# 6 Census-over-Census change
pop_count = pop_wide.diff(axis=1)
assert growth[1790].isna().all() and pop_count[1790].isna().all()

# 7 State shares by census
shares = pop_wide.div(pop_wide.sum(axis=0), axis=1) * 100
assert (shares.sum().round(6) == 100).all()

# 8 Key milestone census years
peak = pd.DataFrame({
    "peak_growth":   growth.max(axis=1),
    "peak_growth_yr": growth.idxmax(axis=1),
    "peak_share":    shares.max(axis=1),
    "peak_share_yr": shares.idxmax(axis=1),
})
peak["rank_growth"] = peak["peak_growth"].rank(ascending=False)
peak["rank_share"]  = peak["peak_share"].rank(ascending=False)

print(peak.sort_values("rank_growth").head(8))

peak["start_pop"] = [pop_wide.loc[s, int(y) - 10] for s, y in peak["peak_growth_yr"].items()]
print(peak.sort_values("start_pop")[["peak_growth", "peak_growth_yr", "start_pop"]].head(25))

assert peak.loc["Minnesota", "peak_growth_yr"] == 1860
assert peak.loc["Virginia", "rank_growth"] == 51 and peak.loc["Virginia", "rank_share"] == 1
assert peak["peak_share_yr"].eq(1990).sum() == 11
assert peak["peak_growth"].notna().all()


# 9 Export the Stage 2 hand-off files
SMALL_BASE = 25_000

growth_rows = pd.DataFrame({
    "State": peak.index,
    "view": "growth",
    "peak_value": peak["peak_growth"].values,
    "peak_year": peak["peak_growth_yr"].values,
    "rank": peak["rank_growth"].values,
    "rank_other": peak["rank_share"].values,
})

growth_rows["rank"] = growth_rows["rank"].astype(int)
growth_rows["rank_other"] = growth_rows["rank_other"].astype(int)
print(growth_rows[growth_rows["State"].isin(["Virginia", "Minnesota"])])

share_rows = pd.DataFrame({
    "State": peak.index,
    "view": "share",
    "peak_value": peak["peak_share"].values,
    "peak_year": peak["peak_share_yr"].values,
    "rank": peak["rank_share"].values,
    "rank_other": peak["rank_growth"].values,
})

hand_off = pd.concat([growth_rows, share_rows], ignore_index=True)

hand_off["move"] = hand_off["rank_other"] - hand_off["rank"]
hand_off[["rank", "rank_other", "move"]] = hand_off[["rank", "rank_other", "move"]].astype(int)

assert len(hand_off) == 102
assert hand_off.groupby("view")["rank"].apply(lambda r: sorted(r) == list(range(1, 52))).all()
assert hand_off.groupby("view")["move"].sum().eq(0).all()

va = hand_off[hand_off["State"] == "Virginia"].set_index("view")
assert va.loc["share", "rank"] == 1 and va.loc["share", "move"] == 50
assert va.loc["growth", "rank"] == 51 and va.loc["growth", "move"] == -50
print(hand_off[hand_off["State"].isin(["Virginia", "Minnesota"])])

hand_off["start_pop"] = hand_off["State"].map(peak["start_pop"]).astype("Int64")

hand_off["small_base"] = hand_off["start_pop"] < SMALL_BASE

def make_label(r):
    if r["view"] == "growth":
        txt = f"+{r['peak_value']:,.0f}%"
        if r["small_base"]:
            txt += f"   from {r['start_pop']:,.0f}"
        return txt
    return f"{r['peak_value']:.1f}%"

hand_off["small_base"] = hand_off["small_base"].astype("boolean")
share = hand_off["view"] == "share"
hand_off.loc[share, ["start_pop", "small_base"]] = pd.NA
hand_off["peak_value"] = hand_off["peak_value"].round(2)
hand_off["label"] = hand_off.apply(make_label, axis=1)

print(hand_off[hand_off["State"].isin(["Virginia", "Minnesota"])])
print(hand_off[hand_off["view"] == "growth"]["small_base"].sum())

MIN_MOVE = 8
def make_move_label(m):
    if abs(m) < MIN_MOVE:
        return ""
    return f"{'▲' if m > 0 else '▼'}{abs(m)}"

hand_off["move_label"] = hand_off["move"].apply(make_move_label)


assert hand_off.loc[(hand_off["State"] == "Minnesota") & (hand_off["view"] == "growth"), "label"].iloc[0] == "+2,731%   from 6,077"
assert hand_off.loc[(hand_off["State"] == "Virginia") & (hand_off["view"] == "share"), "label"].iloc[0] == "17.6%"
assert va.loc["share", "move"] == 50 and make_move_label(50) == "▲50" and make_move_label(-50) == "▼50"
print(hand_off[hand_off["State"].isin(["Virginia", "Minnesota"])])

duel = pd.DataFrame({"State": ["Indiana", "California"]}).set_index("State")
duel["peak_year"]   = peak["peak_growth_yr"]
duel["start_pop"]   = peak["start_pop"]
duel["added"]       = [pop_count.loc[s, int(y)] for s, y in duel["peak_year"].items()]
duel["peak_growth"] = peak["peak_growth"]
duel["peak_share"]  = peak["peak_share"]
duel["rank_growth"] = peak["rank_growth"].astype(int)
duel["rank_share"]  = peak["rank_share"].astype(int)

assert duel.loc["Indiana", "added"] == 21888 and duel.loc["California", "added"] == 287397
assert round(duel.loc["Indiana", "peak_growth"] / duel.loc["California", "peak_growth"], 1) == 2.7
assert round(duel.loc["California", "added"] / duel.loc["Indiana", "added"]) == 13
assert round(duel.loc["California", "peak_share"] / duel.loc["Indiana", "peak_share"], 1) == 2.7

write_atomic(hand_off, "us_pop_stage2.csv")
write_atomic(duel.reset_index(), "us_pop_duel.csv")