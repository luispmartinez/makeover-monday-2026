# build_turkey_canvas.py  (Stage 3: canvas CSV, no analysis)

#0 Config
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent.parent / "toolkit"))
from stage_helpers import write_atomic
from title_glyphs import TitleFont
import math

HERE = Path(__file__).parent
OUT  = Path.home() / "TableauData" / "minnesota-turkey"
CLEAN = OUT / "clean"

def blend(fg_hex, bg_hex, alpha):
    assert len(fg_hex) == 6 and len(bg_hex) == 6 and 0 <= alpha <= 1
    out = ""
    for i in (0, 2, 4):                                   # red, green, blue. in case we need to blend colors
        f = int(fg_hex[i:i + 2], 16)
        b = int(bg_hex[i:i + 2], 16)
        out += f"{round((alpha * f) + (b * (1 - alpha))):02X}"
    return out

assert blend("F3DFC4", "EBCBA6", 1.0) == "F3DFC4"
assert blend("F3DFC4", "EBCBA6", 0) == "EBCBA6"
assert blend("F3DFC4", "EBCBA6", 0.7) == "F1D9BB"


W, H_PX = 1387, 857
DEG_PX  = 40   
MARGIN, GAP = 40, 40    
HEADER_H, FOOTER_H = 190, 50
LABEL_PX  = 15
LABEL_GAP = 10

PALETTE = {"page": "EBCBA6", "ray_tint": "F3DFC4",
           "ink": "2A1C14", "soft": "6B563F", "names": "4A3626", "headline_accent": "9A3A0A",
           "beak": "E3A008",
           "Minnesota_dark_blue": "002C5A", "Minnesota_star": "FFFFFF", "Minnesota_light_blue": "74C6E4",
           "México_green":  "006847", "México_white": "FFFFFF", "México_red": "CE1126",
           "Canada": "D52B1E",
           "Rep._Dominicana_body": "002D62", "Rep._Dominicana_head": "CE1126",
           "Guatemala": "4997D0",
           "Costa_Rica_body": "002B7F", "Costa_Rica_head": "CE1126",
           "Panamá_body": "072357", "Panamá_head": "DA121A",
           "China_body": "DE2910", "China_head": "FFDE00",
           "Otros_1":"888780", "Otros_2":"B4B2A9", "Otros_3":"D3D1C7", 
}

PAGE = PALETTE["page"]

STACK = [
    ("ray_tint",                blend(PALETTE["ray_tint"],               PAGE, 0.7)),
    ("under_mexico_green",      blend(PALETTE["México_green"],           PAGE, 0.22)), ("under_mexico_white",      blend(PALETTE["México_white"],           PAGE, 0.22)), ("under_mexico_red",        blend(PALETTE["México_red"],             PAGE, 0.22)),
    ("under_canada",            blend(PALETTE["Canada"],                 PAGE, 0.22)), ("under_rep_dominicana",    blend(PALETTE["Rep._Dominicana_body"],   PAGE, 0.22)), 
    ("under_guatemala",         blend(PALETTE["Guatemala"],              PAGE, 0.22)), ("under_costa_rica",        blend(PALETTE["Costa_Rica_body"],        PAGE, 0.22)), 
    ("under_panama",            blend(PALETTE["Panamá_body"],            PAGE, 0.22)), ("under_china",             blend(PALETTE["China_body"],             PAGE, 0.22)), ("under_otros",             blend(PALETTE["Otros_1"],                PAGE, 0.22)),
    ("mn_field",                PALETTE["Minnesota_light_blue"],),      ("mn_bar", PALETTE["Minnesota_dark_blue"]),
    ("body_mexico_green",       PALETTE["México_green"]),               ("body_canada", PALETTE["Canada"]),                     ("body_dominicana",PALETTE["Rep._Dominicana_body"]), ("body_guatemala",PALETTE["Guatemala"]),
    ("body_costa_rica",         PALETTE["Costa_Rica_body"]),            ("body_panama", PALETTE["Panamá_body"]),                ("body_china",PALETTE["China_body"]), ("body_otros_1",PALETTE["Otros_1"]),
    ("body_mexico_red",         PALETTE["México_red"]),                 ("head_dominicana", PALETTE["Rep._Dominicana_head"]),   ("head_costa_rica",PALETTE["Costa_Rica_head"]),
    ("head_otros_2",            PALETTE["Otros_2"]),                    ("head_otros_3", PALETTE["Otros_3"]),
    ("head_panama",             PALETTE["Panamá_head"]),                ("head_china", PALETTE["China_head"]),
    ("body_mexico_white",       PALETTE["México_white"]),               ("mn_star", PALETTE["Minnesota_star"]),                 ("head_canada", PALETTE["México_white"]), ("head_guatemala", PALETTE["México_white"]),
    ("beak",                    PALETTE["beak"],                                    ),
    ("halo",                    PALETTE["page"],                                    ),
    ("soft",                    PALETTE["soft"],                                    ),
    ("names",                   PALETTE["names"],                                   ),
    ("ink",                     PALETTE["ink"],                                     ),
    ("headline_accent",         PALETTE["headline_accent"],                         ),
]
HEX = dict(STACK)
Z = {name: len(STACK) - i for i, (name, hex_) in enumerate(STACK)}
print(HEX["halo"], PALETTE["page"], len(set(HEX.values())))
z_table = pd.DataFrame({"color": [hex_ for name, hex_ in STACK],
                        "z":     [Z [name]for name, hex_ in STACK]})
