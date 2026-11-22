# build_balloon_canvas.py  (Stage 3: canvas CSV, no analysis)

# 0  CONFIG
import json, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent.parent / "toolkit"))
from stage_helpers import write_atomic
from title_glyphs import TitleFont
import math

HERE = Path(__file__).parent
OUT  = Path.home() / "TableauData" / "wk45-hot-air-balloon"      # same folder Stage 2 wrote to

WORK = OUT / "work"                         # the folder explore_balloon.py wrote to
HEAD = json.loads((WORK / "headline.json").read_text())     
PLACES = pd.read_csv(WORK / "places.csv", dtype={"owner_seen": str})


def blend(fg_hex, bg_hex, alpha):
    out = ""
    for i in (0, 2, 4):                                   # red, green, blue
        f = int(fg_hex[i:i + 2], 16)
        b = int(bg_hex[i:i + 2], 16)
        out += f"{round((alpha * f) + (b * (1 - alpha))):02X}"
    return out


       
W, H_PX = 1387, 857
DEG_PX  = 40   
MARGIN, GAP = 40, 40    
HEADER_H, FOOTER_H = 267, 50
PALETTE = {"lit balloon": "D4AF37", "dim balloon": "55555E", "medal 1": "D4AF37", "medal 2": "B8BCC6", "medal 3": "B8733A",
           "medal rank 1": "F2D27A", "medal rank 2": "E3E5EA", "medal rank 3": "E0A06A", "unmedaled fill": "3A3A40", "unmedaled rank": "8C8C94",
           "place name rank 1": "F2D27A", "place name": "F5F5F2", "others": "F5F5F2", 
           "card text": "F5F5F2", "card border": "D4AF37", "card body": "0B0B0D", "card small": "B9B6AA", "card value": "F5F5F2", "card name": "F2D27A",
           "card big": "F2D27A", "card close": "F2D27A", "card label": "D4AF37", "small text": "B9B6AA", "subtitle": "B9B6AA", "notes": "B9B6AA", "offset shadow": "D4AF37",
           "button text gold": "0B0B0D", "page": "0B0B0D", "button filled": "D4AF37", "button outline": "D4AF37", "button inactive": "F2D27A",
           "bg": "0D0B12", "story": "E0243C", "context": "EDEAF2", 
           "faint": "8E8A99", "band": "37101A", "flag": "D9A441", "panel": "14111C", "grid": "24202F",
           "tick": "B4B0C0"}

assert blend("D4AF37", "0B0B0D", 1) == "D4AF37"
assert blend("D4AF37", "0B0B0D", 0) == "0B0B0D"
assert blend("D4AF37", "0B0B0D", 0.55) == "7A6524"
assert blend("D4AF37", "0B0B0D", 0.4) == "5B4D1E"

