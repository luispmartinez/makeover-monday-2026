"""
explore PISA 2025
This file explores the PISA 2025 dataset and hands off subject findings,
country-level points, and regression confidence bands for the Tableau build.

"""


## explore_pisa_2025.py                       one numbering style: 0 to 6

# 0  CONFIG
import json, sys
from pathlib import Path
import pandas as pd
from scipy import stats
sys.path.insert(0, str(Path(__file__).parent.parent / "toolkit"))
from stage_helpers import write_atomic

HERE = Path(__file__).parent
SOURCE_FILE = HERE / "drop" / "PISA2025.xlsx"
OUT = Path.home() / "TableauData" / "wk44-pisa-2025"  # Set this to build_pisa_canvas.py's input folder
OUT.mkdir(parents=True, exist_ok=True)
KEY = ["Country"]
AI  = "Students using AI at least weekly to help them learn"
BANDS = [(0.70, "strong"), (0.40, "moderate"), (0.10, "weak"), (0.00, "none or very weak")]

def band(r):
    for floor, label in BANDS:
        if abs(r) >= floor:
            return label

assert band(0.095) == "none or very weak"
assert band(0.10)  == "weak"          # the floor itself belongs to the band above
assert band(-0.40) == "moderate"
assert band(0.699) == "moderate"
assert band(0.70)  == "strong"

SUBJECTS = {
    "Science": "Science mean score",
    "Reading": "Reading mean score",
    "Math": "Mathematics mean score",
    "Computational problem solving": "Computational problem solving mean score",
}
EXPECT_PAIRED_N = {
    "Science": 85,
    "Reading": 84,
    "Math": 84,
    "Computational problem solving": 85,
}

DETAIL_COLUMNS = [
    "Country",
    "Region",
    "Sampling caution",
    AI,
    "Science mean score",
    "Reading mean score",
    "Mathematics mean score",
    "Computational problem solving mean score",
    "Science change 2022-2025 (points)",
    "Reading change 2022-2025 (points)",
    "Mathematics change 2022-2025 (points)",
    "Top performers (Level 5-6) in at least one subject",
    "Low performers (below Level 2) in all three subjects",
    "Index of schools' capacity to use digital devices",
    "Students in schools where cell phones are not allowed",
    "Students in schools with subject-specific digital device guidelines",
]

assert len(set(DETAIL_COLUMNS)) == len(DETAIL_COLUMNS), "DETAIL_COLUMNS lists a column twice"

# 1  LOAD (once)                          item 1: one read, no repeat
df = pd.read_excel(SOURCE_FILE, sheet_name="PISA2025-Data", engine="openpyxl")  # item 1: one read, no repeat
ABOUT = pd.read_excel(SOURCE_FILE, sheet_name="About", header=None)          # section 1: load
ABOUT = ABOUT.dropna(subset=[0, 1])                     # keep only rows that have both a label and a text


# 2  SHAPE ASSERTS                        these stay
assert not df.duplicated(KEY).any()                         # one row per key
assert (df.groupby("Country")[["Region", "OECD member"]].nunique() == 1).all().all()   # each country has one region and one OECD flag
assert len(df) == 91, "About tab: 91 countries and economies"

no_ai = df.loc[df[AI].isna(), "Country"].tolist()
assert len(no_ai) == 6
assert set(no_ai) == {"Cambodia", "Dushanbe (Tajikistan)", "Kurdistan Region (Iraq)", "Mauritius", "Rwanda", "Zambia"}                   # the six, by name
assert AI in df.columns and all(column in df.columns for column in SUBJECTS.values())
assert tuple(EXPECT_PAIRED_N[subject] for subject in SUBJECTS) == tuple(
    len(df.dropna(subset=[AI, column])) for column in SUBJECTS.values()
), "Expect paired n for each subject"

SOURCE_NOTES = dict(zip(ABOUT[0], ABOUT[1]))