span = z_table.groupby("color")["z"].agg(["min", "max"])
for color, (lo, hi) in span.iterrows():
    others = z_table[z_table["color"] != color]["z"]
    assert not others.between(lo, hi, inclusive="neither").any(), f"{color} is split"

TOOLKIT = HERE.parent / "toolkit"
ANTON_FILE   = TOOLKIT / "fonts" / "Anton-Regular.ttf"
BARLOW_FILE = TOOLKIT / "fonts" / "BarlowCondensed-Medium.ttf"

for f in (ANTON_FILE, BARLOW_FILE):
    assert f.exists(), f"font missing: {f}"

HEADLINE_FONT = TitleFont(ANTON_FILE, steps=2)
BARLOW = TitleFont(BARLOW_FILE, steps=1)

HEADLINE = "$73.8 million worth of turkeys trot from Minnesota to Mexico"

LABELS   = ["México", "Canadá", "Rep. Dominicana", "Guatemala", "Costa Rica", "Panamá", "China", "Otros"]

SUBTITLE = "Minnesota's $104M in turkey exports, by destination. Ribbon thickness = dollars"
assert BARLOW.width(SUBTITLE, 24) <=  W - 2 * MARGIN, "subtitle too wide"
FOOTER = "Source: Minnesota turkey fact sheet."
KICKER = "MAKEOVER MONDAY · WEEK 46 · MINNESOTA TURKEYS"
NUMERALS = ["$73.84M", "$4.16M", "$2.08M", "$15.6M"]

def assert_glyphs(font, text, name):
    """Every character of `text` must have a glyph in `font`."""
    for ch in text:
        assert ord(ch) in font.cmap, f"{name}: no glyph for {ch!r} in {text!r}"

assert_glyphs(HEADLINE_FONT, HEADLINE, "headline")

for text in (" ".join(LABELS), SUBTITLE, FOOTER, KICKER):          # labels, subtitle, footer, kicker
    assert_glyphs(BARLOW, text, "barlow")
    
# widths: same pattern as the subtitle
KICK_TRACK = 1.5                      # wk45's kicker tracking
KICKER_PX, FOOT_PX = 19, 12           # wk45's sizes
assert BARLOW.width(KICKER, KICKER_PX, KICK_TRACK) <= W - 2 * MARGIN, "kicker too wide"
assert BARLOW.width(FOOTER, FOOT_PX) <= W - 2 * MARGIN, "footer too wide"

# the headline's numbers come from the data
exports = pd.read_csv(CLEAN / "mn_exports.csv")
VALUE = "Estimated Export Value (USD)"
assert exports[VALUE].sum() == 104000000                        # the $104M total
mex = exports.loc[exports["Market / Country"] == "Mexico"].iloc[0]
assert round(mex[VALUE] / 1e6, 1) == 73.8                  # the 73.8 in HEADLINE
assert round(mex["Market Share (%)"], 2) == 0.71           # the 71%

TITLE_PX = HEADLINE_FONT.fit([HEADLINE], W - 2 * MARGIN, 100)
assert HEADLINE_FONT.width(HEADLINE, TITLE_PX) <= W - 2 * MARGIN

print(TITLE_PX)

REGION = {"Costa Rica": "Central America", "Guatemala": "Central America", "Panama": "Central America", "Dominican Republic": "Caribbean", "China": "Asia"}
REGION_ORDER = ["Central America", "Caribbean", "Asia"]
TRANSLATE = {
    "Mexico": "México", "Canada": "Canadá", "Dominican Republic": "Rep. Dominicana", "Panama": "Panamá", "All other": "Otros", "China": "China", "Guatemala": "Guatemala", "Costa Rica": "Costa Rica"
    }
assert set(REGION.values()) <= set(REGION_ORDER)
assert set(REGION) == set(exports.loc[exports["Rank"] == 3, "Market / Country"])

TIE_ORDER = sorted(REGION, key=lambda name: (REGION_ORDER.index(REGION[name]), name))
assert TIE_ORDER == ["Costa Rica", "Guatemala", "Panama", "Dominican Republic", "China"]

ORDER = ["Mexico", "Canada"] + TIE_ORDER + ["All other"]     # top to bottom
assert set(ORDER) == set(exports["Market / Country"]) and len(ORDER) == 8


SUB_PX   = 24
LINE_GAP = 24          # clear space between one line's baseline and the next line's cap top

KICKER_BASE = MARGIN + KICKER_PX * BARLOW.cap
TITLE_BASE  = KICKER_BASE + LINE_GAP + TITLE_PX * HEADLINE_FONT.cap
SUB_BASE    = TITLE_BASE  + LINE_GAP + SUB_PX * BARLOW.cap
print(KICKER_BASE, TITLE_BASE, SUB_BASE)
assert SUB_BASE + 6 < HEADER_H

# 1 Layout and Geometry
BODY_TOP, BODY_BOTTOM = HEADER_H, H_PX - FOOTER_H        # 190 to 807

# horizontal
BAR_X0 = MARGIN
FLAG_W, FLAG_H = 133, 80
FLAG_TOP_PAD   = 10
FLAG_LABEL_GAP      = 28          # flag bottom to the MINNESOTA label's baseline
BAR_AIR        = 12          # label baseline to the bar's top
bar_top = BODY_TOP + FLAG_TOP_PAD + FLAG_H + FLAG_LABEL_GAP + BAR_AIR

