# Data Quality Report: KC Metro Tract and Cafe Data

**Question:** Is this public data reliable enough to support coffeehouse site-selection analysis?

| # | Check | Table | Result (fill in from SQL) | Impact | Action taken |
|---|-------|-------|---------------------------|--------|--------------|
| 1 | Duplicate tract IDs | acs_tracts | | | |
| 2 | Census sentinel values in income | acs_tracts | | Naive avg vs. clean avg: | |
| 3 | Zero-population tracts | acs_tracts | | | |
| 4 | Income outliers (1.5 x IQR) | acs_tracts | | | |
| 5 | Cafes missing name or coordinates | osm_cafes | | | |
| 6 | Duplicate cafe points (same name, ~50 m) | osm_cafes | | | |
| 7 | Inconsistent name spellings | osm_cafes | | | |

## Recommendations
1.
2.
3.

## Limitations
Public data, not company data. OpenStreetMap is volunteer-maintained and incomplete. Findings are illustrative.
