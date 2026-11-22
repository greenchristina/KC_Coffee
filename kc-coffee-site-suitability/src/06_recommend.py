"""Turn the ranking into five recommended sites for the decision memo.

1. Spacing: walk down the ranking and accept a tract only if its site point is at least MIN_GAP_MI
   from every site already chosen, so the five stores do not split the same customers.
2. Robustness: re-score every tract under 1,000 random weightings (Dirichlet, alpha = 2) and record how
   often each tract lands in the top 25. A pick that only wins under the default weights is fragile.
3. Labels: attach the Census place (city) each site falls in, for a non-technical reader.
"""
import numpy as np, pandas as pd, geopandas as gpd, requests
from config import RAW, INTERIM, PROCESSED, STATES, ACS_YEAR, CRS_M, WEIGHTS

N_PICKS, MIN_GAP_MI, TOP_K, N_SIMS = 5, 5, 25, 1000
FACTORS = list(WEIGHTS)

tr = gpd.read_file(PROCESSED / "tracts_scored.geojson").to_crs(CRS_M)
tr = tr[tr["scored"].astype(bool)].copy()
tr["site"] = tr.representative_point()

# ---------------------------------------------------------------- robustness across weightings
rng = np.random.default_rng(42)
W = rng.dirichlet(np.full(len(FACTORS), 2.0), N_SIMS)               # each row sums to 1
P = tr[[f"pct_{k}" for k in FACTORS]].to_numpy()
ranks = (-(P @ W.T)).argsort(0).argsort(0) + 1                        # rank of each tract in each run
tr["top25_share"] = (ranks <= TOP_K).mean(1)
tr["median_rank_alt"] = np.median(ranks, 1)

# ---------------------------------------------------------------- place names
for st in STATES:
    dest = RAW / f"cb_{ACS_YEAR}_{st}_place_500k.zip"
    if not dest.exists():
        url = f"https://www2.census.gov/geo/tiger/GENZ{ACS_YEAR}/shp/cb_{ACS_YEAR}_{st}_place_500k.zip"
        dest.write_bytes(requests.get(url, timeout=300).content)
places = pd.concat([gpd.read_file(RAW / f"cb_{ACS_YEAR}_{st}_place_500k.zip") for st in STATES]).to_crs(CRS_M)
pts = gpd.GeoDataFrame(tr[["GEOID"]], geometry=tr["site"], crs=CRS_M)
hit = gpd.sjoin(pts, places[["NAME", "geometry"]], predicate="within").drop_duplicates("GEOID")
tr["place"] = tr["GEOID"].map(hit.set_index("GEOID")["NAME"])
tr["place"] = tr["place"].fillna("Unincorporated " + tr["county"])

# ---------------------------------------------------------------- spaced picks
gap_m = MIN_GAP_MI * 1609.34
picks = []
for i, row in tr.sort_values("rank").iterrows():
    if all(row["site"].distance(tr.at[j, "site"]) >= gap_m for j in picks):
        picks.append(i)
    if len(picks) == N_PICKS:
        break

cols = ["rank", "GEOID", "NAMELSAD", "place", "county", "score", "median_income", "growth_pct", "jobs",
        "jobs_per_sqmi", "reach_pop_10", "cafes_10", "chain_cafes_10", "cafes_per_10k", "nearest_cafe_min",
        "top25_share", "median_rank_alt"]
rec = tr.loc[picks, cols].copy()
rec.insert(0, "pick", range(1, N_PICKS + 1))
site_ll = gpd.GeoSeries(tr.loc[picks, "site"], crs=CRS_M).to_crs(4326)
rec["lat"], rec["lon"] = site_ll.y.round(5).to_numpy(), site_ll.x.round(5).to_numpy()

# "Near X and Y": the two closest differently-named major roads in the OSM network from 04_drive_times.py.
import osmnx as ox
edges = ox.graph_to_gdfs(ox.load_graphml(INTERIM / "kc_drive.graphml"), nodes=False)[["name", "highway", "geometry"]]
major = edges[edges["highway"].astype(str).str.contains("primary|secondary|trunk") & edges["name"].notna()].to_crs(CRS_M)
major = major.assign(name=major["name"].map(lambda n: n[0] if isinstance(n, list) else n))
def near_roads(pt):
    d = major.distance(pt).groupby(major["name"]).min().nsmallest(2)
    return " & ".join(d.index)
rec["near"] = [near_roads(tr.at[i, "site"]) for i in picks]
rec.to_csv(PROCESSED / "recommendations.csv", index=False)

# Context for the memo: the best urban-core alternative, and how concentrated the top of the list is.
top50 = tr.sort_values("rank").head(50)
print(f"top 50 by county: {top50['county'].value_counts().to_dict()}")
core = tr[tr["county"].isin(["Jackson MO", "Wyandotte KS"])].sort_values("rank").head(3)
print("best Jackson/Wyandotte tracts:")
print(core[cols].to_string(index=False))
stable = tr.sort_values("top25_share", ascending=False).head(10)
print("most robust tracts (share of 1,000 weightings in top 25):")
print(stable[["rank", "GEOID", "place", "county", "score", "top25_share"]].to_string(index=False))
print("\nPICKS")
print(rec.drop(columns=["GEOID"]).to_string(index=False, float_format=lambda v: f"{v:,.2f}"))
