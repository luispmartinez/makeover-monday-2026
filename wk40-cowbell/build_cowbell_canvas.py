import pandas as pd

from PIL import Image, ImageDraw, ImageFont
from paths_local import OUT, FONTS_DIR, write_atomic
import textwrap

W, H, SCALE = 1000, 2100, 3                # design px; render at 3x
PAL = {"bg": "#150E3A", "ink": "#F8FAFC", "no1": "#F59E0B", "top10": "#0EA5E9",
       "hot": "#D946EF", "never": "#3C298F", "band": "#E11D48"}

# 1. DATA
df = pd.read_csv(OUT / "cowbell_stage2.csv")
df = df[df["Is Song"]].copy()
assert len(df) == 655
assert df["charted"].sum() == 303
assert df["Is No 1"].sum() == 54
assert df["Is Top 10"].sum() == 160
g = df.groupby("Artist").agg(songs=("Title", "size"), charted=("charted", "sum"),
                             no1=("Is No 1", "sum"), top10=("Is Top 10", "sum"))
top8  = list(g[g["songs"] >= 6].sort_index().sort_values("songs", ascending=False, kind="stable").index)
hits4 = list(g.sort_values(["no1", "top10", "charted"], ascending=False).head(4).index)
lo, hi = int(g.loc[hits4, "songs"].min()), int(g.loc[hits4, "songs"].max())
assert len(top8) == 8 and set(hits4) == {"Sly and The Family Stone", "Rolling Stones", "Duran Duran", "Prince"}
assert (lo, hi) == (3, 5)
assert (int(g.loc[top8, "charted"].sum()), int(g.loc[top8, "songs"].sum())) == (18, 55)

# 2. HELPERS
def font(name, size):
    return ImageFont.truetype(str(FONTS_DIR / name), size * SCALE)

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

TB_FONT = ImageFont.truetype(str(FONTS_DIR / "OpenSans-Regular.ttf"), 1000)   # measured at 1000, scaled down
TB_PX   = 12.35                                                                # Tableau label size, fitted from the screenshots

def tb_w(text, bold=False):
    return TB_FONT.getlength(text) / 1000 * TB_PX * (1.035 if bold else 1.0)

def tb_wrap(text, max_w):
    lines, line = [], ""
    for word in text.split():
        trial = (line + " " + word).strip()
        if tb_w(trial) <= max_w:
            line = trial
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return lines

def add_text(recs, layer, x_px, y_px, text, anchor="center", bold=False, **extra):
    w  = tb_w(text, bold)
    cx = {"center": x_px, "left": x_px + w / 2, "right": x_px - w / 2}[anchor]
    recs.append({"layer": layer, "lon": (cx - W / 2) / U, "lat": (H / 2 - y_px) / U, "text": text, **extra})