BAR_W   = 26
BAR_X1  = MARGIN + BAR_W              # the bar's right edge, where every ribbon starts
assert BAR_X0 >= MARGIN
HERO_CELL = 8                                   # bitmap cell size for "$73.84M", px
NUM_GAP   = 28                                  # air between ribbon end and numerals
hero_w    = len(NUMERALS[0]) * 6 * HERO_CELL    # 6 cells per character, as in the sketch
RIB_X1    = W - MARGIN - NUM_GAP - hero_w
assert RIB_X1 > BAR_X1 + 400, "ribbons too short"
# vertical
THICK   = 360              # total ribbon thickness for the full $104M, px
RIB_GAP = 24                # air between ribbons at the destination end
D = 7.5
by_name = exports.set_index("Market / Country")[VALUE]
t = {name: by_name[name] / by_name.sum() * THICK for name in ORDER}      # px per market
assert abs(sum(t.values()) - THICK) < 1e-9
assert BODY_TOP <= bar_top and bar_top + THICK <= BODY_BOTTOM
DST_SPAN = THICK + (len(ORDER) - 1) * RIB_GAP
dst_top = (BODY_TOP + BODY_BOTTOM - DST_SPAN) / 2            # top of the destination stack, centered in the body
assert BODY_TOP <= dst_top and dst_top + DST_SPAN <= BODY_BOTTOM
assert min(t.values()) >= 0.9 * D, "thinnest ribbon is shorter than one turkey row"

src_y0 = {}
dst_y0 = {}
src_y = bar_top
dst_y = dst_top
for name in ORDER:
    src_y0[name] = src_y
    dst_y0[name] = dst_y
    src_y += t[name]               # source slices touch: no gap on the bar
    dst_y += t[name] + RIB_GAP     # destination slices are spaced out
assert abs(src_y - (bar_top + THICK)) < 1e-9                       # source slices fill the bar exactly
assert abs((dst_y - RIB_GAP) - (dst_top + DST_SPAN)) < 1e-9        # destination stack has the expected span
assert set(src_y0) == set(dst_y0) == set(ORDER)

# 2  HELPERS: reuse from build_us_pop_canvas.py until glyph_helpers.py exists
rows = []                                  # every helper appends dicts here; one DataFrame at the end
LAYERS = ("back", "data", "text")

def line(key, xs, ys, layer, **cols):
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



glyph_rows(BARLOW, "t", "I", 100, 200, 68, "text", color="FFFFFF")
assert len({r["poly_id"] for r in rows}) == 1
rows.clear()


def star(key, cx, cy, r, layer, points=8, inner=0.4, **cols):
    pts = []
    for k in range(2 * points):
        a = math.pi / points * k - math.pi / 2                 # start at the top, go clockwise
        reach = r if k % 2 == 0 else inner * r              
        pts.append((cx + reach * math.cos(a), cy + reach * math.sin(a)))
    line(key, [p[0] for p in pts], [p[1] for p in pts], layer, **cols)

star("t", 100, 100, 10, "back", color="FFFFFF")
assert len(rows) == 16
assert (round(min(r["y_px"] for r in rows), 6), round(max(r["y_px"] for r in rows), 6)) == (90, 110)
rows.clear()

star("t4", 100, 100, 10, "back", points=4, color="FFFFFF")
assert len(rows) == 8          # four points, eight corners: wk45's sparkle
rows.clear()

def cubic(p0, p1, p2, p3, steps):
    """Points along one cubic curve, not including p0 (it's the previous segment's end)."""
    pts = []
    for i in range(1, steps + 1):
        t = i / steps
        x = (1 - t)**3 * p0[0] + 3 * (1 - t)**2 * t * p1[0] + 3 * (1 - t) * t**2 * p2[0] + t**3 * p3[0]
        y = (1 - t)**3 * p0[1] + 3 * (1 - t)**2 * t * p1[1] + 3 * (1 - t) * t**2 * p2[1] + t**3 * p3[1]
        pts.append((x, y))
    return pts

def ribbon(key, p0, p1, p2, p3, half, steps, layer, **cols):
    """A cubic curve with thickness: the top edge out, the bottom edge back."""
    pts    = [p0] + cubic(p0, p1, p2, p3, steps)             # cubic() leaves out p0
    top    = [(x, y - half) for x, y in pts]
    bottom = [(x, y + half) for x, y in reversed(pts)]              # offset the other way, in reverse order
    line(key, [p[0] for p in top + bottom], [p[1] for p in top + bottom], layer, **cols)

ribbon("t", (0, 0), (5, 0), (5, 10), (10, 10), 0.6, 8, "data")
assert len(rows) == 18
assert (rows[0]["x_px"], rows[0]["y_px"]) == (0, -.6)
assert (min(r["y_px"] for r in rows), max(r["y_px"] for r in rows)) == (-.6, 10.6)
rows.clear()


# 3  LAYERS: one block per piece of the picture, each ending in asserts
def centerline(name):
    y0 = src_y0[name] + t[name] / 2
    y1 = dst_y0[name] + t[name] / 2
    xm = (BAR_X1 + RIB_X1) / 2
    p0, p1, p2, p3 = (BAR_X1, y0), (xm, y0), (xm, y1), (RIB_X1, y1)
    return [p0] + cubic(p0, p1, p2, p3, 400)          # a dense polyline

