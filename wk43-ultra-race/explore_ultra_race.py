# ---- STAGE 2: the numbers ----




# 1  load the data: runner_results + nation_years, drop DNS            
from pathlib import Path
import pandas as pd
import json

HERE = Path(__file__).parent
SRC = HERE / "drop" / "bigs_backyard_wtc_2020_2026.xlsx"
KEY = ["year", "nation_code"]
PACK_STAT = "median"          # the one place to change the pack definition

r = pd.read_excel(SRC, sheet_name="runner_results")
r = r[r.result != "DNS"]

# 2  nat table: leader, assist, pack, lead_vs_pack 
leader = r[r.result == "Winner"].set_index(KEY).yards.rename("leader_yards")
assist = r[r.result == "Assist"].groupby(KEY).yards.max().rename("assist_yards")
pack   = r[r.result == "Ran"].groupby(KEY).yards.agg(PACK_STAT).rename("pack_yards")

nat = pd.concat([leader, assist, pack], axis=1, join="inner").reset_index()
nat["lead_vs_pack"] = nat.leader_yards / nat.pack_yards

# 3  tripwires: gap == 1, unique keys, 179 rows 
assert leader.index.is_unique
assert ((nat.leader_yards - nat.assist_yards) == 1).all()
assert len(nat) == 179        # predict first
print(len(nat))
print(nat.lead_vs_pack.describe())
print(nat.loc[nat.lead_vs_pack.idxmax()])
# or, keeps the row as a frame:
print(nat[nat.lead_vs_pack == nat.lead_vs_pack.max()])

rr = r.merge(nat[KEY + ["leader_yards"]], on=KEY)
rr = rr[rr.result == "Ran"]
for f in [0.4, 0.5, 0.6, 0.7, 0.8]:
    surv = (rr.yards >= f * rr.leader_yards).groupby([rr.year, rr.nation_code]).mean()
    print(f, surv.groupby(level="year").median().round(2).to_dict())

# ---- STEP 4: survivor curve ----
# Merge = attach each nation-year's leader_yards to every runner row,
# so each runner knows how far *their* leader went.
pack_rows = r[r.result == "Ran"].merge(nat[KEY + ["leader_yards"]], on=KEY)

curve = {}
for f in [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
    # True/False per runner: did they last at least f of the leader's distance?
    still_in = pack_rows.yards >= f * pack_rows.leader_yards
    # The mean of True/False is the share who lasted. Group by nation-year first.
    share = still_in.groupby([pack_rows.year, pack_rows.nation_code]).mean()
    # Then pool: the median of those 179 shares.
    curve[f] = share.median()

curve = pd.Series(curve)
print(curve)

# ---- STEP 5: landmark ----
half_out = curve[curve <= 0.5].index.min()   # first fraction at or below 0.5
print(half_out, 1 / nat.lead_vs_pack.median())

# ---- STEP 6: constant nations ----
ny = pd.read_excel(SRC, sheet_name="nation_years")
scored = ny[ny.team_yards > 0]                     # only nations that scored yards

# For each nation, count the editions it scored in.
editions = scored.groupby("nation_code").year.nunique()
edition_count = scored.year.nunique()
constant = editions[editions == edition_count].index
print(len(constant))                               # predict first: I found 18

# ---- STEP 7: trend ----
trend = scored[scored.nation_code.isin(constant)].groupby("year")[["team_yards", "national_winner_yards"]].mean()
print(trend)
assert len(constant) == 18
half_out = curve[curve <= 0.5].index.min()
assert half_out == 0.6, f"Expected landmark 0.6, got {half_out}"
print(half_out, 1 / nat.lead_vs_pack.median())

# 8  headline numbers: compute every figure that will appear in large type, with asserts
HEADLINE = {
    "half_out":   round(1 / nat.lead_vs_pack.median(), 1),
    "races":      len(nat),
    "yards_2020": round(trend.team_yards.loc[2020]),
    "yards_2026": round(trend.team_yards.loc[2026]),
    "constant":   len(constant),
}

assert HEADLINE["half_out"] == half_out == 0.6
assert HEADLINE["races"] == 179
assert (HEADLINE["yards_2020"], HEADLINE["yards_2026"]) == (420, 715)
assert HEADLINE["constant"] == 18
print(HEADLINE)




OUT_DIR = Path.home() / "TableauData" / "Ultra Race"  # Set this to build_ultra_canvas.py's input folder
OUT_DIR.mkdir(parents=True, exist_ok=True)

headline_path = OUT_DIR / "headline.json"

def write_text_atomic(path, text):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)

