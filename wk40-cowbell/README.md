# Week 40 · Cowbell

![dashboard](screenshots/cowbell.png)

**Tableau Public:** (https://public.tableau.com/views/Cowbell/Cowbell?:language=en-US&:sid=&:redirect=auth&:display_count=n&:origin=viz_share_link)

A crowd-sourced list of 655 "cowbell" songs for Makeover Monday 2026 week 40, joined to the
Billboard Hot 100 to ask one question: did the songs people remember for cowbell chart?

## The finding

- 303 of 655 songs (46.3%) reached the Hot 100. 160 made the Top 10. 54 hit No. 1.
- The eight artists with six or more songs charted 18 of 55 (32.7%); everyone else, 285 of 600 (47.5%).
- The four artists with the most No. 1s (Sly and The Family Stone, Rolling Stones, Duran Duran, Prince) needed only three to five songs each.

"Charted" means a Hot 100 entry for the same song. Many album-rock tracks got airplay without one.

## How it is built

Python decides, Tableau paints. Every position, color, label and tooltip string is computed in
Python and written to one CSV; Tableau draws marks from it with `MAKEPOINT`.

| Stage | Script | Output |
|---|---|---|
| 1. Clean | `build_cowbell_clean.py` | `cowbell_songs_clean.csv` |
| 2. Join to the Hot 100 | `explore_billboard_match.py` | `cowbell_stage2.csv` |
| 3. Canvas | `build_cowbell_canvas.py` | `cowbell_canvas.csv` + background PNGs |

Every number printed on the dashboard is asserted against the data in the script that draws it.
Static type (headline, band, footer) is rendered to PNG in Python because Tableau handles
custom fonts unreliably; only dots, labels and tooltips are Tableau marks.

## Decisions

<!-- Write these in your own words. Suggested headings: -->
- **Matching.** Keys ignore case, punctuation, a leading "The", and treat "&" as "and". Hand-reviewed overrides live in `lookups/` (title mismatches and credit variants). Every override was checked against MusicBrainz.
- **Left as submitted:** the "The" prefix on artist names, and Funkadelic / Parliament Funkadelic.
- **No genre column.** <!-- your reason -->
- **Bottom group is picked for hits,** so its hit rate is not comparable to the top group.

## Reproduce

```
python -m venv .venv && source .venv/bin/activate
pip install -r ../requirements.txt
sh fetch_fonts.sh
cp paths_local.example.py paths_local.py        # then edit OUT if you want
# download into drop/:
#   MM2026_wk40.xlsx        (Makeover Monday week 40)
#   hot-100-current.csv     (https://github.com/utdata/rwd-billboard-data, data-out/)
python build_cowbell_clean.py
python explore_billboard_match.py
python build_cowbell_canvas.py
```

To run stage 3 only, use the committed `cowbell_stage2.csv` and skip the downloads.

## Credits

- Makeover Monday, Andy Kriebel, Next Level Tableau.
- Billboard Hot 100 history: [utdata/rwd-billboard-data](https://github.com/utdata/rwd-billboard-data), CC BY.
- Fonts: Anton, Barlow Condensed, Open Sans (SIL Open Font License).
