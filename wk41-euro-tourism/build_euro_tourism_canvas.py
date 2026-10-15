"""
build_euro_tourism_canvas.py
Geometry for the Tableau heatmap + bars. Reads the two Stage 2 hand-off files,
writes ONE long CSV with a `layer` column. Tableau: MAKEPOINT(lat, lon) per layer.
"""
# 1 Load libraries
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import paths_local
from scipy import stats

# Layout constants, in sketch pixels (y grows DOWNWARD). Converted once in to_latlon().
CANVAS_W, CANVAS_H = 1300, 805
X0, COL_PITCH, CELL_W = 180, 40, 39        # 12 cols -> ends x=659; cells are wide rectangles
Y0, ROW_PITCH, CELL_H = 198, 20, 19        # 27 rows -> ends y=737
HEADER_Y = 184
BAR_X0, BAR_W, BAR_H, LABEL_GAP = 690, 280, 14, 6
NOTE_X = 1040
UNIT = 60
BIN_EDGES = [0, 4, 8.33, 12, 16, 20, 24, 30]     # 8.33 = an even calendar
SCALE = 3
HEADER_W, HEADER_H = 1300, 805


def rect(df, x, y, w, h):
    """Explode each row into 4 corner rows. x, y = top-left corner."""
    corners = [(0, 0), (1, 0), (1, 1), (0, 1)]   # around the rectangle, no crossing
    parts = []
    for order, (dx, dy) in enumerate(corners, start=1):
        p = df.copy()
        p["x_px"] = x + dx * w
        p["y_px"] = y + dy * h
        p["point_order"] = order
        parts.append(p)
    return pd.concat(parts, ignore_index=True)

def to_latlon(df):
    df["lon"] = df["x_px"] / UNIT
    df["lat"] = (CANVAS_H - df["y_px"]) / UNIT       # flip: pixels grow down, latitude grows up
    return df

def font(name, size):
    return ImageFont.truetype(str(paths_local.FONTS_DIR / name), size * SCALE)

def wrap(draw, text, f, max_w):
    lines, line = [], ""
    for word in text.split():
        trial = (line + " " + word).strip()
        if draw.textlength(trial, font=f) <= max_w:
            line = trial
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return lines

def put(text, fname, size, x, y, fill, max_w=None, step=None, shadow=None):
    f = font(fname, size)
    lines = wrap(draw, text, f, max_w * SCALE) if max_w else [text]
    for line in lines:
        if shadow:
            draw.text(((x + shadow[0]) * SCALE, (y + shadow[1]) * SCALE), line, font=f, fill=shadow[2])
        draw.text((x * SCALE, y * SCALE), line, font=f, fill=fill)
        y += step or size
    return y

TB_FONT = ImageFont.truetype(str(paths_local.FONTS_DIR / "OpenSans-Regular.ttf"), 1000)   # measured at 1000, scaled down
TB_PX   = 12.35

def tb_w(text, bold=False):
    return TB_FONT.getlength(text) / 1000 * TB_PX * (1.035 if bold else 1.0)

# 2 Load data
monthly_out = pd.read_csv(paths_local.OUT / "euro_tourism_monthly_stage2.csv")
euro_tourism = pd.read_csv(paths_local.OUT / "euro_tourism_stage2.csv")

# 3 Row positions
anchors = set(monthly_out.loc[monthly_out["is_anchor"], "geo"])
rows = euro_tourism.sort_values(["summer_rank", "geo"]).reset_index(drop=True)
rows["row_idx"] = rows.index                         # 0..26. NOT summer_rank (Hungary/Slovakia tie)
rows["y_top"] = Y0 + rows["row_idx"] * ROW_PITCH
rows["is_anchor"] = rows["geo"].isin(anchors)
# Luxembourg: row_idx 26 -> y_top = 198 + 26 * 20 = 718; 718 + CELL_H = 737 < CANVAS_H = 805

# 4 Cell geometry
cells = monthly_out.merge(rows[["geo", "y_top"]], on="geo")
cells["x_left"] = X0 + (cells["month_num"] - 1) * COL_PITCH
cells["poly_id"] = cells["geo"] + "|" + cells["month_num"].astype(str)
cells = rect(cells, cells["x_left"], cells["y_top"], CELL_W, CELL_H)
cells["layer"] = "cell"