def badge(text, x, y, fill, ink, size=84, pad=22, tilt=4):
    f  = font("Anton-Regular.ttf", size)
    bw = int(draw.textlength(text, font=f) / SCALE + 2 * pad)
    bh = int(size * 1.1)
    layer = Image.new("RGBA", (bw * SCALE, bh * SCALE), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.rectangle((0, 0, bw * SCALE, bh * SCALE), fill=fill)
    ld.text((pad * SCALE, 2 * SCALE), text, font=f, fill=ink)
    layer = layer.rotate(tilt, expand=True, resample=Image.BICUBIC)
    img.alpha_composite(layer, (int(x * SCALE), int((y - 6) * SCALE)))
    return bw

# 3. CANVAS LAYOUT
img  = Image.new("RGBA", (W * SCALE, H * SCALE), PAL["bg"])
draw = ImageDraw.Draw(img)

# 4. TOP
y = 40
y = put("MAKEOVER MONDAY · WEEK 40 · COWBELL", "BarlowCondensed-SemiBold.ttf", 15, 40, y, PAL["top10"])
y = put("MOST COWBELL SONGS NEVER MADE THE HOT 100.", "Anton-Regular.ttf", 78, 40, y + 40, PAL["ink"],
        max_w=920, step=80, shadow=(5, 5, PAL["band"]))
y = put("One dot is one song. A lit dot reached Billboard's Hot 100. Brighter means a higher peak.",
        "BarlowCondensed-Medium.ttf", 21, 40, y + 14, "#D8D5F5", max_w=720, step=28)
nums = [(int(df["charted"].sum()),  f"of {len(df)} songs reached the Hot 100", PAL["hot"]),
        (int(df["Is Top 10"].sum()), "made the Top 10",                         PAL["top10"]),
        (int(df["Is No 1"].sum()),   "hit No. 1",                               PAL["no1"])]
x = 40
for n, label, color in nums:
    put(str(n), "Anton-Regular.ttf", 84, x, y, color)
    put(label, "BarlowCondensed-Medium.ttf", 20, x, y + 100, PAL["ink"])
    w = max(draw.textlength(str(n), font=font("Anton-Regular.ttf", 84)),
            draw.textlength(label, font=font("BarlowCondensed-Medium.ttf", 20))) / SCALE
    x += w + 56
    
# 5. WALL OF DOTS
y += 100 + 20
BEAT_GAP, DOT_GAP, COLS, BEATS = 14, 4, 40, 10
beat_w = (920 - (BEATS - 1) * BEAT_GAP) / BEATS
dot_d  = (beat_w - 3 * DOT_GAP) / 4          # 4 dots per beat
rows   = -(-len(df) // COLS)                    # ceiling division
wall_top    = y + 30
wall_h      = rows * dot_d + (rows - 1) * DOT_GAP
wall_bottom = wall_top + wall_h
print(f"dot {dot_d:.2f}px  rows {rows}  wall {wall_top:.0f}..{wall_bottom:.0f}")

peak = df["peak"]
n1     = int((peak == 1).sum())                     # 54
n10    = int(((peak >= 2) & (peak <= 10)).sum())    # 106
n100   = int(((peak >= 11) & (peak <= 100)).sum())  # 143
nnever = int((~df["charted"]).sum())                # 352
assert n1 + n10 + n100 + nnever == len(df)

U = 200                                    # design px per MAKEPOINT unit
ws = df.assign(_k=df["peak"].fillna(999)).sort_values(["_k", "Artist", "Title"]).reset_index(drop=True)


rows_out = []
for i, r in ws.iterrows():
    row, col = divmod(i, COLS)
    beat, k  = divmod(col, 4)
    x = 40 + beat * (beat_w + BEAT_GAP) + k * (dot_d + DOT_GAP) + dot_d / 2
    yy = wall_top + row * (dot_d + DOT_GAP) + dot_d / 2
    rows_out.append({"layer": "wall_dot", "lon": (x - W / 2) / U, "lat": (H / 2 - yy) / U,
                     "peak": r["peak"], "weeks": r["weeks"], "artist": r["Artist"], "title": r["Title"]})
wall = pd.DataFrame(rows_out)
assert len(wall) == 655
assert not wall.duplicated(["lon", "lat"]).any()
assert wall["lon"].max() <= (W - 40 - W / 2) / U
assert wall["lat"].min() >= (H / 2 - wall_bottom) / U
print(f"wall dots {len(wall)}   lon {wall['lon'].min():.3f}..{wall['lon'].max():.3f}   lat {wall['lat'].min():.3f}..{wall['lat'].max():.3f}")

def tier(p):
    if pd.isna(p):
        return "never"
    if p == 1:
        return "no1"
    if p <= 10:
        return "top10"
    return "hot"

wall["tier"] = wall["peak"].map(tier)
wall["fill"] = wall["tier"].map(PAL)
counts = wall["tier"].value_counts().to_dict()
assert counts == {"no1": 54, "top10": 106, "hot": 143, "never": 352}

def tip(r):
    if pd.isna(r["peak"]):
        return f'{r["artist"]}||{r["title"]}||Never reached the Hot 100'
    return f'{r["artist"]}||{r["title"]}||Peak {int(r["peak"])} · {int(r["weeks"])} weeks'

wall["tip"] = wall.apply(tip, axis=1)
assert (wall["tip"].str.count(r"\|\|") == 2).all()

rp = wall[wall["title"].str.contains("Reaper")]
assert len(rp) == 1
reaper = rp.assign(layer="reaper")

print(wall["tier"].value_counts().to_string())

# 5b. LEGEND (static, drawn in the PNG)
y = wall_bottom + 26
items = [("No. 1",         n1,     PAL["no1"]),
         ("Top 10",        n10,    PAL["top10"]),
         ("Hot 100",       n100,   PAL["hot"]),
         ("Never charted", nnever, PAL["never"])]
x = 40
for label, n, color in items:
    draw.ellipse(((x) * SCALE, (y) * SCALE, (x + 16) * SCALE, (y + 16) * SCALE), fill=color)
    text = f"{label} · {n}"
    put(text, "BarlowCondensed-Medium.ttf", 17, x + 24, y - 2, PAL["ink"])
    x += 24 + draw.textlength(text, font=font("BarlowCondensed-Medium.ttf", 17)) / SCALE + 28
r0 = rp.iloc[0]
draw.ellipse(((x - 3) * SCALE, (y - 3) * SCALE, (x + 19) * SCALE, (y + 19) * SCALE),
             outline=PAL["ink"], width=2 * SCALE)
draw.ellipse((x * SCALE, y * SCALE, (x + 16) * SCALE, (y + 16) * SCALE), fill=PAL["hot"])
put(f'{r0["title"]} · peak {int(r0["peak"])}', "BarlowCondensed-Medium.ttf", 17, x + 24, y - 2, PAL["ink"])
y += 16 + 14

print(f"y after legend: {y:.0f}")


LEG_CY  = wall_bottom + 26 + 8                  # swatch center (swatch is 16 px)
TIERS   = ["no1", "top10", "hot", "never"]
leg_recs = []
x = 40
for key, (label, n, color) in zip(TIERS, items):
    leg_recs.append({"layer": "legend_dot", "lon": (x + 8 - W / 2) / U, "lat": (H / 2 - LEG_CY) / U, "tier": key})
    text = f"{label} · {n}"
    tw = tb_w(text)
    leg_recs.append({"layer": "legend_text", "lon": (x + 24 + tw / 2 - W / 2) / U, "lat": (H / 2 - LEG_CY) / U, "text": text})
    x += 24 + tw + 28

rtext = f'{r0["title"]} · peak {int(r0["peak"])}'
rtw   = tb_w(rtext)
rlon  = (x + 8 - W / 2) / U                       # center of the 16 px swatch
rlat  = (H / 2 - LEG_CY) / U

leg_recs.append({"layer": "legend_ring", "lon": rlon, "lat": rlat})
leg_recs.append({"layer": "legend_dot",  "lon": rlon, "lat": rlat, "tier": "hot"})
leg_recs.append({"layer": "legend_text", "lon": (x + 24 + rtw / 2 - W / 2) / U, "lat": rlat, "text": rtext})

legd = pd.DataFrame(leg_recs)
legd["fill"] = legd["tier"].map(PAL)
assert legd["layer"].value_counts().to_dict() == {"legend_dot": 5, "legend_text": 5, "legend_ring": 1}
assert legd["lon"].max() <= (W - 40 - W / 2) / U

# 6. BAND
BAND_TOP = y + 40
head = "MORE COWBELL DID NOT MEAN MORE HITS."
t8c, t8s = int(g.loc[top8, "charted"].sum()), int(g.loc[top8, "songs"].sum())
sub = (f"The eight artists with the most cowbell songs placed {t8c} of {t8s} on the Hot 100. "
       f"The four artists with the most No. 1s needed only {lo} to {hi} songs each. "
       "The number under a dot is its peak.")
n_h = len(wrap(draw, head, font("Anton-Regular.ttf", 52), 920 * SCALE))
n_s = len(wrap(draw, sub, font("BarlowCondensed-Medium.ttf", 21), 780 * SCALE))
band_h = 34 + n_h * 54 + 24 + n_s * 28 + 52
draw.polygon([(0, BAND_TOP * SCALE), (W * SCALE, BAND_TOP * SCALE),
              (W * SCALE, (BAND_TOP + band_h * 0.86) * SCALE), (0, (BAND_TOP + band_h) * SCALE)],
             fill=PAL["band"])
yb = put(head, "Anton-Regular.ttf", 52, 40, BAND_TOP + 34, "#FFFFFF", max_w=920, step=54)
put(sub, "BarlowCondensed-Medium.ttf", 21, 40, yb + 24, "#FFFFFF", max_w=780, step=28)
y = BAND_TOP + band_h
assert y <= H, f"layout runs past the board: {y} > {H}"
print(f"band {BAND_TOP:.0f}..{y:.0f}   head lines {n_h}   sub lines {n_s}")


# 7. ROWS
ROW_X0, ROW_DOT, ROW_GAP, ROW_STEP = 300, 34, 10, 62
y += 30
row_recs, label_recs = [], []                                                  # new: label_recs
for grp, label, names in (("most", "MOST COWBELL SONGS", top8), ("hits", "MOST NO. 1 HITS", hits4)):
    put(label, "BarlowCondensed-SemiBold.ttf", 15, ROW_X0, y, PAL["top10"])
    add_text(label_recs, "group_label", ROW_X0, y + 8, label, anchor="left", bold=True)        # new
    y += 34
    for a in names:
        songs = ws[ws["Artist"] == a].sort_values(["_k", "Title"])
        cy = y + ROW_DOT / 2
        nm_w = draw.textlength(a, font=font("BarlowCondensed-SemiBold.ttf", 20)) / SCALE
        put(a, "BarlowCondensed-SemiBold.ttf", 20, ROW_X0 - 16 - nm_w, cy - 11, PAL["ink"])
        add_text(label_recs, "row_label", ROW_X0 - 16, cy, a, anchor="right")        # new
        for j, (_, s) in enumerate(songs.iterrows()):
            cx = ROW_X0 + j * (ROW_DOT + ROW_GAP) + ROW_DOT / 2
            row_recs.append({"layer": "row_dot", "lon": (cx - W / 2) / U, "lat": (H / 2 - cy) / U,
                             "peak": s["peak"], "weeks": s["weeks"], "artist": a, "title": s["Title"], "group": grp})
            if pd.notna(s["peak"]):
                lab = str(int(s["peak"]))
                lw = draw.textlength(lab, font=font("BarlowCondensed-Medium.ttf", 14)) / SCALE
                put(lab, "BarlowCondensed-Medium.ttf", 14, cx - lw / 2, cy + ROW_DOT / 2 + 4, PAL["ink"])
                add_text(label_recs, "peak_label", cx, cy + ROW_DOT / 2 + 11, lab)    # new
        tally_txt = f'{int(songs["charted"].sum())} of {len(songs)}'                  # new
        tx = ROW_X0 + len(songs) * (ROW_DOT + ROW_GAP) + 10                           # new
        put(tally_txt, "BarlowCondensed-Medium.ttf", 18, tx, cy - 9, "#D8D5F5")
        add_text(label_recs, "tally", tx, cy, tally_txt, anchor="left")      # new
        y += ROW_STEP
    y += 20

rowd = pd.DataFrame(row_recs)
rowd["tier"] = rowd["peak"].map(tier)
rowd["fill"] = rowd["tier"].map(PAL)
rowd["tip"]  = rowd.apply(tip, axis=1)
assert rowd["group"].value_counts().to_dict() == {"most": 55, "hits": 16}
assert not rowd.duplicated(["lon", "lat"]).any()
assert rowd["lon"].max() <= (W - 40 - W / 2) / U
print(f"rows end {y:.0f}")

# 8. FOOTER
y += 10
y_foot = y
foot1 = ("Charted means the song reached Billboard's Hot 100. Many album-rock tracks got airplay without a Hot 100 spot. "
         "Matching is by song, not recording; peak is the best Hot 100 position (1 is best). "
         "Bottom group: the four artists with the most No. 1s, ties broken by Top 10s. "
         "They are picked for hits, so their rate is not comparable to the top group.")
foot2 = ("Source: Makeover Monday 2026 week 40 song list; Billboard Hot 100 history "
         "(utdata/rwd-billboard-data, CC BY). Luis Pablo Martinez")
y = put(foot1, "BarlowCondensed-Medium.ttf", 14, 40, y, "#BDB8E8", max_w=880, step= 18)
y = put(foot2, "BarlowCondensed-Medium.ttf", 14, 40, y + 6, "#BDB8E8", max_w=880, step= 14)
y_end = y + 30
assert y_end <= H, f"layout runs past the board: {y_end} > {H}"
print(f"footer ends {y_end:.0f} of {H}")




labd = pd.DataFrame(label_recs)
vc = labd["layer"].value_counts().to_dict()
assert vc["row_label"] == 12 and vc["tally"] == 12 and vc["group_label"] == 2 and vc["peak_label"] == 32
assert labd["lat"].min() >= -H / 2 / U


# 9. SLICES -- two static strips + two sheet windows
STRIP1_H  = int(wall_top - 14)          # top PNG: kicker, headline, subtitle, the three big numbers
BAND_Y0   = int(BAND_TOP)               # band PNG starts where the legend ends
BAND_Y1   = int(BAND_TOP + band_h)
SHEET1_H  = BAND_Y0 - STRIP1_H          # sheet 1: wall + legend
SHEET2_Y0 = BAND_Y1
SHEET2_H  = H - SHEET2_Y0               # sheet 2: rows + labels + footer
assert STRIP1_H + SHEET1_H + (BAND_Y1 - BAND_Y0) + SHEET2_H == H

img.crop((0, 0, W * SCALE, STRIP1_H * SCALE)).save(OUT / "cowbell_headline.png")
img.crop((0, BAND_Y0 * SCALE, W * SCALE, BAND_Y1 * SCALE)).save(OUT / "cowbell_band.png")
FOOT_Y0 = int(y_foot - 12)
FOOT_Y1 = int(y_end)
img.crop((0, FOOT_Y0 * SCALE, W * SCALE, FOOT_Y1 * SCALE)).save(OUT / "cowbell_footer.png")
latF = ((H / 2 - FOOT_Y0) / U, (H / 2 - FOOT_Y1) / U)
print(f"footer png {FOOT_Y0}..{FOOT_Y1}   lat {latF[1]:.3f}..{latF[0]:.3f}")
print(f"wrote {OUT / 'cowbell_headline.png'}, {OUT / 'cowbell_band.png'}")

lat1 = ((H / 2 - STRIP1_H) / U,  (H / 2 - BAND_Y0) / U)     # sheet 1 top, bottom
lat2 = ((H / 2 - SHEET2_Y0) / U, -H / 2 / U)                    # sheet 2 top, bottom
frames = pd.DataFrame([
    {"layer": "frame_s1", "lon": -W / 2 / U, "lat": lat1[0]},
    {"layer": "frame_s1", "lon":  W / 2 / U, "lat": lat1[1]},
    {"layer": "frame_s2", "lon": -W / 2 / U, "lat": lat2[0]},
    {"layer": "frame_s2", "lon":  W / 2 / U, "lat": lat2[1]},
])

# 10. EXPORT
canvas = pd.concat([wall, rowd, reaper, legd, labd, frames], ignore_index=True)
canvas.insert(0, "id", range(1, len(canvas) + 1))
assert canvas["id"].is_unique
expected = {"wall_dot": 655, "row_dot": 71, "reaper": 1, "legend_dot": 5, "legend_text": 5,
            "legend_ring": 1, "group_label": 2, "row_label": 12, "peak_label": 32, "tally": 12,
            "frame_s1": 2, "frame_s2": 2}
assert canvas["layer"].value_counts().to_dict() == expected
print(canvas.groupby("layer").size().to_string())
write_atomic(canvas, "cowbell_canvas.csv")

img.save(OUT / "cowbell_background.png")
prev = img.copy()
pd_ = ImageDraw.Draw(prev)
for df_, d in ((wall, dot_d), (rowd, ROW_DOT)):
    for _, r in df_.iterrows():
        cx = (r["lon"] * U + W / 2) * SCALE
        cy = (H / 2 - r["lat"] * U) * SCALE
        rad = d / 2 * SCALE
        pd_.ellipse((cx - rad, cy - rad, cx + rad, cy + rad), fill=r["fill"])
prev.save(OUT / "cowbell_preview.png")
print(f"wrote {OUT / 'cowbell_background.png'}  {img.size[0]}x{img.size[1]} px")
print(f"wrote {OUT / 'cowbell_preview.png'}")