PAGE = PALETTE["page"]
STACK = [                                   # back to front: (element, hex)
    ("fan_gold",      blend(PALETTE["medal 1"], PAGE, 0.55)),
    ("fan_silver",    blend(PALETTE["medal 2"], PAGE, 0.55)),
    ("fan_bronze",    blend(PALETTE["medal 3"], PAGE, 0.55)),
    ("fan_other",     blend(PALETTE["unmedaled rank"], PAGE, 0.55)),
    ("balloon_dim",   PALETTE["dim balloon"]),
    ("balloon_lit",   PALETTE["lit balloon"]),
    ("medal_ring_1",  PALETTE["medal rank 1"]),  ("medal_ring_2", PALETTE["medal rank 2"]),  ("medal_ring_3", PALETTE["medal rank 3"]),  ("medal_ring_0", PALETTE["unmedaled rank"]),
    ("medal_fill_1",  "D4AF38"),  # medal 1 fill: D4AF37 nudged, so the lit balloon keeps its own level
    ("medal_fill_2", PALETTE["medal 2"]),  ("medal_fill_3", PALETTE["medal 3"]),  ("medal_fill_0", PALETTE["unmedaled fill"]),
    ("name_rank1",    "F2D27B"),  # rank 1 name: F2D27A nudged, so the ring keeps its own level,
    ("name_other",    PALETTE["place name"]),
    ("btn_inactive_outline", "D4AF36"),   # inactive button outline: D4AF37 nudged, so the lit balloon keeps its own level
    ("btn_inactive_bg",      PALETTE["page"]),   # the smaller rectangle, inset by the outline's thickness
    ("btn_inactive_text",    "F2D27C"),   # the nudged literal we just decided
    ("btn_active_fill", "D4AF35"),   # gold fill - literal nudge
    ("btn_active_text", "0B0B0E"),   # dark letters - literal nudge
    ("card_shadow",  "D4AF34"),   # card shadow: D4AF37 nudged, so the lit balloon keeps its own level
    ("card_border",  "D4AF34"),   # same literal as the shadow; adjacent rows can share a level
    ("card_body",    "0B0B0F"),   # card body: 0B0B0D nudged, so the inactive button keeps its own level
    ("card_hit",     "0B0C0D"),   # invisible click area, one digit off the body
    ("card_divider", blend(PALETTE["card border"], PALETTE["card body"], 0.4)),   # blend(gold, body, 0.4)
    ("card_name",    "F2D27D"),   # F2D27D - literal nudge
    ("card_big",     "F2D27D"),   # F2D27D - literal nudge
    ("card_close",   "F2D27D"),   # F2D27D - literal nudge
    ("card_label",   "D4AF33"),   # gold labels: its own nudge, because the body sits between them and the border
    ("card_small",   PALETTE["card small"]),   # small grey line
    ("strip_note",  PALETTE["notes"]),   # shares B9B6AA with card small, it follows card small
    ("card_value",   "F5F5F3"),   # F5F5F3 - literal nudge,
    ("strip_label", "F2D27E"),   # strip label and click text: F2D27A nudged, shared by both
]
HEX = dict(STACK)
Z = {name: len(STACK) - i for i, (name, hex_) in enumerate(STACK)}
print(Z["fan_gold"], Z["name_other"])

z_table = pd.DataFrame({"color": [hex_ for name, hex_ in STACK],
                        "z":     [Z [name]for name, hex_ in STACK]})
span = z_table.groupby("color")["z"].agg(["min", "max"])
for color, (lo, hi) in span.iterrows():
    others = z_table[z_table["color"] != color]["z"]
    assert not others.between(lo, hi, inclusive="neither").any(), f"{color} is split"

max_n = PLACES["n"].max()
assert max_n == 795
assert PLACES["k"].sum() == 673
assert PLACES.loc[PLACES["Location"] == "Ohio", "k"].iloc[0] == 117

TOOLKIT = HERE.parent / "toolkit"
FONT_FILE   = TOOLKIT / "fonts" / "Shrikhand-Regular.ttf"
BARLOW_FILE = TOOLKIT / "fonts" / "BarlowCondensed-Medium.ttf"

for f in (FONT_FILE, BARLOW_FILE):
    assert f.exists(), f"font missing: {f}"



# 1  LAYOUT: vertical, descending order. jet stream of real balloons. one dot per real balloon. dim means not seen. yellow means seen.

BODY_TOP, BODY_BOTTOM = HEADER_H, H_PX - FOOTER_H

N_ROWS = 10
ROW_H = (BODY_BOTTOM - BODY_TOP) / N_ROWS
assert ROW_H == 54

BALLOON_ASPECT = 1.4                          # height / width, as in the sketch
ROW_PAD = 8                                # px of air above and below the big balloon
BALLOON_MAX_H = ROW_H - 2 * ROW_PAD
BALLOON_MAX_W = BALLOON_MAX_H / BALLOON_ASPECT
assert BALLOON_MAX_H < ROW_H
assert round(BALLOON_MAX_H) == 38
assert round(BALLOON_MAX_W, 2) == 27.14



LABEL_W, ZONE_W, STREAM_W, COL_GAP, CARD_W = 252, 171, 640, 16, 228
INNER_W = W - 2 * MARGIN
assert LABEL_W + ZONE_W + STREAM_W + COL_GAP + CARD_W <= INNER_W
LABEL_X0  = MARGIN
STREAM_X0 = LABEL_X0 + LABEL_W + ZONE_W
CARD_X0   = STREAM_X0 + STREAM_W + COL_GAP
assert CARD_X0 + CARD_W == W - MARGIN

