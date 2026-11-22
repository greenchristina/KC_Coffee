"""Load raw JSON into DuckDB WITHOUT cleaning, so the profiling queries can find the problems."""
import json, duckdb, pandas as pd

con = duckdb.connect("kc_coffee.duckdb")

acs = pd.DataFrame(json.load(open("data/raw/acs_tracts.json")))
acs = acs.rename(columns={"B19013_001E": "median_income", "B01003_001E": "total_pop", "B25077_001E": "median_home_value"})
acs["geoid"] = acs["state"] + acs["county"] + acs["tract"]
for c in ["median_income", "total_pop", "median_home_value"]:
    acs[c] = pd.to_numeric(acs[c], errors="coerce")  # keep Census sentinel codes (e.g. -666666666) as numbers
con.execute("CREATE OR REPLACE TABLE acs_tracts AS SELECT * FROM acs")

els = json.load(open("data/raw/osm_cafes.json"))["elements"]
rows = []
for e in els:
    t = e.get("tags", {})
    c = e.get("center", {})
    rows.append({"osm_id": e["id"], "osm_type": e["type"], "lat": e.get("lat", c.get("lat")), "lon": e.get("lon", c.get("lon")),
                 "name": t.get("name"), "brand": t.get("brand"), "opening_hours": t.get("opening_hours"),
                 "street": t.get("addr:street"), "website": t.get("website")})
cafes = pd.DataFrame(rows)
con.execute("CREATE OR REPLACE TABLE osm_cafes AS SELECT * FROM cafes")
print(con.sql("SELECT 'acs_tracts' t, count(*) n FROM acs_tracts UNION ALL SELECT 'osm_cafes', count(*) FROM osm_cafes"))