# 5 Cell colors
cells["color_step"] = pd.cut(cells["share_pct"], bins=BIN_EDGES, labels=range(len(BIN_EDGES)-1), include_lowest=True)
assert cells["color_step"].notna().all()
cells["color_step"] = cells["color_step"].astype(int)
# 5b Cell tooltips (after step 5, before the concat in step 9)
cells["tooltip"] = (cells["geo"] + ", " + cells["month"].astype(str) + ": "
                    + cells["share_pct"].round(1).astype(str)
                    + "% of its 2025 platform nights")

# 6 Non-data layers (row names + month header)
names = rows[["geo", "is_anchor", "y_top"]].copy()
NAME_RIGHT = X0 - 12    # row names right-aligned to this edge
names["x_px"] = NAME_RIGHT - names.apply(lambda r: tb_w(r["geo"], r["is_anchor"]), axis=1) / 2                        # right-aligned to NAME_RIGHT
names["y_px"] = names["y_top"] + CELL_H / 2
names["text"] = names["geo"]
names["layer"], names["point_order"] = "row_name", 1
# Luxembourg row name y_px = 718 + 19 / 2 = 727.5
# luxembourg (canvas_h - y_px)/UNIT = (805 - 727.5)/60 = 1.2917 latitude

hdr = pd.DataFrame({"month_num": range(1, 13)})
hdr["x_px"] = X0 + (hdr["month_num"] - 1) * COL_PITCH + CELL_W / 2
hdr["y_px"] = HEADER_Y
hdr["text"] = list("JFMAMJJASOND")
hdr["is_anchor"] = hdr["month_num"].isin([7, 8])     # bold the two summer months
hdr["layer"], hdr["point_order"] = "month_header", 1

# 7 Bars (one shared scale; France = full width)
rows["bar_w"] = rows["annual_nights"] / rows["annual_nights"].max() * BAR_W
bars = rows[["geo", "is_anchor", "annual_nights", "bar_w", "y_top"]].copy()
bars["poly_id"] = bars["geo"]
bars = rect(bars, BAR_X0, bars["y_top"] + (CELL_H - BAR_H) / 2, bars["bar_w"], BAR_H)
bars["layer"] = "bar"

# 7b Bar tooltips (after the bars are built in step 7)
bars["tooltip"] = (bars["geo"] + ": "
                   + (bars["annual_nights"] / 1e6).round(1).astype(str)
                   + "M guest nights booked via platforms, 2025")

lab = rows.loc[rows["is_anchor"], ["geo", "annual_nights", "bar_w", "y_top"]].copy()
lab["x_px"] = BAR_X0 + lab["bar_w"] + LABEL_GAP
lab["y_px"] = lab["y_top"] + CELL_H / 2
lab["text"] = (lab["annual_nights"] / 1e6).round(1).astype(str) + "M"
lab["layer"], lab["point_order"] = "bar_label", 1
lab["x_px"]   = BAR_X0 + lab["bar_w"] + LABEL_GAP + lab["text"].map(tb_w) / 2   # left-aligned after the bar

# 8 Margin notes (editorial text lives here; asserts guard every claim)
spain_peak = monthly_out.loc[monthly_out["geo"] == "Spain", "share_pct"].max()
NOTES = {
    "Croatia": "Two peaks, two shoulders, eight quiet",
    "Spain": f"Peak month: {spain_peak:.0f}% of its year",
    "Luxembourg": "Evenly lit all year",
}

even = 100 / 12
cro = monthly_out[monthly_out["geo"] == "Croatia"].set_index("month_num")["share_pct"]
assert set(cro.nlargest(2).index) == {7, 8}              # two peaks: July, August
assert set(cro[cro >= even].index) == {6, 7, 8, 9}       # two shoulders: June, September
assert (cro < even).sum() == 8                        # eight quiet months, below an even share
assert cro[cro < even].max() <  6                   # and they stay well clear of the shoulders
lux = monthly_out.loc[monthly_out["geo"] == "Luxembourg", "share_pct"]
assert lux.max() < 1.5 * even                            # "evenly lit": no month above 1.5x an even share

frame = pd.DataFrame({"x_px": [0, CANVAS_W], "y_px": [0, CANVAS_H]})
frame["layer"], frame["point_order"] = "frame", 1
frame["poly_id"] = ["frame|0", "frame|1"]

recs = []
for geo, line in NOTES.items():
    y_top = rows.loc[rows["geo"] == geo, "y_top"].iloc[0]
    recs.append({"geo": geo, "text": line, "y_px": y_top + CELL_H / 2,
                 "layer": "note", "point_order": 1})
notes = pd.DataFrame(recs)
notes["x_px"] = NOTE_X + notes["text"].map(tb_w) / 2