def samples(name):
    pts = centerline(name)
    cum = [0.0]                                              # distance from the start to each point
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        cum.append(cum[-1] + math.hypot(xb - xa, yb - ya))

    out, i, s = [], 0, D / 2                                 # s = distance of the next sample
    while s <= cum[-1] - D / 2:
        while cum[i + 1] < s:                                # advance to the segment holding s
            i += 1
        (xa, ya), (xb, yb) = pts[i], pts[i + 1]
        f = (s - cum[i]) / (cum[i + 1] - cum[i])             # how far along this segment, 0 to 1
        x = xa + f * (xb - xa)
        y = ya + f * (yb - ya)
        angle = math.atan2(yb - ya, xb - xa)                 # direction of this segment: math.atan2
        out.append((x, y, angle))
        s += D
    return out
c = samples("Canada")
assert all(abs(math.dist(c[k][:2], c[k + 1][:2]) - D) < 0.1 for k in range(len(c) - 1))   # spacing is D
assert BAR_X1 < c[0][0] < BAR_X1 + D and c[-1][0] < RIB_X1

rows_per  = {name: max(1, round(t[name] / D)) for name in ORDER}
N_TURKEYS = sum(len(samples(name)) * rows_per[name] for name in ORDER)
print(N_TURKEYS)

ACCENT = "$73.8 million"
REST   = HEADLINE[len(ACCENT):]                       # " worth of turkeys trot ..."
assert HEADLINE.startswith(ACCENT)
accent_w = HEADLINE_FONT.width(ACCENT, TITLE_PX)

glyph_rows(HEADLINE_FONT, "title_accent", ACCENT, MARGIN, TITLE_BASE, TITLE_PX, "text", color=HEX["headline_accent"])
glyph_rows(HEADLINE_FONT, "title_rest",   REST,   MARGIN + accent_w, TITLE_BASE, TITLE_PX, "text", color=HEX["ink"])
glyph_rows(BARLOW, "kicker", KICKER, MARGIN, KICKER_BASE, KICKER_PX, "text", tracking=KICK_TRACK, color=HEX["soft"])
glyph_rows(BARLOW, "sub",    SUBTITLE, MARGIN, SUB_BASE, SUB_PX, "text", color=HEX["soft"])
hdr = pd.DataFrame(rows)
assert hdr.x_px.between(MARGIN, W - MARGIN).all()
assert hdr.y_px.between(0, HEADER_H).all()
print(len(rows))

TURKEY_BODY = [(-36, -28), (-20, -42), (-4, -34), (2, -12), (10, -30), (24, -4), (20, 22), (0, 34), (-22, 26), (-34, 6)]
TURKEY_HEAD = [(6, -40), (20, -38), (12, -24)]
TURKEY_BEAK = [(19, -37), (30, -32), (19, -32)]                                                                           # 3
GLYPH_VERTS = len(TURKEY_BODY) + len(TURKEY_HEAD) + len(TURKEY_BEAK)

VERTS_MAX = 16
assert GLYPH_VERTS <= VERTS_MAX, f"glyph has {GLYPH_VERTS} vertices, budget is {VERTS_MAX}"

parts = (TURKEY_BODY, TURKEY_HEAD, TURKEY_BEAK)
gx = [x for part in parts for x, _ in part]
gy = [y for part in parts for _, y in part]
GLYPH_W, GLYPH_H = max(gx) - min(gx), max(gy) - min(gy)       # 66 and 76 units
assert (GLYPH_W, GLYPH_H) == (66, 76)
TURKEY_S = D/100                                                # px per unit
assert GLYPH_W * TURKEY_S <= D and GLYPH_H * TURKEY_S <= D, "turkeys would touch"

def place(pts, x, y, angle, s):
    """Unit-shape vertices -> canvas vertices: scale, rotate, translate."""
    ca, sa = math.cos(angle), math.sin(angle)
    out = []
    for ux, uy in pts:
        px, py = ux * s, uy * s                     # scale
        nx = x + px * ca - py * sa             # rotate, then move to the sample x
        ny = y + px * sa + py * ca             # rotate, then move to the sample y
        out.append((nx, ny))                    # append x and y 
    return out

def turkey(key, x, y, angle, body, head, s=TURKEY_S):
    for part, pts, color in (("body", TURKEY_BODY, body), ("head", TURKEY_HEAD, head), ("beak", TURKEY_BEAK, HEX["beak"])):
        q = place(pts, x, y, angle, s)
        line(f"{key}:{part}", [p[0] for p in q], [p[1] for p in q], "data", color=color)
        
# angle 0: scale and translate
before = len(rows)
turkey("t", 100, 100, 0, "006847", "006847")
new = rows[before:]
assert len(new) == GLYPH_VERTS
xs = [r["x_px"] for r in new]
assert abs(min(xs) - (100 + min(gx) * TURKEY_S)) < 1e-6
assert abs(max(xs) - (100 + max(gx) * TURKEY_S)) < 1e-6
del rows[before:]
assert len(rows) == before

