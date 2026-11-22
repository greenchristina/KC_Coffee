"""Shared paths and constants for the site-suitability pipeline."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW, INTERIM, PROCESSED, REF = (ROOT / "data" / d for d in ("raw", "interim", "processed", "reference"))
for d in (RAW, INTERIM, PROCESSED):
    d.mkdir(parents=True, exist_ok=True)

# Project 1 (data quality profile) holds the raw ACS 2023 and OSM cafe downloads this model builds on.
DQ_PROJECT = Path(os.environ.get("KC_DQ_PROJECT", ROOT.parent / "kc-coffee-data-quality"))
DQ_RAW = DQ_PROJECT / "data" / "raw"

# (state FIPS, county FIPS, name): same six counties as project 1
COUNTIES = [("20", "091", "Johnson KS"), ("20", "209", "Wyandotte KS"), ("29", "095", "Jackson MO"),
            ("29", "047", "Clay MO"), ("29", "165", "Platte MO"), ("29", "037", "Cass MO")]
COUNTY_NAME = {st + co: name for st, co, name in COUNTIES}
STATES = {"20": "ks", "29": "mo"}

ACS_YEAR = 2023          # 2019-2023 ACS 5-year (project 1)
GROWTH_BASE_YEAR = 2018  # 2014-2018 ACS 5-year: does not overlap 2019-2023, as Census advises for comparisons
LODES_YEAR = 2023        # LEHD LODES8 workplace jobs, 2020 census blocks

CRS_M = "EPSG:26915"     # NAD83 / UTM 15N, metres: covers KC
INCOME_TOPCODE = 250001
CATCHMENT_MIN = 10       # drive-time trade area, minutes
SEARCH_MIN = 20          # Dijkstra cutoff (also caps "minutes to nearest cafe")
GRAPH_BUFFER_M = 8000    # road network extends past the county line so edge tracts can route outside it

# Default factor weights (the Shiny app lets users change them)
WEIGHTS = {"income": 0.25, "growth": 0.15, "workers": 0.20, "access": 0.20, "competition": 0.20}
