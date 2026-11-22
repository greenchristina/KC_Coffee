"""Apply the fixes recommended in project 1's data quality report.

Report rec 1  Census sentinels (-666666666 etc.) -> NULL before any calculation
Report rec 2  Zero-population tracts excluded from scoring; populated tracts with suppressed income
              are kept, flagged, and given the median income of their neighbouring tracts
Report rec 3  Cafe names standardised through data/reference/cafe_name_map.csv; chain status from the map,
              not the OSM brand tag
Report rec 4  Whitespace trimmed; same-name points within 50 m (node + way) collapsed to one
Report rec 5  Income top-code flagged; scoring is rank-based (05_score.py) so it cannot distort the scale
"""
import json
import numpy as np, pandas as pd, geopandas as gpd
from scipy.spatial import cKDTree
from config import RAW, INTERIM, REF, DQ_RAW, STATES, ACS_YEAR, CRS_M, INCOME_TOPCODE, COUNTY_NAME

# ---------------------------------------------------------------- tracts
acs = pd.DataFrame(json.load(open(DQ_RAW / "acs_tracts.json")))
acs = acs.rename(columns={"B19013_001E": "median_income", "B01003_001E": "total_pop", "B25077_001E": "median_home_value"})
acs["GEOID"] = acs["state"] + acs["county"] + acs["tract"]
num = ["median_income", "total_pop", "median_home_value"]
acs[num] = acs[num].apply(pd.to_numeric, errors="coerce")

# Rec 1: every Census annotation code is a large negative number; none of these fields can be negative.
n_sentinel = int((acs["median_income"] < 0).sum())
acs[num] = acs[num].mask(acs[num] < 0)
print(f"[rec 1] sentinel income values -> NULL: {n_sentinel} (report: 21)")

shapes = pd.concat([gpd.read_file(RAW / f"cb_{ACS_YEAR}_{st}_tract_500k.zip") for st in STATES])
tracts = shapes[["GEOID", "NAMELSAD", "ALAND", "geometry"]].merge(acs[["GEOID"] + num], on="GEOID")
assert len(tracts) == len(acs), f"{len(acs) - len(tracts)} ACS tracts have no boundary"
tracts = tracts.to_crs(CRS_M)
tracts["county"] = tracts["GEOID"].str[:5].map(COUNTY_NAME)

# Rec 2: exclude empty tracts, keep and impute populated tracts with suppressed income.
tracts["scored"] = tracts["total_pop"] > 0
tracts["exclude_reason"] = np.where(tracts["scored"], "", "No residents (airport, park or industrial land)")
print(f"[rec 2] zero-population tracts excluded: {(~tracts['scored']).sum()} (report: 14)")

need = tracts[tracts["scored"] & tracts["median_income"].isna()]
# Cartographic boundaries are generalised, so neighbours may not touch exactly: a 50 m buffer finds them.
nb = gpd.sjoin(need[["GEOID", "geometry"]].assign(geometry=need.buffer(50)),
               tracts[["GEOID", "median_income", "geometry"]], predicate="intersects")
nb = nb[nb["GEOID_left"] != nb["GEOID_right"]]
fill = nb.groupby("GEOID_left")["median_income"].median()
tracts["income_imputed"] = tracts["GEOID"].isin(need["GEOID"])
tracts["median_income"] = tracts["median_income"].fillna(tracts["GEOID"].map(fill))
print(f"[rec 2] populated tracts with suppressed income, filled from neighbours: {len(need)} "
      f"({int(need['total_pop'].sum()):,} residents; report: 7 tracts, 6,608 residents)")

# Rec 5: flag, do not alter.
tracts["income_topcoded"] = tracts["median_income"] >= INCOME_TOPCODE
print(f"[rec 5] top-coded income tracts flagged: {tracts['income_topcoded'].sum()} (report: 2)")

tracts.to_file(INTERIM / "tracts_clean.gpkg", driver="GPKG")

# ---------------------------------------------------------------- cafes
rows = []
for e in json.load(open(DQ_RAW / "osm_cafes.json"))["elements"]:
    t, c = e.get("tags", {}), e.get("center", {})
    rows.append({"osm_id": e["id"], "osm_type": e["type"], "lat": e.get("lat", c.get("lat")),
                 "lon": e.get("lon", c.get("lon")), "name_raw": t.get("name")})
cafes = pd.DataFrame(rows)
cafes["name"] = cafes["name_raw"].str.strip()  # rec 4: "Filling Station " -> "Filling Station"

# Rec 3: standardise through the mapping table; names not in it are single-site independents.
name_map = pd.read_csv(REF / "cafe_name_map.csv")
cafes = cafes.merge(name_map[["name", "std_name", "segment", "coffee_competitor"]], on="name", how="left")
cafes["std_name"] = cafes["std_name"].fillna(cafes["name"])
cafes["segment"] = cafes["segment"].fillna(cafes["name"].isna().map({True: "unknown", False: "independent"}))
cafes["coffee_competitor"] = cafes["coffee_competitor"].fillna(1).astype(bool)  # unnamed cafes still compete

cafes = gpd.GeoDataFrame(cafes, geometry=gpd.points_from_xy(cafes["lon"], cafes["lat"]), crs=4326).to_crs(CRS_M)

# Rec 4: same standardised name within 50 m = one place mapped twice. Keep the node (point) record.
cafes = cafes.sort_values(["osm_type", "osm_id"]).reset_index(drop=True)  # 'node' sorts before 'way'
xy = np.column_stack([cafes.geometry.x, cafes.geometry.y])
dupes = sorted({j for i, j in cKDTree(xy).query_pairs(50)
                if pd.notna(cafes.at[i, "std_name"]) and cafes.at[i, "std_name"] == cafes.at[j, "std_name"]})
print(f"[rec 4] duplicate points removed: {len(dupes)} -> {cafes.loc[dupes, 'std_name'].tolist()} "
      "(report found 1 by exact name; standardised names can catch more)")
cafes = cafes.drop(index=dupes)

counts = cafes.groupby("std_name").size().to_dict()
scooters, dutch, sbux = (counts.get(n, 0) for n in ("Scooter's Coffee", "Dutch Bros Coffee", "Starbucks"))
print(f"[rec 3] Scooter's: {scooters} (report: 30), Dutch Bros: {dutch} (report: 14), Starbucks: {sbux}")
print(f"[rec 3] segments: {cafes['segment'].value_counts().to_dict()}; "
      f"coffee competitors kept for scoring: {cafes['coffee_competitor'].sum()} of {len(cafes)}")

cafes.drop(columns=["lat", "lon"]).to_file(INTERIM / "cafes_clean.gpkg", driver="GPKG")
print(f"wrote {len(tracts)} tracts, {len(cafes)} cafes to {INTERIM}")
