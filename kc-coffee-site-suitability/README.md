# KC Metro Coffeehouse Site-Suitability Ranking

**Question:** Which Kansas City metro census tracts are the strongest candidates for a new coffeehouse?

**Data:** 551 census tracts in Johnson and Wyandotte (KS) and Jackson, Clay, Platte and Cass (MO). ACS 5-year estimates (2014-18 and 2019-23), LEHD LODES 2023 workplace jobs, OpenStreetMap cafes and road network. Public data only, not company data.

**Tools:** Python (GeoPandas, OSMnx, SciPy), R Shiny + Leaflet.

**Builds on:** [kc-coffee-data-quality](../kc-coffee-data-quality), the profile that found the problems this model fixes before scoring.

**Decision memo:** [jump to the one-page recommendation](#decision-memo-where-to-open-the-next-5-coffeehouses-in-kc-and-why) written from this model for a non-technical reader.

## Run it
```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
$env:CENSUS_API_KEY = "your_key"           # free: api.census.gov/data/key_signup.html
.venv\Scripts\python src/01_download.py     # boundaries, jobs, crosswalk, 2014-18 population
.venv\Scripts\python src/02_clean.py        # applies the data quality report's fixes
.venv\Scripts\python src/03_features.py     # population growth, daytime workers
.venv\Scripts\python src/04_drive_times.py  # road network + 10-minute trade areas (first run ~10 min)
.venv\Scripts\python src/05_score.py        # percentiles, weighted score, exports
.venv\Scripts\python src/06_recommend.py    # five spaced-out picks + weighting robustness (for the memo)
.venv\Scripts\python src/07_export_site.py  # slimmed map data for the portfolio site (../assets)
Rscript -e "shiny::runApp('shiny')"         # needs shiny, bslib, leaflet, sf, dplyr
```
Project 1's raw downloads are read from `../kc-coffee-data-quality/data/raw` (override with `KC_DQ_PROJECT`).

## Scoring
Each factor is converted to a percentile rank across the 537 scored tracts, then combined as a weighted average and scaled to 0-100.

| Factor | Measure | Source | Default weight |
|---|---|---|---|
| Income | Median household income | ACS 2019-23 | 25% |
| Population growth | % change in residents, 2014-18 to 2019-23 | ACS, 2010 tracts moved onto 2020 tracts with the Census relationship file (land-area weights) | 15% |
| Daytime workers | Jobs located in the tract, per square mile | LODES 2023 (WAC, all jobs) | 20% |
| Drive time | Residents within a 10-minute drive of the tract | OSM road network, free-flow speeds | 20% |
| Competitor density | Coffee competitors per 10k residents within that 10-minute drive (lower is better) | OSM cafes, cleaned | 20% |

Percentile ranks rather than raw values are used because the income top-code ($250,001), a handful of downtown tracts with 60,000+ jobs per square mile, and fast-growing tracts that started near zero would otherwise dominate the score. In the Shiny app the weights are sliders: the ranking updates as they move.

**How drive time is measured.** Each tract's candidate site is an interior point snapped to the nearest road. Dijkstra on the reversed road graph gives the time to drive *to* that site from everywhere. Neighbouring tracts whose interior point is within 10 minutes count toward its trade area. The network extends 8 km past the county line so trips near the edge can route outside it.

## Data quality fixes applied (from project 1)
`src/02_clean.py` prints each check next to the number the report found. All match.

| Report recommendation | What this pipeline does | Result |
|---|---|---|
| 1. Sentinel codes to NULL | Any negative income, population or home value becomes missing | 21 tracts (report: 21) |
| 2. Exclude empty tracts, flag missing income | 14 zero-population tracts are shown grey and not scored. 7 populated tracts with suppressed income get the median income of the tracts around them and are flagged in the map popup | 14 excluded, 7 filled (6,608 residents) |
| 3. Standardise cafe names | `data/reference/cafe_name_map.csv` maps spelling variants and sets chain / independent / non-coffee | Scooter's 30, Dutch Bros 14 (report: 30, 14) |
| 4. Deduplicate, trim whitespace | Same standardised name within 50 m collapses to one point | 3 removed: 7 Brew (found in the report), plus Revocup and Overflow, which were mapped twice under different spellings |
| 5. Handle the income top-code | Percentile scoring; top-coded tracts flagged | 2 tracts flagged |

The name map also marks 23 places tagged as cafes in OSM that are not coffee competitors (BBQ and gyro restaurants, bubble tea, juice and cookie shops). They are left out of competitor counts.

## Findings (default weights)
1. **The top 15 tracts are all in Johnson County.** 14 of 15 have median incomes of $100K-$190K, most grew 5-30% since 2014-18, and all reach 155,000-311,000 residents within a 10-minute drive. The exception at #12 ($73K, +149%) is a fast-growing tract with dense jobs.
2. **Those areas are not empty of coffee.** The leaders still have 22-57 competitors within 10 minutes. They rank high because the number of residents per competitor is high, not because there are no cafes.
3. **The ranking depends on the weights.** With only daytime workers and low competition (50/50), the top five move to the urban core of Jackson County and Wyandotte (tracts 174, 126, 117.01, 124 in Jackson; 441.01 in Wyandotte). The suburban result reflects how heavily income and growth are weighted.
4. **Drive-time reach is wide.** The median tract reaches about 144,000 residents in 10 minutes, and the nearest competitor is a median 2.8 minutes away. Free-flow speeds overstate reach at rush hour, so treat reach as relative, not literal.

Outputs: `data/processed/tracts_scored.geojson` (map layer), `tracts_scored.csv` (every factor, percentile and flag) and `cafes.geojson`.

## Limitations
- **Area-weighted growth.** Where a 2010 tract was split, its population is divided by land area, not by where people actually live. Population-weighted block crosswalks (NHGIS) would be more precise.
- **Coarse trade areas.** Each tract is one point; a tract counts as "in" a trade area only if that point is within 10 minutes. Large rural tracts in Cass and Platte are approximated most roughly.
- **Free-flow drive times.** No congestion, turn penalties or traffic signals.
- **Edge effects.** Residents and jobs outside the six counties (Leavenworth, Miami, Ray, Clinton) are not counted, so border tracts are understated. Cafes outside the counties but within the 8 km network buffer are counted.
- **OSM is incomplete.** The competitor count is a lower bound (project 1). ACS margins of error are not modelled.
- **Not modelled:** traffic counts, visibility, rents, zoning, and whether a site exists. This is a screen for where to look, not a site decision.

---

## Decision memo: Where to open the next 5 coffeehouses in KC, and why

**To:** Expansion leadership · **Re:** Next five Kansas City locations · **Date:** November 2026

**Bottom line.** I recommend opening the next five coffeehouses in the five areas below: four in fast-growing, high-income Johnson County suburbs and one in downtown Kansas City, Missouri. Each is at least 5 miles from the others, so the new stores will not compete with each other for the same customers.

| # | Where | Why it stands out | What to watch |
|---|---|---|---|
| 1 | **Overland Park**, W 159th St & Antioch Rd | Highest score in the metro. Household income $131K, population up 21% in five years, and about 194,000 people within a 10-minute drive, but only one coffee shop per 7,700 of them. | 20 of the 25 nearby coffee shops are chains, so speed and drive-thru convenience will decide who wins. |
| 2 | **Overland Park**, W 119th St & Nall Ave | An office hub: 36,000 jobs in the area, the most in the metro, plus $108K income and 25% growth. Morning commuters and residents. | Busy field: 43 coffee shops nearby, 26 of them chains. |
| 3 | **Lenexa**, Pflumm Rd & College Blvd | The biggest customer base of the five: about 309,000 people within a 10-minute drive. Income $113K. | Most crowded suburban pick (57 coffee shops, 39 chains) and slower growth (10%). |
| 4 | **Olathe**, S Ridgeview Rd & E 151st St | The fastest-growing suburban pick (30%), income $124K, and the fewest competitors (22). | Smallest customer base today (155,000). This one is a bet that the growth continues. |
| 5 | **Downtown Kansas City, MO**, Main St & Grand Blvd | The densest daytime crowd in the metro (12,600 jobs packed into a few blocks), and the number of residents has more than doubled. | Very competitive: 93 coffee shops nearby, almost all independents, one practically next door. Needs a different format. |

**How I chose them.** I scored all 551 neighborhoods (census tracts) in the six-county metro on five things that drive coffee sales: income, population growth, daytime workers, how many people live within a 10-minute drive, and how many coffee shops already serve them. I then took the highest-scoring areas, skipping any within 5 miles of a site already chosen. Sites 1-4 stayed in the top 25 in 78-91% of 1,000 alternative ways of weighting those five factors, so they do not depend on my exact choices. Site 5 did in 62%.

**Tradeoffs**
- **Suburbs vs. downtown.** The four suburban sites win on income, growth and drive-time reach, and are built for drive-thru traffic against chains. Downtown wins on weekday office workers and walk-in traffic, and competes against local independents. It carries more risk, but it tests a second store format and a second market.
- **Concentration.** 42 of the top 50 areas are in Johnson County. Four stores there can share managers, supply runs and marketing, but they tie most of the investment to one county's economy.
- **Proven vs. future demand.** Lenexa and the two Overland Park sites serve demand that already exists. Olathe and downtown depend on growth continuing.
- **The weights are a judgment call.** I weighted income most heavily (25%). If leadership values daytime workers more, more downtown and Jackson County sites rise; if it values income more, the list becomes almost all Johnson County.

**Risks and how to reduce them**
- **The competitor count is a floor.** Public map data misses some coffee shops, so the real competition is likely heavier. *Walk each area and count competitors before signing a lease.*
- **Drive times assume no traffic.** Rush-hour access may be worse. *Check state traffic counts and which side of the road morning commuters drive on.*
- **Office attendance.** Downtown job counts show where people are employed, not how often they come into the office. *Observe weekday morning foot traffic before committing to site 5.*
- **What the data cannot see:** rent, visibility, parking, drive-thru permits, available buildings, and where our own stores already are. *These need the real estate team.*

**Next steps.** (1) Two-week field visit to all five areas. (2) Pull listings and lease quotes near each intersection. (3) Decide the downtown format before committing. (4) Open sites 1 and 2 first: they rank highest and are the most stable under different weightings.
