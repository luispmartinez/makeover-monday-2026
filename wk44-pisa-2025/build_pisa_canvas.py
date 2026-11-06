# build_pisa_canvas.py  (Stage 3: canvas CSV, no analysis)

# 0  CONFIG
import json, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent.parent / "toolkit"))
from stage_helpers import write_atomic
from title_glyphs import TitleFont
import math

HERE = Path(__file__).parent
OUT  = Path.home() / "TableauData" / "wk44-pisa-2025"      # same folder Stage 2 wrote to
HEAD = json.loads((OUT / "headline.json").read_text())     # never retype a number

NOTES = json.loads((OUT / "source_notes.json").read_text())      # section 0, beside HEAD
assert {"Source", "Tables used", "Licence"} <= set(NOTES)
PTS  = pd.read_csv(OUT / "points.csv")                     
FIT_BANDS = pd.read_csv(OUT / "fit_bands.csv")             
W, H_PX = 1300, 805
DEG_PX  = 40   
MARGIN, GAP = 40, 40    
HEADER_H, FOOTER_H = 215, 50
PALETTE = {"bg": "0D0B12", "story": "E0243C", "context": "EDEAF2", 
           "faint": "8E8A99", "band": "37101A", "flag": "D9A441", "panel": "14111C", "grid": "24202F",
           "tick": "B4B0C0"}
SUBJECTS = ["Science", "Reading", "Math", "Computational problem solving"]  # 2x2 order
assert set(HEAD) == set(SUBJECTS)
assert {"subject", "Country", "Sampling caution", "ai_use", "score"} <= set(PTS.columns)
assert PTS.groupby("subject").size().to_dict() == {s: HEAD[s]["n"] for s in SUBJECTS}
GRID_N = 101                                   # must match Stage 2's grid
GRID_HALF = 0.5
assert FIT_BANDS.groupby("subject").size().eq(GRID_N).all()
for s in SUBJECTS:
    first = FIT_BANDS[FIT_BANDS.subject == s].sort_values("ai_use").iloc[0]
    assert abs(first.fitted_score - (HEAD[s]["intercept"] + HEAD[s]["slope"] * first.ai_use)) < 1e-3


TOOLKIT = HERE.parent / "toolkit"
FONT_FILE   = TOOLKIT / "fonts" / "Shrikhand-Regular.ttf"
BARLOW_FILE = TOOLKIT / "fonts" / "BarlowCondensed-Medium.ttf"

for f in (FONT_FILE, BARLOW_FILE):
    assert f.exists(), f"font missing: {f}"
PANEL_TITLE_PX, KEY_PX, PANEL_PAD_TOP = 14, 12, 10

DETAILS = pd.read_csv(OUT / "details.csv")
assert len(DETAILS) == 91 and DETAILS["Country"].is_unique
assert set(PTS["Country"]) <= set(DETAILS["Country"])

# 1  LAYOUT: constants only, so a spacing change is one edit
PANEL_W = (W - 2 * MARGIN -  GAP) / 2
PANEL_H = (H_PX - HEADER_H - FOOTER_H - GAP) / 2 # one gap between panels, one gap above footer

PANEL_X0 = [MARGIN, MARGIN + PANEL_W + GAP]
PANEL_Y0 = [HEADER_H, HEADER_H + PANEL_H + GAP]
assert PANEL_Y0[1] + PANEL_H == H_PX - FOOTER_H     # the bottom-up check

assert 2 * PANEL_W + GAP + 2 * MARGIN == W
assert 2 * PANEL_H + GAP + HEADER_H + FOOTER_H == H_PX

TICK_PX, TICK_GAP, TICK_EDGE = 12, 6, 6          # label size, gap to the gridline, clearance from the panel edge
# 1  LAYOUT (add)
TITLE_H, AXIS_H = 34, 26                  # px inside each panel; tune in a preview
PAD_L, PAD_R = 30, 16                     # left holds the y labels, right keeps the old padding
X_TITLE = "AI use, % of students"

DOT_R = 3.5
LINE_HALF = 1.0
SAMPLING_NOTE = {"Yes": "OECD sampling caution: standards not fully met", "No": "No sampling caution flagged"}
FOOT_PX, FOOT_LEAD, FOOT_TOP_PAD = 12, 16, 10

CARD_W, CARD_H, CARD_PAD = 400, 450, 20
CARD_X = (W - CARD_W) / 2
CARD_Y = HEADER_H + (H_PX - HEADER_H - FOOTER_H - CARD_H) // 2
CARD_NAME_PX = 20

assert CARD_X >= MARGIN and CARD_X + CARD_W <= W - MARGIN
assert CARD_Y >= HEADER_H and CARD_Y + CARD_H <= H_PX - FOOTER_H


