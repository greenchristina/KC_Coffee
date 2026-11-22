# Data Quality Report: KC Metro Tract and Cafe Data

**Question:** Is this public data reliable enough to support coffeehouse site-selection analysis?

**Scope:** 551 census tracts (ACS 2023 5-year, Johnson KS, Wyandotte KS, Jackson MO, Clay MO, Platte MO, Cass MO) and 327 OpenStreetMap cafe elements (206 nodes, 121 ways) inside the six-county bounding box.

| # | Check | Table | Result (from SQL) | Impact | Action taken |
|---|-------|-------|-------------------|--------|--------------|
| 1 | Duplicate tract IDs | acs_tracts | 0 duplicates (551 rows, 551 distinct GEOIDs) | None. Key is reliable. | None needed. |
| 2 | Census sentinel values in income | acs_tracts | 21 of 551 tracts (3.8%) carry -666666666 in median income; the same 21 carry it in median home value | Naive avg income: **-$25,325,790**. Clean avg: **$85,827**. Median of valid tracts: $78,555. | Convert sentinels to NULL before any aggregation. |
| 3 | Zero-population tracts | acs_tracts | 14 tracts (all with sentinel income): 4 Johnson, 6 Wyandotte, 3 Jackson, 1 Platte | No residents, so no demand signal (airports, parks, industrial). | Exclude from demand scoring. |
| 4 | Income outliers (1.5 x IQR) | acs_tracts | 14 high outliers, 0 low. Two tracts sit at the 250,001 top-code. Most outliers are in Johnson County (11 of 14). | Real affluent areas, not errors, but the top-code hides true values and will compress variation at the high end. | Keep, flag top-coded tracts, consider rank-based scoring. |
| 5 | Cafes missing name or coordinates | osm_cafes | 0 missing coordinates; 2 missing names (0.6%) | Negligible, but unnamed cafes cannot be classed as chain or independent. | Drop unnamed rows from chain analysis. |
| 6 | Duplicate cafe points (same name, ~50 m) | osm_cafes | 1 pair ("7 Brew", a node and a way at the same spot) | Small overcount of one location. | Keep one record per pair. |
| 7 | Inconsistent name spellings | osm_cafes | Case-insensitive check finds 0, but real variants exist: "Scooter's Coffee" (25), "Scooters" (3), "Scooter's Coffeehouse" (2); "Dutch Bros. Coffee" (13) vs "Dutch Bros Coffee" (1). One trailing-space name ("Filling Station "). | Chain counts split across spellings: Scooter's is 30 locations, not 25. | Standardize names with a mapping table before counting chains. |

## Additional observations
- **Seven tracts have residents but no income** (6,608 people in total, including a tract of 1,520 in Wyandotte and one of 2,561 in Jackson). These are suppressed estimates, not empty tracts. Dropping them silently removes populated areas, so treat them as unknown rather than zero.
- **Sentinels also affect home value:** naive average -$25.2M vs. clean average $268,159.
- **Brand tag is incomplete:** only 36.7% of cafes have a `brand` tag, and 12 of 30 Scooter's locations lack one. Using `brand IS NOT NULL` to find chains undercounts them.
- **Attribute completeness:** name 99.4%, street 68.2%, opening hours 39.1%.
- **Chain mix:** Starbucks is 71 of 327 cafes (22%), Scooter's about 30, Dutch Bros 14. The dataset is dominated by a few chains.
- **Coverage gap:** Wyandotte County has income for 56 of 64 tracts (88%), the lowest of the six counties.
- All coordinates fall inside the download box.

## Recommendations
1. **Convert Census sentinel codes (-666666666) to NULL before any calculation.** Left in, they turn a $86K average income into -$25M. This is the highest-impact fix.
2. **Exclude the 14 zero-population tracts from demand scoring and flag the 7 populated tracts with missing income** instead of dropping them, so low-income or small areas are not silently erased from the model.
3. **Standardize cafe names with a mapping table (for example Scooter's / Scooters / Scooter's Coffeehouse) and derive chain status from that mapping, not from the OSM `brand` tag.** Otherwise chain counts and the chain-versus-independent split are wrong.
4. **Deduplicate points (node versus way) and trim whitespace** before counting competitors per tract.
5. **Handle the 250,001 income top-code** by using rank-based or capped scoring so affluent tracts are not treated as precisely measured.

## Limitations
Public data, not company data. OpenStreetMap is volunteer-maintained and incomplete, so the cafe count is a lower bound and may miss newer or smaller shops. ACS estimates carry margins of error that were not examined here. The 50 m duplicate check only matches identical names, so duplicates entered under different names are not caught. Findings are illustrative.
