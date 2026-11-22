"""Write slim map data for the portfolio site (../assets): simplified tract shapes, cafes, the five picks."""
import json
import geopandas as gpd, pandas as pd
from config import ROOT, PROCESSED, CRS_M

SITE_ASSETS = ROOT.parent / "assets"
SITE_ASSETS.mkdir(exist_ok=True)

tr = gpd.read_file(PROCESSED / "tracts_scored.geojson").to_crs(CRS_M)
tr["geometry"] = tr.simplify(25)  # 25 m tolerance: invisible at metro zoom, cuts the file to a fraction
tr = tr.rename(columns={"NAMELSAD": "tract"})
tr["tract"] = tr["tract"].str.replace("Census Tract ", "", regex=False)
keep = ["GEOID", "tract", "county", "scored", "score", "rank", "median_income", "growth_pct", "jobs",
        "reach_pop_10", "cafes_10"]
tr = tr[keep + ["geometry"]].to_crs(4326)
tr["score"] = tr["score"].round(1)
tr["growth_pct"] = tr["growth_pct"].round(1)
tr.to_file(SITE_ASSETS / "tracts.geojson", driver="GeoJSON", COORDINATE_PRECISION=5)

cafes = gpd.read_file(PROCESSED / "cafes.geojson")
cafes = cafes[cafes["coffee_competitor"].astype(bool)][["std_name", "segment", "geometry"]]
cafes.to_file(SITE_ASSETS / "cafes.geojson", driver="GeoJSON", COORDINATE_PRECISION=5)

rec = pd.read_csv(PROCESSED / "recommendations.csv")
picks = rec[["pick", "place", "near", "lat", "lon", "score", "rank"]].round({"score": 1}).to_dict("records")
(SITE_ASSETS / "picks.json").write_text(json.dumps(picks, indent=1))

for f in ("tracts.geojson", "cafes.geojson", "picks.json"):
    print(f"{f}: {(SITE_ASSETS / f).stat().st_size / 1024:,.0f} KB")