S, B = 4, 1                                      # card shadow offset, border width

NON_ENDORSE = "Independent analysis, not an OECD product."
CREDIT_LEAD, CREDIT_NAME, CREDIT_PX, CREDIT_SHADOW = "Created by ", "Luis Pablo Martinez", 18, 2
CREDIT_LEAD_DROP = 4          # px below the name's baseline; try 3 or 4 if it still looks high

# 2  HELPERS: reuse from build_us_pop_canvas.py until glyph_helpers.py exists
rows = []                                  # every helper appends dicts here; one DataFrame at the end
LAYERS = ("back", "grid", "band", "data", "text", "cardframe", "cardname", "closebtn")           # section 2, in the `line` helper's allowed set

def line(key, xs, ys, layer, **cols):
    """Any polygon or path: one row per vertex. poly_id = key; point_order counts from 1."""
    assert layer in LAYERS, f"{key}: unknown layer {layer!r}"
    assert len(xs) == len(ys) >= 1
    for order, (x, y) in enumerate(zip(xs, ys), start=1):
        rows.append(dict(layer=layer, poly_id=key, point_order=order, x_px=x, y_px=y, **cols))

line("test", [0, 10, 10], [0, 0, 10], "back")
assert len(rows) == 3 and rows[0]["point_order"] == 1 and rows[2]["x_px"] == 10
rows.clear()

def rect(key, x0, y0, x1, y1, layer, **cols):
    """Four corners, clockwise from the top-left, as one polygon."""
    line(key, [x0, x1, x1, x0], [y0, y0, y1, y1], layer, **cols)

rect("t", 2, 3, 12, 8, "back")
assert len(rows) == 4
assert (rows[1]["x_px"], rows[1]["y_px"]) == (12, 3)      # top-right
assert (rows[2]["x_px"], rows[2]["y_px"]) == (12, 8)      # bottom-right
rows.clear()

def disc(key, cx, cy, r, layer, n=20, **cols):
    """A circle as n corners."""
    angles = [2 * math.pi * k / n for k in range(n)]
    line(key, [cx + r * math.cos(a) for a in angles], [cy + r * math.sin(a) for a in angles], layer, **cols)

disc("t", 100, 50, 10, "data")
assert len(rows) == 20
assert (min(r["x_px"] for r in rows), max(r["x_px"] for r in rows)) == (90, 110)
rows.clear()

def glyph_rows(font, key, txt, x, base, px, layer, tracking=0.0, align="left", **cols):
    wd = font.width(txt, px, tracking)
    x0 = {"left": x, "right": x - wd, "center": x - wd / 2}[align]
    for rid, pts in font.rings(txt, x0, base, px, tracking):
        line(f"{layer}:{key}:{rid}", [p[0] for p in pts], [p[1] for p in pts], layer, **cols)


SHRIKHAND = TitleFont(FONT_FILE, steps= 2)           # fewer curve steps, fewer rows
glyph_rows(SHRIKHAND, "t", "I", 100, 200, 68, "text", color="FFFFFF")
BARLOW = TitleFont(BARLOW_FILE, steps=1)
assert len({r["poly_id"] for r in rows}) == 1       # "I" has no counter: one ring
rows.clear()

def star(key, cx, cy, r, layer, **cols):
    """Four-point sparkle: 8 corners, alternating the long reach and a short reach."""
    pts = []
    for k in range(8):
        a = math.pi / 4 * k - math.pi / 2                 # start at the top, go clockwise
        reach = r if k % 2 == 0 else 0.2 * r              # short reach: about a fifth of the long one
        pts.append((cx + reach * math.cos(a), cy + reach * math.sin(a)))
    line(key, [p[0] for p in pts], [p[1] for p in pts], layer, **cols)

star("t", 100, 100, 10, "back", color="FFFFFF")
assert len(rows) == 8
assert (round(min(r["y_px"] for r in rows), 6), round(max(r["y_px"] for r in rows), 6)) == (90, 110)
rows.clear()

STAR_PAD = 5                                             # clear space around each star, px
def boxes_overlap(a, b, pad=0):
    """Boxes are (left, top, right, bottom). True if they come within `pad` of each other."""
    return not (a[2] + pad < b[0] or b[2] + pad < a[0] or a[3] + pad < b[1] or b[3] + pad < a[1])

assert boxes_overlap((0, 0, 10, 10), (5, 5, 15, 15))
assert not boxes_overlap((0, 0, 10, 10), (30, 30, 40, 40), pad=5)

def nice_ticks(lo, hi, step):
    """Multiples of `step` inside [lo, hi], in order."""
    first, last = math.ceil(lo / step), math.floor(hi / step)
    return [round(k * step, 10) for k in range(first, last + 1)]