# angle pi: rotation (mirror about x = 100)
before = len(rows)
turkey("t", 100, 100, math.pi, "006847", "006847")
new = rows[before:]
assert len(new) == GLYPH_VERTS
xs = [r["x_px"] for r in new]
assert abs(min(xs) - (100 - max(gx) * TURKEY_S)) < 1e-6
assert abs(max(xs) - (100 - min(gx) * TURKEY_S)) < 1e-6
del rows[before:]
assert len(rows) == before

# ---- 3c  UNDERLAYS -------------------------------------------------------------
under_start = len(rows)
def thin(pts, every):
    """Every `every`-th point, always keeping the last one."""
    out = pts[::every]
    if out[-1] != pts[-1]:
        out.append(pts[-1])
    return out

def band(key, pts, half, layer, **cols):
    """A polyline with thickness: top edge out, bottom edge back (same idea as ribbon())."""
    top    = [(x, y - half) for x, y in pts]
    bottom = [(x, y + half) for x, y in reversed(pts)]
    line(key, [p[0] for p in top + bottom], [p[1] for p in top + bottom], layer, **cols)

UNDER_KEYS = {"Canada": "under_canada", "Dominican Republic": "under_rep_dominicana",
              "Guatemala": "under_guatemala", "Costa Rica": "under_costa_rica", "Panama": "under_panama",
              "China": "under_china", "All other": "under_otros"}

X_THIRD  = (RIB_X1 - BAR_X1) / 3
UNDER_X1 = RIB_X1 - D / 2

for name, key in UNDER_KEYS.items():
    pts = [p for p in centerline(name) if p[0] <= UNDER_X1]
    band(key + ":" + name, thin(pts, 10), t[name] / 2, "back", color=HEX[key])

mex_line = centerline("Mexico")
cuts = [BAR_X1, BAR_X1 + X_THIRD, BAR_X1 + 2 * X_THIRD, UNDER_X1 + 1e-9]
for key, lo_x, hi_x in zip(("under_mexico_green", "under_mexico_white", "under_mexico_red"), cuts, cuts[1:]):
    seg = [p for p in mex_line if lo_x <= p[0] < hi_x]
    band(key, thin(seg, 10), t["Mexico"] / 2, "back", color=HEX[key])

under = rows[under_start:]
assert len({r["poly_id"] for r in under}) == 10
assert min(r["y_px"] for r in under) >= BODY_TOP and max(r["y_px"] for r in under) <= BODY_BOTTOM
print(len(under))


# ---- 3d  RAYS ------------------------------------------------------------------
rays_start = len(rows)
RAY_N     = 24                                    # wedges drawn
RAY_ORIGIN = (BAR_X0, bar_top + THICK / 2)        # fan from the middle of the Minnesota bar
RAY_R     = 1.2 * W                               # long enough to leave the canvas
RAY_SPAN  = math.pi * 0.9                                  # total angle covered, in radians (e.g. math.pi * 0.9)
RAY_START = -RAY_SPAN / 2                         # fan centered on straight right

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

for k in range(RAY_N):
    a0 = RAY_START + RAY_SPAN * (2 * k)     / (2 * RAY_N)       # wedge start angle
    a1 = RAY_START + RAY_SPAN * (2 * k + 1) / (2 * RAY_N)       # wedge end angle (half the slot)
    pts = [RAY_ORIGIN] + [(RAY_ORIGIN[0] + RAY_R * math.cos(a), RAY_ORIGIN[1] + RAY_R * math.sin(a))
                          for a in (a0, a1)]
    xs = [clamp(p[0], 0, W) for p in pts]
    ys = [clamp(p[1], 0, H_PX) for p in pts]
    line(f"ray:{k}", xs, ys, "back", color=HEX["ray_tint"])

rays = rows[rays_start:]
assert len({r["poly_id"] for r in rays}) == RAY_N
assert min(r["x_px"] for r in rays) >= 0 and max(r["x_px"] for r in rays) <= W
assert min(r["y_px"] for r in rays) >= 0 and max(r["y_px"] for r in rays) <= H_PX
print(len(rays))

# ---- 3e  MINNESOTA BAR + FLAG -------------------------------------------------
before = len(rows)
flag_top    = BODY_TOP + FLAG_TOP_PAD
flag_bottom = flag_top + FLAG_H
label_base  = flag_bottom + FLAG_LABEL_GAP
assert abs(label_base + BAR_AIR - bar_top) < 1e-9      # the constants agree with section 1

rect("mn_bar",   BAR_X0, bar_top, BAR_X1, bar_top + THICK, "back", color=HEX["mn_bar"])
CHEV_EDGE, CHEV_APEX = 0.56, 0.39
STAR_CX, STAR_R, STAR_INNER = 0.21, 0.183, 0.54
fx = lambda f: BAR_X0 + f * FLAG_W
flag_mid = flag_top + FLAG_H / 2
rect("mn_field", BAR_X0, flag_top, BAR_X0 + FLAG_W, flag_bottom, "back", color=HEX["mn_field"])     # light, whole flag
line("mn_dark", [BAR_X0, fx(CHEV_EDGE), fx(CHEV_APEX), fx(CHEV_EDGE), BAR_X0],
                [flag_top, flag_top, flag_mid, flag_bottom, flag_bottom], "back", color=HEX["mn_bar"])  # dark with the chevron
