# wk42: US state population, 1790-1990

Makeover Monday 2026, week 42. Two views of the same 51 bars, one switch.

**Poster:** [Tableau Public](ADD-LINK-HERE)

## What it shows

Each bar is a state's best census, ranked two ways:

- **Fast isn't big.** Peak percent growth from one census to the next. The top of the list is small territories: Minnesota +2,731% in 1860, from 6,077 people.
- **Big isn't fast.** Peak share of the US population. The top of the list is the early giants: Virginia 17.6% in 1790.

Virginia is first by share and last by growth. 42 of the 51 states move 8 or more places between the two rankings, and the rank correlation between them is -0.23.

The duel: Indiana grew 2.7x faster than California (+832% in 1810, from 2,632 people), and California added 13x the people (+287,397 in 1860).

## How the numbers are made

`explore_us_pop.py` (Stage 2) reads the state populations and writes the two hand-off tables the poster is drawn from:

- `us_pop_stage2.csv`: one row per state per view (102 rows): peak value, peak year, both ranks, the move between them, the starting population, and the label text.
- `us_pop_duel.csv`: the Indiana and California numbers.

Definitions:

- **Growth** is the percent change from one census to the next. A state's first census has no growth, so its peak comes later.
- **Share** is a state's population as a percent of the states counted in that census.
- **Bright bars** started with under 25,000 people at the census before their peak growth (16 states). Small starting bases inflate percent growth, and that is the trap the poster is about.

Every number on the poster is asserted in the script (row counts, census totals, ranks, the Indiana and California figures).

## Run it

```
pip install pandas numpy scipy
python3 explore_us_pop.py
```

It expects `drop/us_state_population_1790_1990.csv` (state, year, population: 886 rows, 51 entities, 21 censuses). The data file is not included. Outputs go to `~/TableauData/wk42-us-pop/`.

## Notes

- Data: Makeover Monday 2026, week 42. Inspired by Hewes and Gannett's 1883 statistical atlas of the 1880 census, via the Library of Congress Maps blog.
- The script that turns these tables into the Tableau geometry is kept private.
- Built with AI assistance.