assert {"Source", "Tables used", "Licence"} <= set(SOURCE_NOTES)              # section 2: the rows we need exist
assert "doi.org" in SOURCE_NOTES["Source"]
assert "Table I." in SOURCE_NOTES["Tables used"]
assert "CC BY" in SOURCE_NOTES["Licence"]

# 3  LOOK                                 item 2: prints only, delete when locked
# nothing to see here, move along

# 4  FINDINGS
def band_edges(r):
    magnitude = abs(r)
    for i, (floor, _) in enumerate(BANDS):
        if magnitude >= floor:
            ceiling = BANDS[i - 1][0] if i else 1.0
            return [floor, ceiling]  # lower-inclusive; upper-exclusive

findings = {}
point_frames = []
fit_band_frames = []

for subject, score_column in SUBJECTS.items():
    sample = df.dropna(subset=[AI, score_column])
    no_us = sample[sample["Country"] != "United States"]

    result = stats.pearsonr(sample[AI], sample[score_column])
    result_no_us = stats.pearsonr(no_us[AI], no_us[score_column])
    ci = result.confidence_interval()
    ci_no_us = result_no_us.confidence_interval()
    fit = stats.linregress(sample[AI], sample[score_column])

    r = result.statistic
    crosses_zero = ci.low <= 0 <= ci.high
    se_r = (1 - r**2) / (len(sample) - 1) ** 0.5
    us_shift = 2 * se_r
    us_matters = bool(
        abs(r - result_no_us.statistic) >= us_shift
        or band(r) != band(result_no_us.statistic)
        or crosses_zero != (ci_no_us.low <= 0 <= ci_no_us.high)
    )

    findings[subject] = {
        "n": len(sample),
        "r": r,
        "interval": [ci.low, ci.high],
        "band": band(r),
        "direction": "none" if crosses_zero else ("negative" if r < 0 else "positive"),
        "slope": fit.slope,
        "intercept": fit.intercept,
        "band_edges": band_edges(r),
        "us_matters": us_matters,
    }

    point_frames.append(
        sample[["Country", "Region", "OECD member", "Sampling caution", AI, score_column]]
        .rename(columns={AI: "ai_use", score_column: "score"})
        .assign(subject=subject)
    )

    x = sample[AI].to_numpy(dtype=float)
    y = sample[score_column].to_numpy(dtype=float)
    x_grid = pd.Series(
        [x.min() + i * (x.max() - x.min()) / 100 for i in range(101)],
        name="ai_use",
    )
    x_mean = x.mean()
    sxx = ((x - x_mean) ** 2).sum()
    residual_se = (((y - (fit.intercept + fit.slope * x)) ** 2).sum() / (len(x) - 2)) ** 0.5
    t_critical = stats.t.ppf(0.975, len(x) - 2)
    fitted = fit.intercept + fit.slope * x_grid
    # Pointwise 95% confidence interval for the mean fitted score.
    margin = t_critical * residual_se * (
        1 / len(x) + (x_grid - x_mean) ** 2 / sxx
    ) ** 0.5
    fit_band_frames.append(
        pd.DataFrame(
            {
                "subject": subject,
                "ai_use": x_grid,
                "fitted_score": fitted,
                "lower_95_ci": fitted - margin,
                "upper_95_ci": fitted + margin,
            }
        )
    )

# 5  LOCK
assert set(findings) == set(SUBJECTS)
for subject, finding in findings.items():
    assert finding["n"] == EXPECT_PAIRED_N[subject]
    sample = df.dropna(subset=[AI, SUBJECTS[subject]])
    assert abs(
        finding["r"] - sample[[AI, SUBJECTS[subject]]].corr().iloc[0, 1]
    ) < 1e-9

assert {finding["direction"] for finding in findings.values()} == {"none"}

HEADLINE = {
    subject: {
        **finding,
        "r": round(finding["r"], 2),
        "interval": [round(value, 2) for value in finding["interval"]],
        "slope": round(finding["slope"], 4),
        "intercept": round(finding["intercept"], 4),
        "band_edges": [round(value, 2) for value in finding["band_edges"]],
    }
    for subject, finding in findings.items()
}