star("mn_star", fx(STAR_CX), flag_mid, STAR_R * FLAG_H, "back", inner=STAR_INNER, color=HEX["mn_star"])
assert fx(STAR_CX) + STAR_R * FLAG_H < fx(CHEV_APEX), "star pokes into the light blue"
glyph_rows(BARLOW, "mn_label", "MINNESOTA", BAR_X0, label_base, 18, "text", color=HEX["names"])


mn = rows[before:]
assert min(r["x_px"] for r in mn) >= MARGIN and max(r["x_px"] for r in mn) <= W - MARGIN
assert BARLOW.width("MINNESOTA", 18) <= FLAG_W + 20      # the label doesn't run past the flag
assert min(r["y_px"] for r in mn) >= BODY_TOP and max(r["y_px"] for r in mn) <= BODY_BOTTOM
# ---- 3f  FLOCKS (the data layer) ----------------------------------------------
# body_color / head_color per market:  {"Canada": (HEX["body_canada"], HEX["head_canada"]), ...}
def flock(name, body, head, alt_head =None):
    n = rows_per[name]
    for k, (x, y, angle) in enumerate(samples(name)):
        for j in range(n):
            off = (j + 0.5) / n * t[name] - t[name] / 2
            nx = x + off * math.cos(angle + math.pi / 2)      # step along the normal
            ny = y + off * math.sin(angle + math.pi / 2)      # same step, y component
            b = body(nx) if callable(body) else body          # a function of x, or a fixed color
            h = head(nx) if callable(head) else head
            if alt_head is not None and (k + j) % 2 == 1:      # odd cells take the second head color
                h = alt_head
            turkey(f"{name}:{k}:{j}", nx, ny, angle, b, h)
# asserts: turkey count == N_TURKEYS
#          every flock x_px within BAR_X1 - D .. RIB_X1 + D
#          every flock y_px within BODY_TOP .. BODY_BOTTOM

before = len(rows)
flock("Canada", HEX["body_canada"], HEX["head_canada"])
new = rows[before:]
n_turkeys = len(samples("Canada")) * rows_per["Canada"]
assert len(new) == n_turkeys * GLYPH_VERTS
assert len({r["poly_id"] for r in new}) == n_turkeys * 3          # body, head, beak per turkey
ys = [r["y_px"] for r in new]
src_c = src_y0["Canada"] + t["Canada"] / 2          # source center
dst_c = dst_y0["Canada"] + t["Canada"] / 2          # destination center
lo = min(src_c, dst_c) - t["Canada"] / 2 - D
hi = max(src_c, dst_c) + t["Canada"] / 2 + D
assert lo < min(ys) and max(ys) < hi
del rows[before:]
assert len(rows) == before

FLOCK_COLORS = {
    "Canada":             (HEX["body_canada"],     HEX["head_canada"]),
    "Dominican Republic": (HEX["body_dominicana"], HEX["head_dominicana"]),
    "Costa Rica":         (HEX["body_costa_rica"], HEX["head_costa_rica"]),
    "Panama":             (HEX["body_panama"],     HEX["head_panama"]),
    "China":              (HEX["body_china"],      HEX["head_china"]),
    "Guatemala":          (HEX["body_guatemala"],  HEX["head_guatemala"]),
}

before = len(rows)
for name, (body, head) in FLOCK_COLORS.items():
    flock(name, body, head)
new = rows[before:]
n_expected = sum(len(samples(n)) * rows_per[n] for n in FLOCK_COLORS)
assert len(new) == n_expected * GLYPH_VERTS
assert min(r["x_px"] for r in new) > BAR_X1 - D and max(r["x_px"] for r in new) < RIB_X1 + D
assert min(r["y_px"] for r in new) > BODY_TOP and max(r["y_px"] for r in new) < BODY_BOTTOM
del rows[before:]
assert len(rows) == before

def mexico_color(x):
    if x < BAR_X1 + X_THIRD:
        return HEX["body_mexico_green"]
    elif x < BAR_X1 + 2 * X_THIRD:
        return HEX["body_mexico_white"]
    else:
        return HEX["body_mexico_red"]

before = len(rows)
flock("Mexico", mexico_color, mexico_color)
new = rows[before:]
assert len(new) == len(samples("Mexico")) * rows_per["Mexico"] * GLYPH_VERTS
colors = {r["color"] for r in new}
assert {HEX["body_mexico_green"], HEX["body_mexico_white"], HEX["body_mexico_red"]} <= colors
green = [r["x_px"] for r in new if r["color"] == HEX["body_mexico_green"]]
assert max(green) < BAR_X1 + X_THIRD + D                 # green stays in the first third (+ one turkey of overhang)
del rows[before:]
assert len(rows) == before

before = len(rows)
flock("All other", HEX["body_otros_1"], HEX["head_otros_2"], alt_head=HEX["head_otros_3"])
new = rows[before:]
assert len(new) == len(samples("All other")) * rows_per["All other"] * GLYPH_VERTS
colors = {r["color"] for r in new}
assert {HEX["body_otros_1"], HEX["head_otros_2"], HEX["head_otros_3"]} <= colors
del rows[before:]
assert len(rows) == before

flock_start = len(rows)
for name, (body, head) in FLOCK_COLORS.items():
    flock(name, body, head)
flock("Mexico", mexico_color, mexico_color)
flock("All other", HEX["body_otros_1"], HEX["head_otros_2"], alt_head=HEX["head_otros_3"])
flock_rows = rows[flock_start:]
assert len(flock_rows) == N_TURKEYS * GLYPH_VERTS
assert len({r["poly_id"] for r in flock_rows}) == N_TURKEYS * 3
print(len(rows))