STREAM_PAD = 1            # px of air above and below the stream inside its row
TINY_W = 4
TINY_GAP = 1
cell_w, cell_h = TINY_W + TINY_GAP, BALLOON_ASPECT * TINY_W + TINY_GAP
lanes = int((ROW_H - 2 * STREAM_PAD) // cell_h)
per_lane = int(STREAM_W // cell_w)
assert lanes * per_lane >= max_n

# rows inside the body, top to bottom
NAME_PX, BIG_PX, SMALL_PX = 17, 40, 13
ROW_GAP = 6

CREDIT_LEAD, CREDIT_NAME, CREDIT_PX, CREDIT_SHADOW = "Created by ", "Luis Pablo Martinez", 18, 2
CREDIT_LEAD_DROP = 4          # px below the name's baseline; try 3 or 4 if it still looks high

FOOT_PX, FOOT_LEAD, FOOT_TOP_PAD = 12, 16, 10

# 2  HELPERS: reuse from build_us_pop_canvas.py until glyph_helpers.py exists
rows = []                                  # every helper appends dicts here; one DataFrame at the end
LAYERS = ("back", "grid", "band", "data", "text", "cardframe", "cardname", "closebtn", "strip")

def line(key, xs, ys, layer, **cols):
    """Any polygon or path: one row per vertex. poly_id = key; point_order counts from 1."""
    assert layer in LAYERS, f"{key}: unknown layer {layer!r}"
    assert len(xs) == len(ys) >= 1
    cols.setdefault("click", "none")
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

NAME_FONT, BIG_FONT, SMALL_FONT = BARLOW, BARLOW, BARLOW      # the one place the fonts are chosen
assert max(NAME_FONT.width(name, NAME_PX) for name in PLACES["Location"]) <= LABEL_W


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

RIGHT = [(80, 20), (100, 50), (90, 85), (64, 108), (66, 140)]
TINY_UNIT = [(50, 0)] + RIGHT + [(100 - x, y) for x, y in reversed(RIGHT)]
assert len(TINY_UNIT) == 11

def balloon(key, x, y, w, layer, **cols):
    """Tiny balloon, top-left corner (x, y), width w; height is 1.4 w."""
    s = w / 100
    line(key, [x + px * s for px, py in TINY_UNIT], [y + py * s for px, py in TINY_UNIT], layer, **cols)

balloon("t", 10, 20, 50, "data")
assert len(rows) == 11
assert (min(r["x_px"] for r in rows), max(r["x_px"] for r in rows)) == (10, 60)
assert (min(r["y_px"] for r in rows), max(r["y_px"] for r in rows)) == (20, 90)
rows.clear()


# 3  LAYERS (one list of rows each; every row has layer, poly_id, point_order, x, y, color, tip)
HEADLINE_TEXT = "Be Seen,  "             # placeholder; your Hemingway/Burnett line replaces it
assert HEAD["totals"] == {"all": 7235, "top_ten": 3611, "seen": 1200}
SUBTITLE = f"The ten places with the most balloons hold {HEAD['totals']['top_ten']:,} of the {HEAD['totals']['all']:,} balloons in the archive"
assert BARLOW.width(SUBTITLE, 24) <=  W - 2 * MARGIN, "subtitle too wide"
KICKER = "MAKEOVER MONDAY · WEEK 45 · Hot Air Balloons"
TITLE_PX = SHRIKHAND.fit([HEADLINE_TEXT], W - 2 * MARGIN, 100)
SHADOW = max(4, round(TITLE_PX * 0.06))
# baselines: each one is the previous one plus a gap plus the next line's cap height
KICKER_BASE = 40 + 19 * BARLOW.cap
TITLE_BASE  = KICKER_BASE + 24 + TITLE_PX * SHRIKHAND.cap
SUB_BASE    = TITLE_BASE + SHADOW + 24 + 24 * BARLOW.cap
assert SUB_BASE + 6 < HEADER_H                       # the subtitle's descenders stay above the first panel row
print(SUB_BASE, HEADER_H, HEADER_H - SUB_BASE)
print(BARLOW.width(SUBTITLE, 24), W - 2 * MARGIN)
BTN_H = 44
FREE_TOP, FREE_BOTTOM = SUB_BASE + 6, HEADER_H
BTN_AIR = (FREE_BOTTOM - FREE_TOP - BTN_H) / 2     # equal air above and below
STRIP_TOP = FREE_TOP + BTN_AIR
STRIP_BOTTOM = STRIP_TOP + BTN_H
assert STRIP_BOTTOM + BTN_AIR == FREE_BOTTOM
print(STRIP_TOP, STRIP_BOTTOM, BTN_AIR)

BTN_PX, BTN_PAD, BTN_GAP = 15, 20, 10
BTN_TEXTS = ["Number of balloons", "Share seen in person"]
btn_w = [BARLOW.width(t, BTN_PX) + 2 * BTN_PAD for t in BTN_TEXTS]
print(btn_w)

STRIP_LABEL = "SORT AND SIZE BY"
STRIP_LABEL_PX, STRIP_LABEL_TRACK = 13, 2.34          # 0.18em at 13px, in px like KICK_TRACK
strip_label_w = BARLOW.width(STRIP_LABEL, STRIP_LABEL_PX, STRIP_LABEL_TRACK)
BTN1_X0 = MARGIN + strip_label_w + 16
BTN2_X0 = BTN1_X0 + btn_w[0] + BTN_GAP
NOTE_X0 = BTN2_X0 + btn_w[1] + 16
print(strip_label_w, BTN1_X0, BTN2_X0, NOTE_X0, W - MARGIN - NOTE_X0)

NOTES = {"count": "Biggest fleets first. The stream and the big balloon follow the count; medals go by rank.",
         "pct":   "Highest share seen first. The big balloon follows the share; medals mark tiers whose gaps are wider than chance."}
CLICK = "Click a balloon to see why"
NOTE_PX = 14
note_w = {mode: BARLOW.width(text, NOTE_PX) for mode, text in NOTES.items()}
click_w = BARLOW.width(CLICK, NOTE_PX)
room = W - MARGIN - NOTE_X0 - click_w - 16
print(note_w, click_w, room)


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


FOOT_1 = "Source: Kaggle: Hot Air Balloon (matthuff4)"
assert BARLOW.width(FOOT_1, FOOT_PX) <=  W - 2 * MARGIN, "source line too wide"
FOOT_2 = f"Seen = at least photographed ({HEAD['totals']['seen']:,} of {HEAD['totals']['all']:,} balloons)"
assert BARLOW.width(FOOT_2, FOOT_PX) <=  W - 2 * MARGIN, "footnote too wide"

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

STRIP_MID = STRIP_TOP + BTN_H / 2
label_base = STRIP_MID + STRIP_LABEL_PX * BARLOW.cap / 2
for mode in ("count", "pct"):
    glyph_rows(BARLOW, f"strip_label_{mode}", STRIP_LABEL, MARGIN, label_base, STRIP_LABEL_PX, "strip",
               tracking=STRIP_LABEL_TRACK, color=HEX["strip_label"], mode=mode, view=mode, when="always")

lab = pd.DataFrame(rows)
lab = lab[lab.poly_id.str.contains("strip_label")]
assert len(lab) > 0
assert lab.view.nunique() == 2
assert lab["view"].eq(lab["mode"]).all()
assert lab.x_px.between(MARGIN, BTN1_X0 - 16).all()
assert lab.y_px.between(STRIP_TOP, STRIP_BOTTOM).all()
print(len(lab))
print(lab.groupby("view").size())

BUTTONS = [("count", BTN_TEXTS[0], BTN1_X0, btn_w[0]),
           ("pct",   BTN_TEXTS[1], BTN2_X0, btn_w[1])]
btn_base = STRIP_MID + BTN_PX * BARLOW.cap / 2

note_base = STRIP_MID + NOTE_PX * BARLOW.cap / 2
for mode, text in NOTES.items():
    glyph_rows(BARLOW, f"strip_note_{mode}", text, NOTE_X0, note_base, NOTE_PX, "strip",
               color=HEX["strip_note"], mode= mode, view=mode, when="always")

nt = pd.DataFrame(rows)
nt = nt[nt.poly_id.str.contains("strip_note")]
assert nt.view.nunique() == 2
assert nt.x_px.between(NOTE_X0, W - MARGIN - click_w - 16).all()
print(nt.groupby("view").size())

for mode in ("count", "pct"):
    glyph_rows(BARLOW, f"strip_click_{mode}", CLICK, W - MARGIN, note_base, NOTE_PX, "strip",
               align="right", color=HEX["strip_label"], mode=mode, view=mode, when="none")

ck = pd.DataFrame(rows)
ck = ck[ck.poly_id.str.contains("strip_click")]
assert len(ck) > 0
assert ck["view"].nunique() == 2
assert ck["view"].eq(ck["mode"]).all()
assert ck.x_px.between(W - MARGIN - click_w, W - MARGIN).all()
print(ck.groupby("view").size())

for mode, label, x0, w in BUTTONS:
    rect(f"strip_btn_{mode}_active", x0, STRIP_TOP, x0 + w, STRIP_BOTTOM, "strip",
         color=HEX["btn_active_fill"], mode=mode, view=mode, when="always")
    glyph_rows(BARLOW, f"strip_btn_{mode}_active_text", label, x0 + w /2 , btn_base, BTN_PX, "strip",
               align="center", color=HEX["btn_active_text"], mode=mode, view=mode, when="always")

ba = pd.DataFrame(rows)
ba = ba[ba.poly_id.str.contains("_active")]
assert ba["view"].eq(ba["mode"]).all()
print(ba.groupby("poly_id").size())

BTN_LINE = 1
for mode, label, x0, w in BUTTONS:
    other = "count" if mode == "pct" else "pct"
    rect(f"strip_btn_{mode}_inactive_outline", x0, STRIP_TOP, x0 + w, STRIP_BOTTOM, "strip",
         color=HEX["btn_inactive_outline"], mode=mode, view= other, when="always")
    rect(f"strip_btn_{mode}_inactive_bg", x0 + BTN_LINE, STRIP_TOP + BTN_LINE, x0 + w - BTN_LINE, STRIP_BOTTOM - BTN_LINE, "strip",
         color=HEX["btn_inactive_bg"], mode=mode, view=other, when="always")
    glyph_rows(BARLOW, f"strip_btn_{mode}_inactive_text", label, x0 + w / 2, btn_base, BTN_PX, "strip",
               align="center", color=HEX["btn_inactive_text"], mode=mode, view=other, when="always")
bi = pd.DataFrame(rows)
bi = bi[bi.poly_id.str.contains("_inactive")]
assert (bi["view"] != bi["mode"]).all()
print(bi.groupby("view").size())

st = pd.DataFrame(rows)
st = st[st.poly_id.str.startswith("strip")]
for col in ("mode", "view", "when"):
    assert st[col].notna().all()
assert st["view"].isin(["pct", "count"]).all()
assert st["mode"].isin(["pct", "count"]).all()
assert st["when"].isin(["always", "none", "selected"]).all()
off = st[st["view"] != st["mode"]]
assert off.poly_id.str.contains("inactive").all()
cl = pd.DataFrame(rows)
assert "click" in cl.columns
assert cl["click"].notna().all()
assert cl["click"].eq("none").all()
print(len(cl))
print(len(st))

CARD_SHADOW, CARD_LINE = 4, 2
CARD_TOP, CARD_BOTTOM = BODY_TOP, BODY_BOTTOM
CARD_RIGHT = CARD_X0 + CARD_W
assert CARD_RIGHT + CARD_SHADOW <= W
assert CARD_BOTTOM + CARD_SHADOW < foot_base1 - FOOT_PX * BARLOW.cap

for mode in ("count", "pct"):
    rect(f"card_shadow_{mode}",
         CARD_X0 + CARD_SHADOW, CARD_TOP + CARD_SHADOW,
         CARD_RIGHT + CARD_SHADOW, CARD_BOTTOM + CARD_SHADOW,
         "cardframe",
         color=HEX["card_shadow"], mode=mode, view=mode,
         when="selected", place="none")

    rect(f"card_border_{mode}",
         CARD_X0, CARD_TOP, CARD_RIGHT, CARD_BOTTOM,
         "cardframe",
         color=HEX["card_border"], mode=mode, view=mode,
         when="selected", place="none")

    rect(f"card_body_{mode}",
         CARD_X0 + CARD_LINE, CARD_TOP + CARD_LINE,
         CARD_RIGHT - CARD_LINE, CARD_BOTTOM - CARD_LINE,
         "cardframe",
         color=HEX["card_body"], mode=mode, view=mode,
         when="selected", place="none")

CARD_PAD_X, CARD_PAD_TOP = 18, 12
CARD_INNER_W = CARD_W - 2 * (CARD_LINE + CARD_PAD_X)
CLOSE = "Close ×"
CLOSE_PX, CLOSE_PAD, CLOSE_H = 14, 10, 44
close_w = BARLOW.width(CLOSE, CLOSE_PX)

hit_x1 = CARD_RIGHT - CARD_LINE - CARD_PAD_X
hit_x0 = hit_x1 - (close_w + 2 * CLOSE_PAD)
hit_y0 = CARD_TOP + CARD_LINE + CARD_PAD_TOP
hit_y1 = hit_y0 + CLOSE_H
close_base = (hit_y0 + hit_y1) / 2 + CLOSE_PX * BARLOW.cap / 2

assert hit_x0 > CARD_X0 + CARD_LINE and hit_y1 < CARD_BOTTOM

for mode in ("count", "pct"):
    rect(f"card_hit_{mode}", hit_x0, hit_y0, hit_x1, hit_y1, "closebtn",
         color=HEX["card_hit"], mode=mode, view=mode, when="selected", place="none")
    glyph_rows(BARLOW, f"card_close_{mode}", CLOSE, hit_x1 - CLOSE_PAD, close_base, CLOSE_PX, "closebtn",
               align="right", color=HEX["card_close"], mode=mode, view=mode, when="selected", place="none")

hc = pd.DataFrame(rows)
hc = hc[hc.poly_id.str.contains("card_close")]
assert len(hc) > 0
assert hc.x_px.between(hit_x0, hit_x1).all()
assert hc.y_px.between(hit_y0, hit_y1).all()
print(hc.groupby("view").size())

DIVIDER_GAP = 12
big_base   = hit_y1 + ROW_GAP + BIG_PX * BARLOW.cap
small_base = big_base + ROW_GAP + SMALL_PX * BARLOW.cap
div_y      = small_base + DIVIDER_GAP
div_x0, div_x1 = CARD_X0 + CARD_LINE + CARD_PAD_X, hit_x1

assert div_y + 1 < CARD_BOTTOM - CARD_LINE

for mode in ("count", "pct"):
    rect(f"card_divider_{mode}", div_x0, div_y, div_x1, div_y + 1, "cardframe",
         color=HEX["card_divider"], mode=mode, view=mode, when="selected", place="none")

print(round(big_base, 1), round(small_base, 1), round(div_y, 1))


ROWS_PER_CHAR = 25
CARD_LABELS = ["STILL FLYING", "SEEN AMONG FLYING", "LARGEST FLEET"]

name_chars  = PLACES["Location"].str.len().mean()
big_chars   = 3                       # "40%" is how many characters?
small_chars = 12                       # "290 balloons"
label_chars = sum(len(s) for s in CARD_LABELS)
value_chars = 75                       # your guess for the three value lines together
MODES = ("count", "pct")


per_place_chars = name_chars + big_chars + small_chars + value_chars
content_rows    = per_place_chars * ROWS_PER_CHAR * len(PLACES) * len(MODES)
label_rows      = label_chars * ROWS_PER_CHAR * len(MODES)
print(round(content_rows), round(label_rows), round(content_rows + label_rows))

print(PLACES.columns.tolist())

LABEL_PX, LABEL_TRACK, VALUE_PX = 13, 1.82, 13      # 0.14em at 13px

def card_strings(p):
    big   = f"{p.k / p.n:.0%}"
    small = f"{p.n:,} balloons"
    v1 = f"{p.in_service:.0%}"
    v2 = f"{p.seen_in_service:.0%}"
    if BARLOW.width(p.top_owner, VALUE_PX) <= CARD_INNER_W:
        v3 = [p.top_owner]
    else:
        v3 = p.top_owner.split(" & ")
    v4 = f"{p.owner_n} balloons, {p.owner_seen} seen"
    return big, small, v1, v2, v3, v4

ohio = PLACES[PLACES["Location"] == "Ohio"].iloc[0]
print(card_strings(ohio))
print(ohio[["n", "in_service", "seen_in_service", "p", "k"]])

CARD_TEXT_X = CARD_X0 + CARD_LINE + CARD_PAD_X
name_base   = (hit_y0 + hit_y1) / 2 + NAME_PX * BARLOW.cap / 2

for mode in MODES:
    for place in PLACES.itertuples():
        big, small, v1, v2, v3, v4 = card_strings(place)
        glyph_rows(NAME_FONT, f"card_name_{mode}_{place.Location}", place.Location,
                   CARD_TEXT_X,name_base, NAME_PX, "cardname",
                   color=HEX["card_name"], mode=mode, view=mode, when="selected", place=place.Location)
        glyph_rows(BIG_FONT, f"card_big_{mode}_{place.Location}", big,
                   CARD_TEXT_X, big_base, BIG_PX, "cardname",
                   color=HEX["card_big"], mode=mode, view=mode, when="selected", place=place.Location)
        glyph_rows(SMALL_FONT, f"card_small_{mode}_{place.Location}", small,
                   CARD_TEXT_X, small_base, SMALL_PX, "cardname",
                   color=HEX["card_small"], mode=mode, view=mode, when="selected", place=place.Location)
NAME_GAP = 12      # px of clear space between the name and the close button
NAME_ROOM = hit_x0 - CARD_TEXT_X
assert max(NAME_FONT.width(n, NAME_PX) for n in PLACES["Location"]) + NAME_GAP <= NAME_ROOM

nm = pd.DataFrame(rows)
nm = nm[nm.poly_id.str.startswith("cardname:card_")]
print(len(nm), nm.groupby("view").size().to_dict())

assert nm.x_px.between(CARD_TEXT_X, CARD_RIGHT - CARD_LINE - CARD_PAD_X).all()
assert nm.y_px.between(hit_y0, div_y).all()


LINE_H = 17.55
LABEL_VALUE_GAP = LINE_H - VALUE_PX * BARLOW.cap
GROUP_GAP       = 10 + LINE_H - LABEL_PX * BARLOW.cap
LABEL_TOP_GAP   = 12 + (LINE_H - LABEL_PX * BARLOW.cap) / 2



label_base = []
value_base = []
prev = div_y + 1
for i in range(3):
    lb = prev + (LABEL_TOP_GAP if i == 0 else GROUP_GAP) + LABEL_PX * BARLOW.cap
    vb = lb + LABEL_VALUE_GAP + VALUE_PX * BARLOW.cap
    label_base.append(lb); value_base.append(vb)
    prev = vb
MAX_OWNER_LINES = max(len(card_strings(p)[4]) for p in PLACES.itertuples())
n_lines = [len(card_strings(p)[4]) for p in PLACES.itertuples()]
assert n_lines.count(2) == 1
value_last = value_base[-1] + MAX_OWNER_LINES * LINE_H      # the counts line of the tallest place
assert value_last < CARD_BOTTOM - CARD_LINE


widest_v3 = max(BARLOW.width(ln, VALUE_PX)
                for p in PLACES.itertuples()
                for ln in card_strings(p)[4])
widest_v4 = max(BARLOW.width(card_strings(p)[5], VALUE_PX) for p in PLACES.itertuples())
assert max(widest_v3, widest_v4) <= CARD_INNER_W

for mode in MODES:
    for i, text in enumerate(CARD_LABELS):
        glyph_rows(BARLOW, f"card_label_{mode}_{i}", text, CARD_TEXT_X, label_base[i], LABEL_PX, "cardframe",
                   tracking=LABEL_TRACK, color=HEX["card_label"], mode=mode, view=mode, when="selected", place="none")

    for place in PLACES.itertuples():
        big, small, v1, v2, v3, v4 = card_strings(place)
        groups = [[v1], [v2], v3 + [v4]]
        for i, group in enumerate(groups):
            for j, text in enumerate(group):
                glyph_rows(BARLOW, f"card_value_{mode}_{place.Location}_{i}_{j}", text,
                           CARD_TEXT_X, value_base[i] + j * LINE_H , VALUE_PX, "cardname",
                           color=HEX["card_value"], mode=mode, view=mode, when="selected", place=place.Location)

ct = pd.DataFrame(rows)
ct = ct[ct["layer"] == "cardname"]
sh = pd.DataFrame(rows)
sh = sh[sh["layer"].isin(["cardframe", "closebtn"])]
assert len(sh) > 0
assert sh["when"].eq("selected").all()
assert sh["place"].eq("none").all()
assert sh["view"].eq(sh["mode"]).all()
assert sh["click"].eq("none").all()
print(len(sh))
bad = ct[~ct["place"].isin(PLACES["Location"])]

assert len(ct) > 0
assert ct["place"].ne("none").all()
assert ct["place"].isin(PLACES["Location"]).all()
assert ct["when"].eq("selected").all()
assert ct["view"].eq(ct["mode"]).all()
assert ct["click"].eq("none").all()

RANK = {"pct": list(PLACES.sort_values("p", ascending=False)["Location"]),
        "count": list(PLACES.sort_values("n", ascending=False)["Location"])}

assert RANK["count"][0] == "New Mexico"
assert RANK["pct"][0] == "Ohio"

layout = []
for mode in ("pct", "count"):
    order = PLACES.set_index("Location").loc[RANK[mode]].reset_index()
    for r, place in enumerate(order.itertuples()):
        row_top = BODY_TOP + r * ROW_H + STREAM_PAD            # the stream's top edge in this row
        for i in range(place.n):
            col, lane = divmod(i, lanes)                  # fills each lane before starting the next column
            x = STREAM_X0 + col * cell_w
            y = row_top + lane * cell_h
            lit = i < place.k                             # the first k balloons are the seen ones
            layout.append(dict(glyph_key="tiny", mode=mode, place=place.Location, click=place.Location, idx=i,
                   x_off=f"{(x - W/2) / DEG_PX:.4f}", y_off=f"{(H_PX/2 - y) / DEG_PX:.4f}", lit=lit))

assert len(layout) == 7222          # 3,611 balloons × 2 modes
write_atomic(OUT / "balloon_layout.csv", pd.DataFrame(layout).to_csv(index=False))


atlas = []
for k, (px, py) in enumerate(TINY_UNIT, start=1):
    atlas.append(dict(glyph_key="tiny", ring=1, point_order=k,
                      gx=f"{px * TINY_W / 100 / DEG_PX:.5f}",
                      gy=f"{-py * TINY_W / 100 / DEG_PX:.5f}"))
assert len(atlas) == 11
write_atomic(OUT / "balloon_atlas.csv", pd.DataFrame(atlas).to_csv(index=False))



print(len(rows))          # header + footer + credit + sparkles
raise SystemExit("chunk done")

# 5  ASSERTS: before the conversion
canvas = pd.DataFrame(rows)                              # first line: the only build
rows_at_build = len(rows)

REQUIRED = [
            ("text", "text:foot"),
            ("back", "sparkle:"),
            ("text", "text:credit_name"), ("text", "text:credit_lead"), ("back", "back:credit_shadow")]

for layer, prefix in REQUIRED:
    assert ((canvas.layer == layer) & canvas.poly_id.str.startswith(prefix)).any(), f"missing {layer}:{prefix}"

sizes = canvas.groupby(["layer", "poly_id"]).agg(w=("x_px", lambda s: s.max() - s.min()), h=("y_px", lambda s: s.max() - s.min()))
assert (sizes.w > 0).all() and (sizes.h > 0).all()      # no zero-width or zero-height shape
assert canvas.x_px.between(0, W).all() and canvas.y_px.between(0, H_PX).all()

assert len(canvas) < 120_000

# 6  CONVERT then WRITE
assert len(rows) == rows_at_build                       # nothing was drawn after the section 5 snapshot

canvas["lon"] = (canvas.x_px - W / 2) / DEG_PX
canvas["lat"] = (H_PX / 2 - canvas.y_px) / DEG_PX

# two independent checks
assert ((canvas.lon * DEG_PX + W / 2) - canvas.x_px).abs().max() < 1e-9      # round trip, x
assert ((H_PX / 2 - canvas.lat * DEG_PX) - canvas.y_px).abs().max() < 1e-9   # round trip, y
assert canvas.lon.abs().max() <= W / 2 / DEG_PX + 1e-9 and canvas.lat.abs().max() <= H_PX / 2 / DEG_PX + 1e-9
assert canvas.lon.abs().max() < 180 and canvas.lat.abs().max() < 90          # what MAKEPOINT accepts

COLUMNS = ["layer", "poly_id", "point_order", "lat", "lon", "color"]
out = canvas[COLUMNS].reset_index(drop=True)
write_atomic(OUT / "balloon_canvas.csv", out.to_csv(index=False))

check = pd.read_csv(OUT / "balloon_canvas.csv", dtype={"color": str})
pd.testing.assert_frame_equal(check, out, check_exact=False, rtol=1e-9)