assert nice_ticks(0.259, 0.686, 0.1) == [0.3, 0.4, 0.5, 0.6]
assert nice_ticks(273, 617, 100) == [300, 400, 500, 600]
assert nice_ticks(5, 6, 10) == []

# 3  LAYERS (one list of rows each; every row has layer, poly_id, point_order, x, y, color, tip)


# 4  BUILD
# 4a  scales, written once, shared by every panel
Y_PAD = 5                                            # one number, one edit moves every panel

y_lo, y_hi = PTS.score.min() - Y_PAD, PTS.score.max() + Y_PAD
X_PAD = 0.01                                    # in AI-share units; 0.01 is about 13 px on this plot
x_lo, x_hi = PTS.ai_use.min() - X_PAD, PTS.ai_use.max() + X_PAD

Y_TICKS = nice_ticks(y_lo, y_hi, 100)
X_TICKS = nice_ticks(x_lo, x_hi, 0.1)
assert len(Y_TICKS) >= 2 and len(X_TICKS) >= 2, "too few ticks to label the axes"
assert max(BARLOW.width(str(t), TICK_PX) for t in Y_TICKS) + TICK_GAP + TICK_EDGE <= PAD_L, "y labels don't fit the left pad"
def plot_box(panel):
    """Inner plot rectangle (left, top, right, bottom) in canvas pixels."""
    col, grid_row = panel % 2, panel // 2          # 0..3 -> (0,0) (1,0) (0,1) (1,1)
    x0, y0 = PANEL_X0[col], PANEL_Y0[grid_row]
    return x0 + PAD_L, y0 + TITLE_H, x0 + PANEL_W - PAD_R, y0 + PANEL_H - AXIS_H


def px(panel, ai, score):
    left, top, right, bottom = plot_box(panel)
    return left + (ai - x_lo) / (x_hi - x_lo) * (right - left), top + (y_hi - score) / (y_hi - y_lo) * (bottom - top)

left, top, right, bottom = plot_box(0)
assert px(0, x_lo, y_lo)[1] == bottom            # lowest score sits at the bottom edge
assert abs(px(0, x_hi, y_hi)[0] - right) < 1e-9             # highest AI share sits at the right edge
assert plot_box(1)[0] > plot_box(0)[2]           # panel 1 starts right of panel 0's plot box
assert plot_box(2)[1] > plot_box(0)[3]           # panel 2 starts below panel 0's plot box
# 4b  back layer: frame per panel

for i, subject in enumerate(SUBJECTS):
    col, grid_row = i % 2, i // 2
    rect(f"frame:{subject}", PANEL_X0[col], PANEL_Y0[grid_row], PANEL_X0[col] + PANEL_W, PANEL_Y0[grid_row] + PANEL_H, "back", color=PALETTE["panel"])
for i, subject in enumerate(SUBJECTS):
    left, top, right, bottom = plot_box(i)
    for t in Y_TICKS:
        _, y = px(i, x_lo, t)
        rect(f"grid:{subject}:y{t}", left, y - GRID_HALF, right, y + GRID_HALF, "grid", color=PALETTE["grid"])
        
g = pd.DataFrame(rows)
g = g[g.layer == "grid"]
assert g.poly_id.nunique() == len(SUBJECTS) * len(Y_TICKS)
for i, subject in enumerate(SUBJECTS):
    left, top, right, bottom = plot_box(i)
    gi = g[g.poly_id.str.startswith(f"grid:{subject}:")]
    assert len(gi) > 0
    assert gi.x_px.between(left, right).all()
    assert gi.y_px.between(top, bottom).all()


