"""
explore balloon.py
This file explores the hot air balloon dataset and hands off findings to stage 3 build_balloon_canvas.py,
for the Tableau build.

"""


## explore_balloon.py                       one numbering style: 0 to 6

# 0  CONFIG
import json, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent.parent / "toolkit"))
from stage_helpers import write_atomic

HERE = Path(__file__).parent
SOURCE_FILE = HERE / "drop" / "balloon_clean.csv" # 
OUT = Path.home() / "TableauData" / "wk45-hot-air-balloon" / "work"
OUT.mkdir(parents=True, exist_ok=True)
TOP_PLACES = {"Arizona", 
              "California",
              "Colorado",
              "Canada",
              "Michigan",
              "New Mexico",
              "Ohio",
              "Texas",
              "UK",
              "Missouri"}
Z_CUT = 1.96
EXPECTED_TIERS = {'Ohio': 1, 'New Mexico': 2, 'Michigan': 2, 'Arizona': 3, 'Texas': 3, 'Missouri': 3, 'Colorado': 3, 'Canada': 4, 'California': 4, 'UK': 5}


# 1  LOAD (once)                          item 1: one read, no repeat
df = pd.read_csv(SOURCE_FILE)  



# 2  SHAPE ASSERTS                        these stay
counts = df["Location"].value_counts()
assert len(TOP_PLACES) == 10                          # ten places listed
assert set(counts.head(10).index) == TOP_PLACES               # they are the top ten by rows
assert counts.iloc[9] > counts.iloc[10]               # the tenth is bigger than the eleventh

TOP_TEN = df["Location"].isin(TOP_PLACES).sum()
assert TOP_TEN == 3611    # their rows add up
SEEN_YES = (df["SeenInPerson"] == "yes").sum()
assert SEEN_YES == 1200, f"expected 1200 SeenInPerson, got {SEEN_YES}"
N_ALL = len(df)
assert N_ALL == 7235, f"expected 7235 but got {N_ALL}"



# 3  LOOK                                 item 2: prints only, delete when locked
# nothing to see here, move along

# 4  FINDINGS
def lift_vs_place(df, places):
    """Rebuilt balloons seen vs the count their place's own non-rebuilt rate predicts."""
    sub = df[df["Location"].isin(places)].copy()
    sub["rebuilt"] = sub["rebuilt_year"].notna()
    sub["seen"] = (sub["SeenInPerson"] == "yes")
    base = sub[~sub["rebuilt"]].groupby("Location")["seen"].mean()
    r = sub[sub["rebuilt"]]
    p = r["Location"].map(base)                        # each rebuilt row's place base rate
    return {"n": len(r), "expected": float(p.sum()), "observed": int(r["seen"].sum()), "sd": float((p * (1 - p)).sum() ** 0.5)}

def tier_places(df, places):
    """Tier places by seen rate: a new tier starts when a place is Z_CUT standard errors below the tier leader."""
    sub = df[df["Location"].isin(places)].copy()
    sub["seen"] = (sub["SeenInPerson"] == "yes")
    g = sub.groupby("Location").agg(n=("seen", "size"), k=("seen", "sum"))
    g["p"] = g["k"] / g["n"]
    g = g.sort_values("p", ascending=False)
    var = g["p"] * (1 - g["p"]) / g["n"]                      # variance of each place's p (your old se line, renamed)
    tier = 1
    leader = g.index[0]
    tiers = {leader: tier}
    for place in g.index[1:]:               # every place except the leader
        z = (g.loc[place, "p"] - g.loc[leader, "p"]) / (var[place] + var[leader]) ** 0.5
        if z < -Z_CUT:
            tier += 1
            leader = place
        tiers[place] = tier
    return {"tiers": tiers, "p": g["p"], "n": g["n"], "k": g["k"], "se": var ** 0.5}   # se is the square root of var

