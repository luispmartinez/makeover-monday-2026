from title_glyphs import TitleFont
from toolkit.scan_and_profile import HERE
FONTS_DIR = HERE / "fonts"
TEXT, SIZE = "More AI. Same scores.", 44
for name in ["Anton-Regular", "Shrikhand-Regular", "Bungee-Regular", "Righteous-Regular"]:
    f = TitleFont(FONTS_DIR / f"{name}.ttf")
    rings = f.rings(TEXT, 50, 80, SIZE)
    print(name, "vertices:", sum(len(pts) for _, pts in rings), "width:", round(f.width(TEXT, SIZE)))