for i, subject in enumerate(SUBJECTS):
    left, top, right, bottom = plot_box(i)
    for t in Y_TICKS:
        _, y = px(i, x_lo, t)
        glyph_rows(BARLOW, f"ytick:{subject}:{t}", str(t), left - TICK_GAP, y + TICK_PX * BARLOW.cap / 2, TICK_PX, "text", align="right", color=PALETTE["tick"])
    for v in X_TICKS:
        x, _ = px(i, v, y_lo)
        glyph_rows(BARLOW, f"xtick:{subject}:{v}", f"{v:.0%}", x, bottom + TICK_GAP + TICK_PX * BARLOW.cap, TICK_PX, "text", align="center", color=PALETTE["tick"])
    last_right = px(i, X_TICKS[-1], y_lo)[0] + BARLOW.width(f"{X_TICKS[-1]:.0%}", TICK_PX) / 2
    assert right - BARLOW.width(X_TITLE, TICK_PX) - last_right >= TICK_GAP, f"{subject}: x title touches the last tick label"
    glyph_rows(BARLOW, f"xtitle:{subject}", X_TITLE, right, bottom + TICK_GAP + TICK_PX * BARLOW.cap, TICK_PX, "text", align="right", color=PALETTE["tick"])
    xt = pd.DataFrame(rows)
    xt = xt[xt.poly_id.str.contains(f":xtitle:{subject}:")]
    assert len(xt) > 0
    assert xt.x_px.between(left, right + 1e-6).all() and xt.y_px.between(bottom, PANEL_Y0[i // 2] + PANEL_H).all()
    
lab = pd.DataFrame(rows)
for i, subject in enumerate(SUBJECTS):
    left, top, right, bottom = plot_box(i)
    panel_x0, panel_y1 = PANEL_X0[i % 2], PANEL_Y0[i // 2] + PANEL_H
    yl = lab[lab.poly_id.str.contains(f":ytick:{subject}:")]
    assert len(yl) > 0
    assert yl.x_px.max() <= left - TICK_GAP + 1e-6          # ends at the gridline's left edge
    assert yl.x_px.min() >= panel_x0 + TICK_EDGE            # stays clear of the panel's edge
    assert yl.y_px.between(top, bottom).all()               # inside the plot's height
    xl = lab[lab.poly_id.str.contains(f":xtick:{subject}:")]
    assert len(xl) > 0
    assert xl.y_px.between(bottom, panel_y1).all()          # inside the strip under the plot

FLAG_COUNTS = PTS.loc[PTS["Sampling caution"].eq("Yes")].groupby("subject").size()
assert FLAG_COUNTS.nunique() == 1 and len(FLAG_COUNTS) == len(SUBJECTS)    # same count in every subject
FLAG_N = int(FLAG_COUNTS.iloc[0])
assert FLAG_N == 6                                                         # the report's six asterisks

# 4c  data layer, in this order so dots sit on top: band polygon, fit line, dots
#     band: upper edge forward, lower edge backward, from fit_bands.csv. id "band:<subject>"
#     fit line: first and last row of fit_bands.csv fitted_score. id "fit:<subject>"
#     dots: one disc per row of points.csv. id "pt:<subject>:<country>"
#     colour: flag if Sampling caution == "Yes", else context
for i, subject in enumerate(SUBJECTS):
    r, (lo_ci, hi_ci) = HEAD[subject]["r"], HEAD[subject]["interval"]
    fb = FIT_BANDS[FIT_BANDS.subject == subject].sort_values("ai_use")
    up = [px(i, a, s) for a, s in zip(fb.ai_use, fb.upper_95_ci)]
    lo = [px(i, a, s) for a, s in zip(fb.ai_use[::-1], fb.lower_95_ci[::-1])]
    pts = up + lo
    line(f"band:{subject}", [p[0] for p in pts], [p[1] for p in pts], "band", color=PALETTE["band"], tip=f"{subject}||95% confidence band for the fitted line||Where the average score likely sits at each AI share")
    (x0, y0) = px(i, fb.ai_use.iloc[0],  fb.fitted_score.iloc[0])
    (x1, y1) = px(i, fb.ai_use.iloc[-1], fb.fitted_score.iloc[-1])          # the last row
    line(f"fit:{subject}", [x0, x1, x1, x0], [y0 - LINE_HALF, y1 - LINE_HALF, y1 + LINE_HALF, y0 + LINE_HALF],
     "data", color=PALETTE["story"], tip=f"{subject}: fitted line||r = {r:.2f}||95% interval {lo_ci:.2f} to {hi_ci:.2f}. Direction supported: {HEAD[subject]['direction']}")
    

    # dots: flagged last, so gold sits on top of white
    sub = PTS[PTS.subject == subject].rename(columns={"Sampling caution": "flag"}).sort_values("flag")
    for d in sub.itertuples(index=False):
        cx, cy = px(i, d.ai_use, d.score)
        disc(f"pt:{subject}:{d.Country}", cx, cy, DOT_R, "data",
             color=PALETTE["flag"] if d.flag == "Yes" else PALETTE["context"],
             tip=f"{d.Country}||{d.ai_use:.0%} use AI weekly, score {d.score:.0f}||{SAMPLING_NOTE[d.flag]}",
             country=d.Country, subject=subject)

chk = pd.DataFrame(rows)

dots = chk[chk.layer.eq("data") & chk.poly_id.str.startswith("pt:")]

assert dots.x_px.min() >= plot_box(0)[0] and dots.x_px.max() <= max(plot_box(i)[2] for i in range(4))

# 1: dots per subject equal HEAD[subject]["n"]
# Each dot is stored as multiple vertex rows, so count unique polygon IDs.
dot_ids = dots["poly_id"].drop_duplicates()
assert {
    s: dot_ids[dot_ids.str.startswith(f"pt:{s}:")].nunique()
    for s in SUBJECTS
} == {s: HEAD[s]["n"] for s in SUBJECTS}

# 2: gold dots per subject all equal FLAG_N
flag_dot_ids = dots.loc[
    dots["color"].eq(PALETTE["flag"]), "poly_id"
].drop_duplicates()
flag_counts_by_subject = flag_dot_ids.str.split(":").str[1].value_counts().to_dict()
assert flag_counts_by_subject == {s: FLAG_N for s in SUBJECTS}
# 3: the gold-dot countries equal the countries with Sampling caution == "Yes" in points.csv
expected_flag_ids = {
    f"pt:{subject}:{country}"
    for subject, country in PTS.loc[
        PTS["Sampling caution"].eq("Yes"), ["subject", "Country"]
    ].itertuples(index=False, name=None)
}
assert set(flag_dot_ids) == expected_flag_ids

# 4d  text layer: panel titles from HEAD, header from TitleFont (Shrikhand), footnote

HEADLINE_TEXT = "More AI. Same Scores."             # placeholder; your Hemingway/Burnett line replaces it
KICKER = "MAKEOVER MONDAY · WEEK 44 · PISA 2025"
TITLE_PX = SHRIKHAND.fit([HEADLINE_TEXT], W - 2 * MARGIN, 100)
SHADOW = max(4, round(TITLE_PX * 0.06))
# baselines: each one is the previous one plus a gap plus the next line's cap height
KICKER_BASE = 40 + 19 * BARLOW.cap
TITLE_BASE  = KICKER_BASE + 24 + TITLE_PX * SHRIKHAND.cap
SUB_BASE    = TITLE_BASE + SHADOW + 24 + 24 * BARLOW.cap
assert SUB_BASE + 6 < HEADER_H                       # the subtitle's descenders stay above the first panel row

N_MAX = max(HEAD[s]["n"] for s in SUBJECTS)
FEWER = [s for s in SUBJECTS if HEAD[s]["n"] < N_MAX]            # subjects with a smaller count: Reading and Math
N_FEWER = sorted({HEAD[s]["n"] for s in FEWER})                  # their counts: [84]

assert len(N_FEWER) <= 1, "subjects differ in more than one way; reword the subtitle by hand"
NAMES = " and ".join(FEWER)                                          # "Reading and Math"
FEWER_NOTE = f" ({N_FEWER[0]} in {NAMES})" if FEWER else ""          # " (84 in Reading and Math)", or nothing

SUBTITLE = f"Weekly AI use for learning vs mean score · {N_MAX} countries and economies{FEWER_NOTE} · country averages, not students"
assert BARLOW.width(SUBTITLE, 24) <= W - 2 * MARGIN, "subtitle too wide"


KICK_TRACK = 1.5
glyph_rows(BARLOW, "kicker", KICKER, MARGIN, KICKER_BASE, 19, "text", tracking=KICK_TRACK, color=PALETTE["flag"])
glyph_rows(SHRIKHAND, "title_shadow", HEADLINE_TEXT, MARGIN + SHADOW, TITLE_BASE + SHADOW, TITLE_PX, "back", color=PALETTE["story"])
glyph_rows(SHRIKHAND, "title", HEADLINE_TEXT, MARGIN, TITLE_BASE, TITLE_PX, "text", color=PALETTE["context"])
glyph_rows(BARLOW, "sub", SUBTITLE, MARGIN, SUB_BASE, 24, "text", color=PALETTE["faint"])
assert BARLOW.width(KICKER, 19, KICK_TRACK) <= W - 2 * MARGIN, "kicker too wide"

chk = pd.DataFrame(rows)

print(chk.shape)
print(chk.layer.value_counts().to_dict())
shadow = chk.poly_id.str.contains("title_shadow")
title  = chk.poly_id.str.contains(":title:")
assert shadow.any() and title.any()
assert shadow.sum() == title.sum()                    # same string, same number of vertices
assert chk.loc[shadow, "layer"].eq("back").all()
assert chk.loc[title, "layer"].eq("text").all()

for i, subject in enumerate(SUBJECTS):
    col, grid_row = i % 2, i // 2
    x0, y0 = PANEL_X0[col], PANEL_Y0[grid_row]
    base = y0 + PANEL_PAD_TOP + PANEL_TITLE_PX * BARLOW.cap        # cap height again
    assert base + 4 < y0 + TITLE_H                                    # the title stays inside its strip
    glyph_rows(BARLOW, f"ptitle:{subject}", f"{subject} mean score · r = {HEAD[subject]['r']:.2f}", x0 + PAD_L, base, PANEL_TITLE_PX, "text", color=PALETTE["context"])
    



KEY_TEXT = f"OECD sampling caution ({FLAG_N} countries)"
x_right  = plot_box(0)[2]
key_base = PANEL_Y0[0] + PANEL_PAD_TOP + PANEL_TITLE_PX * BARLOW.cap    # same baseline as the Science title
glyph_rows(BARLOW, "key", KEY_TEXT, x_right, key_base, KEY_PX, "text", align="right", color=PALETTE["faint"])
disc("text:key:dot", x_right - BARLOW.width(KEY_TEXT, KEY_PX) - 10, key_base - KEY_PX * BARLOW.cap / 2, DOT_R, "text", color=PALETTE["flag"])


kk = pd.DataFrame(rows)
kk = kk[kk.poly_id.str.contains(":key:")]
assert len(kk) > 0
assert kk.y_px.between(PANEL_Y0[0], PANEL_Y0[0] + TITLE_H).all()
assert kk.x_px.between(PANEL_X0[0], PANEL_X0[0] + PANEL_W).all()

tt = pd.DataFrame(rows)
for i, subject in enumerate(SUBJECTS):
    col, grid_row = i % 2, i // 2
    t = tt[tt.poly_id.str.contains(f":ptitle:{subject}:")]
    assert len(t) > 0
    assert t.y_px.between(PANEL_Y0[grid_row], PANEL_Y0[grid_row] + TITLE_H).all()
    assert t.x_px.between(PANEL_X0[col], PANEL_X0[col] + PANEL_W).all()

FOOT_1 = f"Source: {NOTES['Source']} {NOTES['Tables used']}"
FOOT_2 = f"{NOTES['Licence short']} {NON_ENDORSE} Shaded band: 95% confidence range for the average, not where most countries fall."
assert "Opinions" not in FOOT_1 + FOOT_2

foot_base1 = H_PX - FOOTER_H + FOOT_TOP_PAD + FOOT_PX * BARLOW.cap
foot_base2 = foot_base1 + FOOT_LEAD
assert foot_base2 + 4 < H_PX                                       # the second line stays on the canvas
glyph_rows(BARLOW, "foot1", FOOT_1, MARGIN, foot_base1, FOOT_PX, "text", color=PALETTE["faint"])
glyph_rows(BARLOW, "foot2", FOOT_2, MARGIN, foot_base2, FOOT_PX, "text", color=PALETTE["faint"])
ff = pd.DataFrame(rows)
ff = ff[ff.poly_id.str.contains(":foot")]
assert len(ff) > 0
assert ff.y_px.between(H_PX - FOOTER_H, H_PX).all()
assert ff.x_px.between(MARGIN, W - MARGIN).all()

name_w = SHRIKHAND.width(CREDIT_NAME, CREDIT_PX)
credit_right = W - MARGIN - CREDIT_SHADOW
assert BARLOW.width(FOOT_2, FOOT_PX) + 24 + BARLOW.width(CREDIT_LEAD, FOOT_PX) + name_w <= W - 2 * MARGIN, "credit collides with the footnote"
glyph_rows(SHRIKHAND, "credit_shadow", CREDIT_NAME, credit_right + CREDIT_SHADOW, foot_base2 + CREDIT_SHADOW, CREDIT_PX, "back", align="right", color=PALETTE["story"])
glyph_rows(SHRIKHAND, "credit_name", CREDIT_NAME, credit_right, foot_base2, CREDIT_PX, "text", align="right", color=PALETTE["context"])


lead_base = foot_base2 + CREDIT_LEAD_DROP                    # sit on the shadow's baseline, so the two read as one line
glyph_rows(BARLOW, "credit_lead", CREDIT_LEAD, credit_right - name_w - 4, lead_base, FOOT_PX, "text", align="right", color=PALETTE["faint"])
cr = pd.DataFrame(rows); cr = cr[cr.poly_id.str.contains(":credit_")]
assert cr.poly_id.str.contains("credit_shadow").sum() == cr.poly_id.str.contains("credit_name").sum() > 0
assert cr.y_px.between(H_PX - FOOTER_H, H_PX).all() and cr.x_px.between(MARGIN, W - MARGIN).all()

# 4e  sparkles, positioned from the header's measured width
title_w   = SHRIKHAND.width(HEADLINE_TEXT, TITLE_PX)
title_box = (MARGIN, TITLE_BASE - TITLE_PX * SHRIKHAND.cap, MARGIN + title_w + SHADOW, TITLE_BASE + SHADOW)
kicker_box = (MARGIN, KICKER_BASE - 19 * BARLOW.cap, MARGIN + BARLOW.width(KICKER, 19, KICK_TRACK), KICKER_BASE + 3)
# Header boxes are (left, top, right, bottom).
subtitle_box = (
    MARGIN,
    SUB_BASE - 24 * BARLOW.cap,
    MARGIN + BARLOW.width(SUBTITLE, 24),
    SUB_BASE + 6,
)
RAD_MAX = 10
band = (kicker_box[2] + STAR_PAD + RAD_MAX, MARGIN + RAD_MAX, W - MARGIN - RAD_MAX, title_box[1] - STAR_PAD - RAD_MAX)
assert band[2] - band[0] > 0 and band[3] - band[1] > 0, "no room for sparkles above the title"

HERO_U, HERO_V, HERO_R = 0.86, 0.45, 10             # fractions of the band; u near the right end, say 0.8 to 0.9
SATELLITES = [                                    # (dx, dy, rad), pixels from the hero's centre
    (-34, 5, 6),
    (18, -4, 5),
    (-92, -2, 4),
]
SPECKS = [(40, 6, 2), (-16, -8, 2)]           # same offsets idea, smallest radius

assert 0 <= HERO_U <= 1 and 0 <= HERO_V <= 1 and 0 < HERO_R <= RAD_MAX


hero_cx = band[0] + HERO_U * (band[2] - band[0])
hero_cy = band[1] + HERO_V * (band[3] - band[1])
STARS = [(hero_cx, hero_cy, HERO_R)] + [(hero_cx + dx, hero_cy + dy, rad) for dx, dy, rad in SATELLITES + SPECKS]
assert len(STARS) == 1 + len(SATELLITES) + len(SPECKS)
assert STARS[0][2] == HERO_R

SAT_PAD = 1  # Smaller than STAR_PAD: stars may sit closer to one another than to text.

for i, (cx, cy, rad) in enumerate(STARS):
    star_box = (cx - rad, cy - rad, cx + rad, cy + rad)
    for label, box in (("kicker", kicker_box), ("title", title_box), ("subtitle", subtitle_box)):
        assert not boxes_overlap(star_box, box, STAR_PAD), f"sparkle:{i} overlaps {label}"

    for j, (other_cx, other_cy, other_rad) in enumerate(STARS[:i]):
        other_box = (
            other_cx - other_rad,
            other_cy - other_rad,
            other_cx + other_rad,
            other_cy + other_rad,
        )
        assert not boxes_overlap(
            star_box, other_box, SAT_PAD
        ), f"sparkle:{i} too close to sparkle:{j}"

    assert star_box[0] >= MARGIN and star_box[2] <= W - MARGIN, f"sparkle:{i} outside horizontal margins"
    star(f"sparkle:{i}", cx, cy, rad, "back", color=PALETTE["context"])
    assert star_box[1] >= MARGIN, f"sparkle:{i} above the top margin"
    assert star_box[3] <= H_PX - MARGIN, f"sparkle:{i} below the bottom margin"
    assert star_box[3] <= HEADER_H, f"sparkle:{i} outside the header's vertical space"

sp = pd.DataFrame(rows)
sp = sp[sp.poly_id.str.startswith("sparkle:")]
assert sp.poly_id.nunique() == len(STARS)
assert sp.layer.eq("back").all()
assert sp.y_px.between(0, HEADER_H).all()
chk = pd.DataFrame(rows)

# fill, inset by the border
rect("cardframe:fill", CARD_X+B, CARD_Y+B, CARD_X+CARD_W-B, CARD_Y+CARD_H-B, "cardframe", color=PALETTE["panel"])
# four gold border strips
rect("cardframe:top",    CARD_X, CARD_Y, CARD_X+CARD_W, CARD_Y+B, "cardframe", color=PALETTE["flag"])
rect("cardframe:bottom", CARD_X, CARD_Y+CARD_H-B, CARD_X+CARD_W, CARD_Y+CARD_H, "cardframe", color=PALETTE["flag"])
rect("cardframe:left",   CARD_X, CARD_Y+B, CARD_X+B, CARD_Y+CARD_H-B, "cardframe", color=PALETTE["flag"])
rect("cardframe:right",  CARD_X+CARD_W-B, CARD_Y+B, CARD_X+CARD_W, CARD_Y+CARD_H-B, "cardframe", color=PALETTE["flag"])
# two crimson shadow strips, outside the card
rect("cardframe:sh_r", CARD_X+CARD_W, CARD_Y+S, CARD_X+CARD_W+S, CARD_Y+CARD_H+S, "cardframe", color=PALETTE["story"])
rect("cardframe:sh_b", CARD_X+S, CARD_Y+CARD_H, CARD_X+CARD_W, CARD_Y+CARD_H+S, "cardframe", color=PALETTE["story"])

# 4f  card names: one per country, all at the same spot; Tableau shows only the selected one
CARD_NAMES = sorted(DETAILS["Country"], key=str.casefold)
assert max(BARLOW.width(c, CARD_NAME_PX) for c in CARD_NAMES) <= CARD_W - 2 * CARD_PAD, "a name is wider than the card"
card_base = CARD_Y + CARD_PAD + CARD_NAME_PX * BARLOW.cap
for c in CARD_NAMES:
    glyph_rows(BARLOW, c, c, CARD_X + CARD_PAD, card_base, CARD_NAME_PX, "cardname", color=PALETTE["context"], country=c)
glyph_rows(BARLOW, "close", "Close ×", CARD_X + CARD_W - CARD_PAD, card_base, 16, "closebtn", align="right", color=PALETTE["flag"], country="none")
cb = pd.DataFrame(rows); cb = cb[cb.layer == "closebtn"]
assert len(cb) > 0 and cb.country.eq("none").all()
assert cb.x_px.between(CARD_X, CARD_X + CARD_W).all() and cb.y_px.between(CARD_Y, CARD_Y + CARD_H).all()
assert cb.poly_id.nunique() == 6 and len(cb) < 400        # one ring per glyph, each drawn once

cn = pd.DataFrame(rows)
cn = cn[cn.layer == "cardname"]
assert cn.country.nunique() == len(CARD_NAMES)
assert cn.x_px.between(CARD_X, CARD_X + CARD_W).all() and cn.y_px.between(CARD_Y, CARD_Y + CARD_H).all()


# 5  ASSERTS: before the conversion
canvas = pd.DataFrame(rows)                              # first line: the only build
rows_at_build = len(rows)

REQUIRED = [("back", "frame:"), ("grid", "grid:"), ("band", "band:"), ("data", "fit:"), ("data", "pt:"),
            ("text", "text:ptitle:"), ("text", "text:key:"), ("text", "text:xtick:"), ("text", "text:foot"),
            ("back", "sparkle:"), ("cardname", "cardname:"), ("closebtn", "closebtn:"),
            ("text", "text:credit_name"), ("text", "text:credit_lead"), ("back", "back:credit_shadow")]

for layer, prefix in REQUIRED:
    assert ((canvas.layer == layer) & canvas.poly_id.str.startswith(prefix)).any(), f"missing {layer}:{prefix}"

sizes = canvas.groupby(["layer", "poly_id"]).agg(w=("x_px", lambda s: s.max() - s.min()), h=("y_px", lambda s: s.max() - s.min()))
assert (sizes.w > 0).all() and (sizes.h > 0).all()      # no zero-width or zero-height shape
assert canvas.x_px.between(0, W).all() and canvas.y_px.between(0, H_PX).all()
assert canvas.loc[canvas.layer.isin(["band", "data"]), "tip"].str.count(r"\|\|").eq(2).all()
assert len(canvas) < 120_000



pts_rows = canvas[canvas.layer.eq("data") & canvas.poly_id.str.startswith("pt:")]
assert pts_rows.poly_id.nunique() == len(PTS)
assert pts_rows.country.notna().all() and pts_rows.subject.notna().all()
holders = canvas.index.isin(pts_rows.index) | canvas.layer.isin(["cardname", "closebtn"])
MUST_HAVE = {f"band:band:{s}" for s in SUBJECTS} | {f"data:fit:{s}" for s in SUBJECTS} | {f"back:frame:{s}" for s in SUBJECTS}
assert MUST_HAVE <= set(canvas["layer"] + ":" + canvas["poly_id"].astype(str))

assert canvas.loc[~holders, "country"].isna().all()


# 6  CONVERT then WRITE
assert len(rows) == rows_at_build                       # nothing was drawn after the section 5 snapshot

canvas["lon"] = (canvas.x_px - W / 2) / DEG_PX
canvas["lat"] = (H_PX / 2 - canvas.y_px) / DEG_PX

# two independent checks
assert ((canvas.lon * DEG_PX + W / 2) - canvas.x_px).abs().max() < 1e-9      # round trip, x
assert ((H_PX / 2 - canvas.lat * DEG_PX) - canvas.y_px).abs().max() < 1e-9   # round trip, y
assert canvas.lon.abs().max() <= W / 2 / DEG_PX + 1e-9 and canvas.lat.abs().max() <= H_PX / 2 / DEG_PX + 1e-9
assert canvas.lon.abs().max() < 180 and canvas.lat.abs().max() < 90          # what MAKEPOINT accepts

COLUMNS = ["layer", "poly_id", "point_order", "lat", "lon", "color", "tip", "country", "subject"]
out = canvas[COLUMNS].reset_index(drop=True)
write_atomic(OUT / "pisa_canvas.csv", out.to_csv(index=False))
check = pd.read_csv(OUT / "pisa_canvas.csv", dtype={"color": str})
pd.testing.assert_frame_equal(check, out, check_exact=False, rtol=1e-9)