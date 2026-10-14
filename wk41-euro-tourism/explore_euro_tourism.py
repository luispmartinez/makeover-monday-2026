"""
Explore the euro tourism data set
Seasonal 
or 
scale 
"""
import pandas as pd
import paths_local
from scipy import stats
from build_tourism import MONTHS
import numpy as np

ANCHORS = {"Croatia", "Spain", "Luxembourg"}

def load():
    long = pd.read_csv(paths_local.OUT / "tourism_2025_long.csv")
    eu = long[long["level"] == "eu"]
    ctry = long[long["level"] == "country"]
    return eu, ctry


def annual(ctry):
    # one number per country, biggest first
    return ctry.groupby("geo")["nights"].sum().sort_values(ascending=False)


def summer_share(ctry):
    piv = ctry.pivot_table(index="geo", columns="month", values="nights", aggfunc="sum")
    summer = piv[["July", "August"]].sum(axis=1)
    return (summer / piv.sum(axis=1) * 100).sort_values()
def handoff(tot, summer):
    out = pd.DataFrame({
        "geo": tot.index,
        "annual_nights": tot.values,
        "summer_pct": summer.reindex(tot.index).round(1).values,
    })
    out["summer_rank"] = out["summer_pct"].rank(ascending=False, method="min").astype(int)
    return out.sort_values("summer_rank").reset_index(drop=True)

def monthly(ctry):
    piv = ctry.pivot_table(index="geo", columns="month", values="nights", aggfunc="sum")
    piv = piv[MONTHS]                          # calendar order, not alphabetical
    share = piv.div(piv.sum(axis=1), axis=0) * 100
    long = share.reset_index().melt(id_vars="geo", var_name="month", value_name="share_pct")
    long["month_num"] = long["month"].map({m: i + 1 for i, m in enumerate(MONTHS)})
    return long

def main():
    eu, ctry = load()
    tot = annual(ctry)
    summer = summer_share(ctry)
    assert eu["geo"].nunique() == 1
    assert summer.between(0, 100).all()
    assert summer.index.isin(ctry["geo"]).all()
    assert ctry["geo"].nunique() == 27
    assert tot.sum() == eu["nights"].sum()
    assert ctry["nights"].isna().sum() == 0
    # Top three countries by annual nights: France, Spain, Italy.
     # guess: top 3 = 60% of EU nights
    top3 = tot.head(3).sum()
    share = top3 / eu["nights"].sum() * 100
    print(f"Top 3 = {share:.1f}% of EU nights")
    # Angle A (scale): what share of EU nights are the top 3 countries?
    # Angle B (seasonality): summer_share(ctry), flattest vs. most summer-heavy
    # top country by summer share: 
    # guess: spain highest, germany flattest
    # real answer - Croatia Flattest: Luxembourg
    print(f"Top country by summer share: {summer.idxmax()}")
    print(f"Flattest country by summer share: {summer.idxmin()}")
    print(summer.head(3))   # flattest, in percent
    print(summer.tail(3))   # most summer-heavy, in percent
    print(tot.head(3))
    assert summer.idxmax() == "Croatia" and round(summer.max(), 1) == 57.0
    assert summer.idxmin() == "Luxembourg" and round(summer.min(), 1) == 21.6
    assert (summer > 2/12 * 100).all()      # even spread = 2/12 as a percent
    out = handoff(tot, summer)
    monthly_out = monthly(ctry)
    # 1. attach the per-country values the canvas needs
    monthly_out["annual_nights"] = monthly_out["geo"].map(tot)
    monthly_out["summer_rank"] = monthly_out["geo"].map(out.set_index("geo")["summer_rank"])

    # 2. anchors = the three called-out countries + the three largest by nights
    anchors = ANCHORS | set(tot.head(3).index)
    monthly_out["is_anchor"] = monthly_out["geo"].isin(anchors)
    assert len(monthly_out) == 27 * 12
    sums = monthly_out.groupby("geo")["share_pct"].sum()
    assert np.isclose(sums, 100).all()
    assert monthly_out.loc[monthly_out["is_anchor"], "geo"].nunique() == 5
    assert monthly_out["summer_rank"].between(1, 27).all()
    assert monthly_out["annual_nights"].between(0, 1e9).all()
    assert monthly_out["share_pct"].between(0, 100).all()
    assert len(out) == 27
    assert out["summer_rank"].iloc[0] == 1
    assert out["geo"].iloc[0] == "Croatia"
    assert out["geo"].iloc[-1] == "Luxembourg"
    rho, p = stats.spearmanr(out["annual_nights"], out["summer_pct"])
    top = monthly_out.loc[monthly_out["share_pct"].idxmax()]
    assert top["geo"] == "Croatia" and top["month"] == "August"
    print(f"rho = {rho:.2f}, p = {p:.2f}")
    assert set(tot.head(3).index) == {"France", "Spain", "Italy"}
    assert abs(rho) < 0.3
    monthly_out = monthly_out.sort_values(["summer_rank", "geo", "month_num"]).reset_index(drop=True)
    assert monthly_out["geo"].iloc[0] == "Croatia"
    assert (monthly_out["month_num"].iloc[:12] == range(1, 13)).all()
    paths_local.write_atomic(out, "euro_tourism_stage2.csv")
    paths_local.write_atomic(monthly_out, "euro_tourism_monthly_stage2.csv")  # 324 rows, new



if __name__ == "__main__":
    main()
