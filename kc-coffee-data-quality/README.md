# KC Metro Coffee Data Quality Profile (SQL)

**Question:** Before building a coffeehouse site-selection model, how reliable are the public inputs?

**Data:** ACS 5-year tract estimates (U.S. Census API) for six KC metro counties; cafe locations from OpenStreetMap (Overpass API). Public data only, not company data.

**Tools:** Python (requests, pandas), DuckDB, SQL.

## Run it
```
pip install -r requirements.txt
python src/01_download.py
python src/02_load_duckdb.py
duckdb kc_coffee.duckdb < sql/01_profile_acs.sql
duckdb kc_coffee.duckdb < sql/02_profile_osm.sql
```

## Findings
Profiled 551 tracts and 327 OSM cafe elements. Full table in [docs/data_quality_report.md](docs/data_quality_report.md).

1. **Census error codes wreck averages.** 21 of 551 tracts (3.8%) carry the sentinel -666666666 for median income. Left in, average income is -$25.3M instead of the true $85,827.
2. **14 tracts have zero population** (airports, parks, industrial areas), and another 7 tracts have 6,608 residents but suppressed income. These need different handling: exclude the first, flag the second.
3. **Cafe names are inconsistent.** Case-insensitive matching finds no variants, but Scooter's appears under three spellings (25 + 3 + 2 = 30 locations) and Dutch Bros under two. Counting by exact name understates chains.
4. **The OSM brand tag is incomplete.** Only 36.7% of cafes have one, and 12 of 30 Scooter's locations lack it, so "branded" undercounts chains. Starbucks alone is 71 of 327 cafes (22%).
5. **Basic integrity is good.** No duplicate tract IDs, no missing coordinates, 2 unnamed cafes, and only 1 duplicate cafe point ("7 Brew" mapped as both a node and a way).

## Recommendations
1. Convert Census sentinel codes to NULL before aggregating.
2. Drop zero-population tracts from demand scoring; flag (don't drop) populated tracts with missing income.
3. Standardize cafe names through a mapping table and derive chain status from it, not from the `brand` tag.
4. Deduplicate node/way pairs and trim whitespace before counting competitors per tract.
5. Handle the 250,001 income top-code with rank-based or capped scoring.

## Limitations
OpenStreetMap is volunteer-maintained; tract estimates carry margins of error not examined here.

## Next step
These fixes feed the site-suitability model in [kc-coffee-site-suitability](../kc-coffee-site-suitability), which scores every tract and ends in a one-page memo recommending five locations.