rho, p = stats.spearmanr(euro_tourism["annual_nights"], euro_tourism["summer_pct"])
assert abs(rho) < 0.3                        # the headline claim: size does not predict the share
print(f"rho = {rho:.2f}, p = {p:.2f}")

# 9 Checks
canvas = pd.concat([cells, names, hdr, bars, lab, notes, frame], ignore_index=True)
canvas = to_latlon(canvas)
assert canvas[["lat", "lon"]].notna().all().all()
assert canvas["lat"].between(-90, 90).all() and canvas["lon"].between(-180, 180).all()
assert canvas["x_px"].between(0, CANVAS_W).all()
assert canvas["y_px"].between(0, CANVAS_H).all()
tt_layers = canvas["layer"].isin(["cell", "bar"])
assert canvas.loc[tt_layers, "tooltip"].notna().all()
assert canvas.loc[~tt_layers, "tooltip"].isna().all()
c = canvas[canvas["layer"] == "cell"]
assert (c.groupby("poly_id")["point_order"].count() == 4).all()
assert c["poly_id"].nunique() == 324
assert canvas.loc[canvas["layer"] == "bar", "poly_id"].nunique() == 27
assert np.isclose(rows["bar_w"].max(), BAR_W)
assert 0 < rows.loc[rows["geo"] == "Luxembourg", "bar_w"].iloc[0] < 1
# guess on count of rows per layer: 27 rows * 12 months * 4 corners + 27 row names + 12 month headers + 27 bars * 4 corners + 5 bar labels + 3 notes + 2 frames = 1,453
assert len(canvas) == 1453                          # 1296 + 27 + 12 + 108 + 5 + 3 notes + 2 frames
assert (canvas["layer"] == "frame").sum() == 2
canvas[canvas["poly_id"] == "Croatia|8"][["point_order", "lon", "lat"]]
print(canvas[canvas["poly_id"] == "Croatia|8"][["point_order", "lon", "lat"]])
assert (NAME_RIGHT - names.apply(lambda r: tb_w(r["geo"], r["is_anchor"]), axis=1)).min() >= 0
print(canvas.loc[canvas["layer"] == "cell", "lon"].max())
assert (canvas["layer"] == "note").sum() == 3       # one note per country
assert (NOTE_X + notes["text"].map(tb_w)).max() <= CANVAS_W - 24     # note's right edge inside the margin

# 10 Export to CSV
COLS = ["layer", "geo", "poly_id", "point_order", "month_num", "text", "is_anchor",
        "share_pct", "annual_nights", "color_step", "lat", "lon", "tooltip"]
paths_local.write_atomic(canvas.reindex(columns=COLS), "euro_tourism_canvas.csv")
print(canvas["layer"].value_counts())

# 11 Header image
img  = Image.new("RGBA", (HEADER_W * SCALE, HEADER_H * SCALE), "#D9A23A")
draw = ImageDraw.Draw(img)

y = put("MAKEOVER MONDAY · WEEK 41 · EUROPEAN TOURISM",
        "BarlowCondensed-SemiBold.ttf", 15, 40, 20, "#5A2F8A")
y = put("SAME CONTINENT. TWO CALENDARS.",
        "Anton-Regular.ttf", 64, 40, y + 5, "#34195E", step=70, shadow=(4, 4, "#B06A74"))
y = put("Croatia puts 57% of its nights in two months. Luxembourg, 22%. "
        "Size does not predict which side a country lands on.",
        "BarlowCondensed-Medium.ttf", 21, 40, y +8, "#2A1A06", step=28)
y = put("Each row is a country. Each cell is a month: darker means a bigger share "
        "of that country's year. Bars show annual nights.",
        "BarlowCondensed-Medium.ttf", 21, 40, y, "#2A1A06", step=28)
put("Source: Eurostat, short-term rental nights booked through Airbnb, Booking and Expedia Group, "
    "2025. Makeover Monday 2026, week 41. EU-27 countries.",
    "BarlowCondensed-Medium.ttf", 14, 40, 746, "#2A1A06", max_w=1220)
y = put(f"Platform bookings only, not all tourist stays. Annual nights vs. July + August share across "
        f"27 countries: Spearman rho {rho:.2f}, p = {p:.2f}.",
        "BarlowCondensed-Medium.ttf", 14, 40, 762, "#2A1A06", max_w=1220)
y = put("Created by Luis Pablo Martinez",
        "BarlowCondensed-Medium.ttf", 14, 40, 778, "#2A1A06", max_w=1220)
assert y <= 805                              # footer stays on the canvas

img.save(paths_local.OUT / "euro_header.png")
print(img.size, y)