# 6  HANDOFF
write_atomic(OUT / "headline.json", json.dumps(HEADLINE, indent=2) + "\n")
assert json.loads((OUT / "headline.json").read_text()) == HEADLINE
POINTS = pd.concat(point_frames, ignore_index=True).reindex(
    columns=["subject", "Country", "Region", "OECD member", "Sampling caution", "ai_use", "score"]
)
assert POINTS["score"].notna().all() and POINTS["Country"].notna().all()   # check before writing
FIT_BANDS = pd.concat(fit_band_frames, ignore_index=True)

write_atomic(OUT / "points.csv", POINTS.to_csv(index=False))
POINTS_CHECK = pd.read_csv(OUT / "points.csv")
pd.testing.assert_frame_equal(POINTS_CHECK, POINTS, check_exact=False, rtol=1e-9)
assert POINTS_CHECK.groupby("subject").size().to_dict() == EXPECT_PAIRED_N

write_atomic(OUT / "fit_bands.csv", FIT_BANDS.to_csv(index=False))
FIT_BANDS_CHECK = pd.read_csv(OUT / "fit_bands.csv")
pd.testing.assert_frame_equal(FIT_BANDS_CHECK, FIT_BANDS, check_exact=False, rtol=1e-9)


assert set(FIT_BANDS_CHECK["subject"]) == set(SUBJECTS)
assert FIT_BANDS_CHECK.groupby("subject").size().eq(101).all()
assert (FIT_BANDS_CHECK["lower_95_ci"] <= FIT_BANDS_CHECK["upper_95_ci"]).all()

DETAILS = df[DETAIL_COLUMNS].copy()
write_atomic(OUT / "details.csv", DETAILS.to_csv(index=False))

DETAILS_CHECK = pd.read_csv(OUT / "details.csv")
pd.testing.assert_frame_equal(DETAILS_CHECK, DETAILS, check_exact=False, rtol=1e-9)
assert len(DETAILS_CHECK) == len(df)
assert DETAILS_CHECK["Country"].is_unique
assert {"Region", AI} <= set(DETAILS_CHECK.columns)
assert DETAILS_CHECK.loc[DETAILS_CHECK.Country == "Canada", "Region"].item() == "North America"
assert DETAILS_CHECK[AI].isna().sum() == 6          # the six with no AI data, by count




SOURCE_NOTES_OUT = {k: SOURCE_NOTES[k] for k in ("Source", "Tables used", "Licence")}     # 1. builds the dict (your line)

head, _, tail = SOURCE_NOTES["Licence"].partition(" Opinions")                             # 2. the new lines
assert tail and head.startswith("CC BY 4.0"), "licence text changed shape"
SOURCE_NOTES_OUT["Licence short"] = head.strip()

assert set(SOURCE_NOTES_OUT) == {"Source", "Tables used", "Licence", "Licence short"}      # 3. update this existing assert
assert all(isinstance(value, str) and value.strip() for value in SOURCE_NOTES_OUT.values())
assert "Opinions" not in SOURCE_NOTES_OUT["Licence short"] and "Opinions" in SOURCE_NOTES_OUT["Licence"]

write_atomic(OUT / "source_notes.json", json.dumps(SOURCE_NOTES_OUT, indent=2) + "\n")
SOURCE_NOTES_CHECK = json.loads((OUT / "source_notes.json").read_text())
assert SOURCE_NOTES_CHECK == SOURCE_NOTES_OUT

PARAM_VALUES = ["none"] + sorted(df["Country"], key=str.casefold)
assert len(PARAM_VALUES) == len(df) + 1 and len(set(PARAM_VALUES)) == len(PARAM_VALUES)
assert "none" not in {c.casefold() for c in df["Country"]}                  # the sentinel can't be a real country
write_atomic(OUT / "parameter_values.txt", "\n".join(PARAM_VALUES) + "\n")