# ---- 3g  NUMERAL TURKEYS (5x7 bitmap, one turkey per lit cell) -----------------
FONT_5X7 = {
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": [".###.", "#...#", "....#", "..##.", "....#", "#...#", ".###."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": ["..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."],
    "$": ["..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."],
    ".": [".....", ".....", ".....", ".....", ".....", "..##.", "..##."],
    "M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
}
assert len(FONT_5X7) == 13          # a repeated key would shrink this
for ch, g in FONT_5X7.items():
    assert len(g) == 7 and all(len(r) == 5 for r in g), f"bad glyph {ch!r}"
assert set("".join(NUMERALS)) <= set(FONT_5X7), "a numeral character has no glyph"

def numeral(key, text, x0, y_center, cell, body, head):
    for ci, ch in enumerate(text):
        for r, row in enumerate(FONT_5X7[ch]):
            for c, bit in enumerate(row):
                if bit == "#":
                    x = x0 + (ci * 6 + c + 0.5) * cell
                    y = y_center + (r + 0.5 - 3.5) * cell        # seven rows centered on y_center: what is half of 7?
                    turkey(f"{key}:{ci}:{r}:{c}", x, y, 0, body, head, s=cell / 100)

num_start = len(rows)
SMALL_CELL = 6         # for example 5: six characters at 6 cells each is 180 px wide
tie_top    = dst_y0[TIE_ORDER[0]]
tie_bottom = dst_y0[TIE_ORDER[-1]] + t[TIE_ORDER[-1]]
tie_center = (tie_top + tie_bottom) / 2

num_x0 = RIB_X1 + NUM_GAP
mex_c  = dst_y0["Mexico"]     + t["Mexico"] / 2
can_c  = dst_y0["Canada"]     + t["Canada"] / 2
oth_c  = dst_y0["All other"]  + t["All other"] / 2

numeral("num_mexico", NUMERALS[0], num_x0, mex_c,      HERO_CELL,  HEX["body_mexico_green"], HEX["body_mexico_green"])
SIDE_NAMES = {n: TRANSLATE.get(n, n) for n in ORDER[1:]}
lab_w      = max(BARLOW.width(s, LABEL_PX) for s in SIDE_NAMES.values())
tie_x0     = num_x0 + lab_w + 12          # now the shared left edge of all three small numerals
assert tie_x0 + len(NUMERALS[2]) * 6 * SMALL_CELL <= W - MARGIN, "tie numeral runs off the canvas"
numeral("num_canada", NUMERALS[1], tie_x0, can_c,      SMALL_CELL, *FLOCK_COLORS["Canada"])
numeral("num_tie",    NUMERALS[2], tie_x0, tie_center, SMALL_CELL, HEX["body_costa_rica"], HEX["body_china"])
numeral("num_otros",  NUMERALS[3], tie_x0, oth_c,      SMALL_CELL, HEX["body_otros_1"], HEX["body_otros_1"])

nums = rows[num_start:]            # AFTER the calls
assert max(r["x_px"] for r in nums) <= W - MARGIN
assert min(r["y_px"] for r in nums) >= BODY_TOP and max(r["y_px"] for r in nums) <= BODY_BOTTOM
print(len(nums))

# ---- 3h  LABELS + MÉXICO TEXT --------------------------------------------------
text_start = len(rows)

MX_PX   = 56                                         # text size in px (try 56)
mx_x    = BAR_X1 + 1.5 * X_THIRD                        # center of the white band
mx_pts  = centerline("Mexico")
mx_y    = min(mx_pts, key=lambda p: abs(p[0] - mx_x))[1]   # centerline y at that x
mx_base = mx_y + MX_PX * HEADLINE_FONT.cap / 2          # baseline so the caps are centered on mx_y
assert HEADLINE_FONT.width("México", MX_PX) <= X_THIRD - 20, "México text too wide for the white band"
assert_glyphs(HEADLINE_FONT, "México", "mexico text")   # does Anton have the é?
assert_glyphs(BARLOW, "cada uno", "cada uno")

HALO_R = 2                                              # px of halo around each letter
for i in range(8):
    a = math.pi / 4 * i
    glyph_rows(HEADLINE_FONT, f"mx_halo{i}", "México", mx_x + HALO_R * math.cos(a), mx_base + HALO_R * math.sin(a),
               MX_PX, "text", align="center", color=HEX["halo"])
glyph_rows(HEADLINE_FONT, "mx_text", "México", mx_x, mx_base, MX_PX, "text", align="center", color=HEX["ink"])

mx = rows[text_start:]
assert min(r["x_px"] for r in mx) >= BAR_X1 + X_THIRD and max(r["x_px"] for r in mx) <= BAR_X1 + 2 * X_THIRD
assert min(r["y_px"] for r in mx) >= BODY_TOP and max(r["y_px"] for r in mx) <= BODY_BOTTOM
print(len(mx))

def label_above(key, name, num_cell, y_center, color):
    txt  = TRANSLATE.get(name, name)
    base = y_center - 3.5 * num_cell - LABEL_GAP
    glyph_rows(BARLOW, key, txt, num_x0, base, LABEL_PX, "text", color=color)