def place_facts(df, places):
    """One row per place: n, share in service, seen among in service, largest fleet."""
    sub = df[df["Location"].isin(places)].copy()
    sub["seen"] = (sub["SeenInPerson"] == "yes")
    sub["in_service"] = (sub["Status"] == "in service")
    facts = pd.DataFrame({
        "n": sub.groupby("Location").size(),
        "in_service": sub.groupby("Location")["in_service"].mean(),
        "seen_in_service": sub[sub["in_service"]].groupby("Location")["seen"].mean(),
    })
    own = sub[sub["PilotOwner"].notna() & (sub["PilotOwner"] != "PENDING")]
    t = own.groupby(["Location", "PilotOwner"])["seen"].agg(owner_n="size", owner_seen="sum").reset_index()
    big = t[t["owner_n"] == t.groupby("Location")["owner_n"].transform("max")]
    big = big.sort_values(["Location", "PilotOwner"])
    top = big.groupby("Location").agg(
        top_owner=("PilotOwner", " & " .join),
        owner_n=("owner_n", "first" ),
        owner_seen=("owner_seen", lambda s: " and ".join(map(str, s)))
    )
    return facts.join(top)

LIFT = lift_vs_place(df, TOP_PLACES)
TIERS = tier_places(df, TOP_PLACES)
FACTS = place_facts(df, TOP_PLACES)

# 5  LOCK
assert LIFT["n"] == 44
assert LIFT["observed"] > LIFT["expected"] + 2 * LIFT["sd"]   # the claim: clearly above the place-only count
assert 1.5 <= LIFT["observed"] / LIFT["expected"] <= 2.5        # "about twice" in the caption
assert TIERS["tiers"] == EXPECTED_TIERS
assert len(FACTS) == 10 and FACTS.notna().all().all()                  # ten places, nothing missing
assert TIERS["k"].sum() == (df.loc[df["Location"].isin(TOP_PLACES), "SeenInPerson"] == "yes").sum()               # two code paths agree

assert FACTS.loc["New Mexico", "top_owner"] == "Rainbow Ryders"
assert FACTS.loc["New Mexico", "owner_n"] == 65 and FACTS.loc["New Mexico", "owner_seen"] == "34"
assert FACTS.loc["Arizona", "top_owner"] == "Hot Air Expeditions & Northern Light Balloon Expeditions"                       # both tied fleets
assert round(FACTS.loc["Ohio", "seen_in_service"], 2) == 0.63


# 6  HANDOFF
HEADLINE = {
    "lift": {"n": LIFT["n"], "expected": LIFT["expected"], "observed": LIFT["observed"], "sd": LIFT["sd"]},
    "tiers": TIERS["tiers"], "totals": {"all": int(N_ALL), "top_ten": int(TOP_TEN), "seen": int(SEEN_YES)},
}
write_atomic(OUT / "headline.json", json.dumps(HEADLINE, indent=2) + "\n")
assert json.loads((OUT / "headline.json").read_text()) == HEADLINE

PLACES = FACTS.join(pd.DataFrame({"p": TIERS["p"], "k": TIERS["k"], "se": TIERS["se"],
                                  "tier": pd.Series(TIERS["tiers"])})).reset_index(names="Location")
ROUND_COLS = ["in_service", "seen_in_service", "p", "se"]
PLACES[ROUND_COLS] = PLACES[ROUND_COLS].round(4)
write_atomic(OUT / "places.csv", PLACES.to_csv(index=False))
PLACES_CHECK = pd.read_csv(OUT / "places.csv", dtype={"owner_seen": str})
pd.testing.assert_frame_equal(PLACES_CHECK, PLACES, check_exact=False, rtol=1e-9)

assert len(PLACES_CHECK) == len(TIERS["tiers"]) and PLACES_CHECK["Location"].is_unique
assert PLACES["k"].sum() == 673
assert PLACES.loc[PLACES["Location"] == "Ohio", "k"].iloc[0] == 117
