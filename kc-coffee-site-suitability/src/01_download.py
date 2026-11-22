"""Download the public inputs this model adds on top of project 1's raw data.

- ACS 2014-2018 tract population (base for population growth)      -> needs CENSUS_API_KEY
- Census 2010->2020 tract relationship file (crosswalk for growth)
- 2023 cartographic-boundary tract polygons (KS, MO)
- LEHD LODES 2023 workplace jobs by block (daytime workers)
Each file is skipped if it already exists, so re-runs are cheap.
"""
import json, os, sys
import pandas as pd, requests
from config import RAW, DQ_RAW, COUNTIES, STATES, GROWTH_BASE_YEAR, LODES_YEAR, ACS_YEAR

UA = {"User-Agent": "kc-coffee-site-suitability/1.0"}

def fetch(url, dest):
    if dest.exists():
        print(f"  have {dest.name}"); return
    print(f"  get  {url}")
    r = requests.get(url, headers=UA, timeout=300); r.raise_for_status()
    dest.write_bytes(r.content)

def acs_base_population():
    dest = RAW / f"acs_{GROWTH_BASE_YEAR}_pop.json"
    if dest.exists():
        print(f"  have {dest.name}"); return
    key = os.environ.get("CENSUS_API_KEY")
    if not key:
        raise SystemExit("CENSUS_API_KEY is not set. Get a free key at https://api.census.gov/data/key_signup.html, "
                         "then in PowerShell run: $env:CENSUS_API_KEY = 'your_key'")
    rows = []
    for st, co, label in COUNTIES:
        url = (f"https://api.census.gov/data/{GROWTH_BASE_YEAR}/acs/acs5?get=B01003_001E"
               f"&for=tract:*&in=state:{st}&in=county:{co}&key={key}")
        r = requests.get(url, headers=UA, timeout=60); r.raise_for_status()
        if "json" not in r.headers.get("content-type", ""):
            raise SystemExit(f"Census API did not return JSON (invalid key?): {r.text[:200]}")
        header, *body = r.json()
        rows += [dict(zip(header, b)) for b in body]
        print(f"  {label}: {len(body)} tracts ({GROWTH_BASE_YEAR}, 2010 geography)")
    dest.write_text(json.dumps(rows))

def tract_crosswalk():
    dest = RAW / "tract_rel_2020_2010_ksmo.csv"
    if dest.exists():
        print(f"  have {dest.name}"); return
    url = "https://www2.census.gov/geo/docs/maps-data/data/rel2020/tract/tab20_tract20_tract10_natl.txt"
    print(f"  get  {url}")
    rel = pd.read_csv(url, sep="|", dtype=str, encoding="utf-8-sig", storage_options=UA)
    keep = rel["GEOID_TRACT_20"].str[:2].isin(STATES)  # national file is ~19 MB; keep KS + MO only
    rel[keep].to_csv(dest, index=False)

if __name__ == "__main__":
    missing = [f for f in ("acs_tracts.json", "osm_cafes.json") if not (DQ_RAW / f).exists()]
    if missing:
        sys.exit(f"Project 1 raw files not found in {DQ_RAW}: {missing}. Run project 1's 01_download.py "
                 "or set KC_DQ_PROJECT to its folder.")
    print("Tract boundaries"); [fetch(f"https://www2.census.gov/geo/tiger/GENZ{ACS_YEAR}/shp/cb_{ACS_YEAR}_{st}_tract_500k.zip",
                                      RAW / f"cb_{ACS_YEAR}_{st}_tract_500k.zip") for st in STATES]
    print("LODES workplace jobs"); [fetch(f"https://lehd.ces.census.gov/data/lodes/LODES8/{s}/wac/{s}_wac_S000_JT00_{LODES_YEAR}.csv.gz",
                                         RAW / f"{s}_wac_S000_JT00_{LODES_YEAR}.csv.gz") for s in STATES.values()]
    print("2010->2020 tract crosswalk"); tract_crosswalk()
    print(f"ACS {GROWTH_BASE_YEAR} population"); acs_base_population()