labels_start = len(rows)
label_above("lab_mexico", "Mexico",    HERO_CELL,  mex_c, HEX["ink"])

lab = rows[labels_start:]
assert max(r["x_px"] for r in lab) <= W - MARGIN
assert min(r["y_px"] for r in lab) >= BODY_TOP
print(len(lab))

ties_start = len(rows)
for n in ORDER[1:]:
    yc   = dst_y0[n] + t[n] / 2
    base = yc + LABEL_PX * BARLOW.cap / 2
    glyph_rows(BARLOW, f"lab_{n}", SIDE_NAMES[n], num_x0, base, LABEL_PX, "text", color=HEX["ink"])

# cada uno under the tie numeral
glyph_rows(BARLOW, "lab_cada", "cada uno", tie_x0, tie_center + 3.5 * SMALL_CELL + LABEL_GAP + LABEL_PX,
           LABEL_PX, "text", color=HEX["ink"])
ties = rows[ties_start:]
assert max(r["x_px"] for r in ties) <= W - MARGIN
assert min(r["y_px"] for r in ties) >= BODY_TOP and max(r["y_px"] for r in ties) <= BODY_BOTTOM
print(len(ties))

# ---- 3i  FOOTER + CREDIT --------------------------------------------------------
CREDIT    = "Luis Pablo Martínez"          # your full name
CREDIT_PX = 18            # try 18
assert_glyphs(HEADLINE_FONT, CREDIT, "credit")          # Anton must have every letter, accents included
FOOT_BASE = H_PX -20     # try 20
assert BARLOW.width(FOOTER, FOOT_PX) + HEADLINE_FONT.width(CREDIT, CREDIT_PX) + 40 <= W - 2 * MARGIN, "footer + credit collide"

foot_start = len(rows)
glyph_rows(BARLOW,        "footer", FOOTER, MARGIN,     FOOT_BASE, FOOT_PX,   "text", color=HEX["soft"])
glyph_rows(HEADLINE_FONT, "credit", CREDIT, W - MARGIN, FOOT_BASE, CREDIT_PX, "text", align="right", color=HEX["ink"])
foot = rows[foot_start:]
assert min(r["x_px"] for r in foot) >= MARGIN and max(r["x_px"] for r in foot) <= W - MARGIN
assert min(r["y_px"] for r in foot) >= BODY_BOTTOM and max(r["y_px"] for r in foot) <= H_PX - 8
print(len(foot))

# ---- 4  ASSEMBLE ----------------------------------------------------------------
df = pd.DataFrame(rows)

# one z per hex: same-hex entries sit side by side in STACK (the split-color assert guarantees it),
# so any one z from the group works. Take the largest.
COLOR_Z = z_table.groupby("color")["z"].max()
df["z"] = df["color"].map(COLOR_Z)
assert df["z"].notna().all(), "a row has a color that is not in STACK"

df = df.sort_values(["z", "poly_id", "point_order"]).reset_index(drop=True)

# ---- 5  ASSERTS ------------------------------------------------------------------
ROW_CAP = 130_000                                      # provisional, until the load test says otherwise
assert len(df) <= ROW_CAP
assert df.x_px.between(0, W).all() and df.y_px.between(0, H_PX).all()
assert df["color"].isin(set(HEX.values())).all()
assert df.groupby("poly_id")["point_order"].apply(lambda s: list(s) == list(range(1, len(s) + 1))).all()
assert df.groupby("color")["z"].nunique().max() == 1        # one hex, one depth: how many z per color?
print(len(df), df["poly_id"].nunique())

# ---- 6  LON / LAT ----------------------------------------------------------------
df["lon"] = (df.x_px - W / 2) / DEG_PX                                   # from x_px and DEG_PX
df["lat"] = (H_PX / 2 - df.y_px) / DEG_PX                                  # from y_px, H_PX and DEG_PX
assert ((df.lon * DEG_PX + W / 2) - df.x_px).abs().max() < 1e-9      # round trip, x
assert ((H_PX / 2 - df.lat * DEG_PX) - df.y_px).abs().max() < 1e-9   # round trip, y
assert df.lon.abs().max() <= W / 2 / DEG_PX + 1e-9 and df.lat.abs().max() <= H_PX / 2 / DEG_PX + 1e-9

# ---- 7  WRITE ----------------------------------------------------------------------
COLUMNS = ["layer", "poly_id", "point_order", "lat", "lon", "color", "z"]
out = df[COLUMNS]
assert not out.duplicated(subset=["poly_id", "point_order"]).any()
assert out.notna().all().all()
write_atomic(OUT / "turkey_canvas.csv", out.to_csv(index=False))

check = pd.read_csv(OUT / "turkey_canvas.csv", dtype={"color": str})
pd.testing.assert_frame_equal(check, out, check_exact=False, rtol=1e-9)

colors = sorted(out["color"].unique())
assert set(colors) <= set(HEX.values())
items = "\n".join(f"      <color>#{c}</color>" for c in colors)
tps = f"""  <color-palette custom='true' name='Turkey' type='regular'>
{items}
  </color-palette>
"""
write_atomic(OUT / "turkey_palette.tps", tps)
maps = "\n".join(f"            <map to='#{c.lower()}'>\n              <bucket>&quot;{c}&quot;</bucket>\n            </map>" for c in colors)
write_atomic(OUT / "turkey_color_map.xml", maps)
print(len(out), len(colors))