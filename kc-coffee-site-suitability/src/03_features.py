"""Tract-level demand features: population growth and daytime workers.

Growth: ACS 2014-18 population sits on 2010 tract boundaries, ACS 2019-23 on 2020 boundaries.
        2010 counts are moved onto 2020 tracts with the Census relationship file, in proportion to
        the share of each 2010 tract's land area that falls in each 2020 tract.
Workers: LODES 2023 jobs located in each tract (all jobs, all workers: C000), summed from blocks.
"""
import json
import numpy as np, pandas as pd, geopandas as gpd
from config import RAW, INTERIM, STATES, GROWTH_BASE_YEAR, LODES_YEAR

tracts = gpd.read_file(INTERIM / "tracts_clean.gpkg")[["GEOID", "ALAND", "total_pop"]]

# ---------------------------------------------------------------- population growth
src = RAW / f"acs_{GROWTH_BASE_YEAR}_pop.json"
if not src.exists():
    raise SystemExit(f"{src.name} missing: set CENSUS_API_KEY and re-run src/01_download.py")
p10 = pd.DataFrame(json.load(open(src)))
p10["GEOID_TRACT_10"] = p10["state"] + p10["county"] + p10["tract"]
p10["pop_base"] = pd.to_numeric(p10["B01003_001E"], errors="coerce").mask(lambda s: s < 0)  # rec 1 again

rel = pd.read_csv(RAW / "tract_rel_2020_2010_ksmo.csv", dtype=str)
for c in ("AREALAND_TRACT_10", "AREALAND_PART"):
    rel[c] = pd.to_numeric(rel[c])
rel = rel[rel["AREALAND_TRACT_10"] > 0]  # water-only 2010 tracts hold no people
rel["w"] = rel["AREALAND_PART"] / rel["AREALAND_TRACT_10"]

xw = rel.merge(p10[["GEOID_TRACT_10", "pop_base"]], on="GEOID_TRACT_10")
xw["pop_part"] = xw["pop_base"] * xw["w"]
base = xw.groupby("GEOID_TRACT_20")["pop_part"].sum().rename("pop_base_xw")
print(f"base population {p10['pop_base'].sum():,.0f} -> {base[base.index.isin(tracts['GEOID'])].sum():,.0f} "
      "after moving onto 2020 tracts (should match: county lines did not change)")

f = tracts.merge(base, left_on="GEOID", right_index=True, how="left")
# Floor the denominator at 100 people so tracts that were nearly empty do not produce +5,000% growth.
f["growth_pct"] = (f["total_pop"] - f["pop_base_xw"]) / np.maximum(f["pop_base_xw"], 100) * 100

# ---------------------------------------------------------------- daytime workers
wac = pd.concat(pd.read_csv(RAW / f"{s}_wac_S000_JT00_{LODES_YEAR}.csv.gz", usecols=["w_geocode", "C000"],
                            dtype={"w_geocode": str}) for s in STATES.values())
jobs = wac.groupby(wac["w_geocode"].str[:11])["C000"].sum().rename("jobs")
f = f.merge(jobs, left_on="GEOID", right_index=True, how="left")
f["jobs"] = f["jobs"].fillna(0).astype(int)        # a tract absent from LODES has no covered jobs
f["jobs_per_sqmi"] = f["jobs"] / (f["ALAND"] / 2_589_988)

print(f"jobs in the six counties: {f['jobs'].sum():,}; tracts with no base population: {f['pop_base_xw'].isna().sum()}")
print(f[["growth_pct", "jobs", "jobs_per_sqmi"]].describe().round(1).to_string())
f[["GEOID", "pop_base_xw", "growth_pct", "jobs", "jobs_per_sqmi"]].to_csv(INTERIM / "tract_features.csv", index=False)