median_curve = pd.DataFrame({"pct": list(range(101)), "share": [
    (pack_rows.yards * 100 >= p * pack_rows.leader_yards)
    .groupby([pack_rows.year, pack_rows.nation_code]).mean().median() for p in range(101)]})
assert median_curve.loc[median_curve.pct == 60, "share"].item() == 0.5

tight, breakaway = nat.loc[nat.lead_vs_pack.idxmin()], nat.loc[nat.lead_vs_pack.idxmax()]
assert (tight.year, tight.nation_code) == (2026, "AUS")
assert (breakaway.year, breakaway.nation_code) == (2022, "PAK")

steps = []
nation_of = r.drop_duplicates("nation_code").set_index("nation_code").nation


for (year, code), g in pack_rows.groupby(["year", "nation_code"]):
    n, L = len(g), g.leader_yards.iloc[0]
    nation = nation_of[code].replace(" of America", "")
    half = int(round((g.yards * 100 / L).median()))          # the per-race version of the 60% claim
    extra = (nation, int(L), n, half)
    named = "tight" if (year, code) == (2026, "AUS") else "breakaway" if (year, code) == (2022, "PAK") else ""
    share, order, remaining = 1.0, 0, n
    steps.append((year, code, order, 0.0, share, named) + extra); order += 1
    for pct, k in (g.yards * 100 / L).value_counts().sort_index().items():
        steps.append((year, code, order, pct, share, named) + extra); order += 1
        remaining -= k
        share = remaining / n
        steps.append((year, code, order, pct, share, named) + extra); order += 1
    assert remaining == 0 and share == 0.0

assert all(len(t) == 10 for t in steps), "a steps.append is missing + extra"
steps_df = pd.DataFrame(steps, columns=["year", "nation_code", "point_order", "pct", "share", "named",
                                        "nation", "leader_yards", "pack_n", "half_pct"])
assert steps_df.nation.notna().all()

assert len(median_curve) == 101
assert len(steps_df) == 3579
assert steps_df.groupby(["year", "nation_code"]).ngroups == HEADLINE["races"]

c2 = scored[scored.nation_code.isin(constant)][["nation_code", "nation", "year", "team_yards"]].copy()
top = c2[c2.year == 2026].nlargest(1, "team_yards").iloc[0]
assert (top.nation_code, top.team_yards) == ("USA", 1120)
c2["named"] = (c2.nation_code == top.nation_code).map({True: "highest", False: ""})
assert len(c2) == 72 and c2.groupby("nation_code").year.nunique().eq(4).all()
assert c2.groupby("year").team_yards.mean().round().tolist() == [420, 531, 654, 715]

sizes = r.groupby(KEY).size()
short = int((sizes.loc[nat.set_index(KEY).index] < 12).sum())
assert short == 6
no_winner = len(ny) - len(nat)
assert no_winner == 11
HEADLINE.update({"short_teams": short, "no_winner": no_winner})
race_hours = int(r[r.year == 2026].yards.max())
assert race_hours == 124
HEADLINE["race_hours"] = race_hours
gaps = nat.leader_yards - nat.assist_yards
assert gaps.nunique() == 1
HEADLINE["winner_gap"] = int(gaps.iloc[0])

write_text_atomic(OUT_DIR / "constant_nations.csv", c2.to_csv(index=False))
write_text_atomic(OUT_DIR / "headline.json", json.dumps(HEADLINE, indent=2) + "\n")
write_text_atomic(OUT_DIR / "median_curve.csv", median_curve.to_csv(index=False))
write_text_atomic(OUT_DIR / "step_curves.csv", steps_df.to_csv(index=False))
print(headline_path)

# ---- STAGE 3: the Tableau canvas ----
# 9  canvas rows: one long table with a `layer` column, x/y geometry, point_order, poly_id
# 10 write the CSV: temp file, then rename, into ~/TableauData/Ultra Race/