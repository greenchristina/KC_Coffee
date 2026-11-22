"""Combine the five factors into a 0-100 suitability score and export for the Shiny map.

Each factor is turned into a percentile rank across the scored tracts (0 = worst, 1 = best). Ranks, not
raw values, so the income top-code, extreme job densities and the floored growth rates cannot dominate
(report rec 5). Score = weighted mean of the five percentiles x 100.
"""
import numpy as np, pandas as pd, geopandas as gpd
from config import INTERIM, PROCESSED, WEIGHTS

# factor key -> (column, higher is better)
FACTORS = {
    "income":      ("median_income", True),    # median household income
    "growth":      ("growth_pct", True),       # population change, 2014-18 to 2019-23
    "workers":     ("jobs_per_sqmi", True),    # daytime workers: jobs per square mile in the tract
    "access":      ("reach_pop_10", True),     # residents within a 10-minute drive
    "competition": ("cafes_per_10k", False),   # coffee competitors per 10k residents in that 10 minutes
}

tr = gpd.read_file(INTERIM / "tracts_clean.gpkg")
for f in ("tract_features.csv", "catchments.csv"):
    tr = tr.merge(pd.read_csv(INTERIM / f, dtype={"GEOID": str}), on="GEOID", how="left")
tr["cafes_per_10k"] = tr["cafes_10"] / tr["reach_pop_10"] * 10_000

s = tr["scored"]
for key, (col, higher_better) in FACTORS.items():
    tr[f"pct_{key}"] = tr.loc[s, col].rank(pct=True, ascending=higher_better)
    gap = s & tr[col].isna()
    if gap.any():
        print(f"  {key}: {gap.sum()} scored tracts missing {col}; given the neutral 0.5")
        tr.loc[gap, f"pct_{key}"] = 0.5

w = pd.Series(WEIGHTS)
tr["score"] = sum(tr[f"pct_{k}"] * w[k] for k in FACTORS) / w.sum() * 100
tr["rank"] = tr["score"].rank(ascending=False, method="min").astype("Int64")

cols = ["GEOID", "NAMELSAD", "county", "scored", "exclude_reason", "total_pop", "median_income",
        "income_imputed", "income_topcoded", "growth_pct", "jobs", "jobs_per_sqmi", "reach_pop_10",
        "reach_jobs_10", "cafes_10", "chain_cafes_10", "cafes_per_10k", "nearest_cafe_min"] \
       + [f"pct_{k}" for k in FACTORS] + ["score", "rank"]
out = tr[cols + ["geometry"]].sort_values("rank", na_position="last")
num = out.select_dtypes("float").columns
out[num] = out[num].round(4)

out.to_crs(4326).to_file(PROCESSED / "tracts_scored.geojson", driver="GeoJSON")
out.drop(columns="geometry").to_csv(PROCESSED / "tracts_scored.csv", index=False)

cafes = gpd.read_file(INTERIM / "cafes_clean.gpkg")
cafes[["osm_id", "std_name", "segment", "coffee_competitor", "geometry"]].to_crs(4326) \
    .to_file(PROCESSED / "cafes.geojson", driver="GeoJSON")

print(f"scored {s.sum()} tracts, excluded {(~s).sum()}; weights {WEIGHTS}")
show = out[out["scored"]].head(15)[["rank", "GEOID", "county", "score", "median_income", "growth_pct", "jobs_per_sqmi",
                        "reach_pop_10", "cafes_10"]]
print(show.to_string(index=False, float_format=lambda v: f"{v:,.1f}"))
