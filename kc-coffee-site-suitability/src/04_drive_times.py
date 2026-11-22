"""Drive-time trade areas on the OpenStreetMap road network.

For every tract, take an interior point as the candidate site and find how long it takes to drive TO it
from every road node (Dijkstra on the reversed graph, free-flow speeds). From that:
  reach_pop_10     residents of tracts whose interior point is within 10 minutes
  reach_jobs_10    jobs in those tracts
  cafes_10         coffee competitors within 10 minutes (chain_cafes_10 = how many are chains)
  nearest_cafe_min minutes to the closest coffee competitor (capped at SEARCH_MIN)
The first run downloads the road network (~10 minutes); later runs load data/interim/kc_drive.graphml.
"""
import numpy as np, pandas as pd, geopandas as gpd, osmnx as ox
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree
from config import INTERIM, CRS_M, CATCHMENT_MIN, SEARCH_MIN, GRAPH_BUFFER_M

tracts = gpd.read_file(INTERIM / "tracts_clean.gpkg")
cafes = gpd.read_file(INTERIM / "cafes_clean.gpkg")

graph_path = INTERIM / "kc_drive.graphml"
if graph_path.exists():
    G = ox.load_graphml(graph_path)
else:
    area = gpd.GeoSeries([tracts.union_all().buffer(GRAPH_BUFFER_M)], crs=CRS_M).to_crs(4326).iloc[0]
    ox.settings.cache_folder = str(INTERIM / "osmnx_cache")
    ox.settings.requests_timeout = 600
    print("downloading drive network (first run only)...")
    G = ox.graph_from_polygon(area, network_type="drive")
    G = ox.add_edge_travel_times(ox.add_edge_speeds(G))  # speed limits, imputed by road class where missing
    ox.save_graphml(G, graph_path)
print(f"network: {G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges")

# Sparse matrix of travel seconds; parallel edges keep the fastest.
nodes = np.array(G.nodes)
pos = {n: i for i, n in enumerate(nodes)}
e = pd.DataFrame([(pos[u], pos[v], d["travel_time"]) for u, v, d in G.edges(data=True)], columns=["u", "v", "t"])
e = e.groupby(["u", "v"], as_index=False)["t"].min()
A = csr_matrix((e["t"], (e["u"], e["v"])), shape=(len(nodes), len(nodes)))
A_to = A.T.tocsr()  # reversed: distances from the site come out as travel time from each node TO the site

# Snap tract interior points and cafes to the nearest road node.
node_xy = gpd.GeoSeries(gpd.points_from_xy([G.nodes[n]["x"] for n in nodes], [G.nodes[n]["y"] for n in nodes]),
                        crs=4326).to_crs(CRS_M)
tree = cKDTree(np.column_stack([node_xy.x, node_xy.y]))
site_pt = tracts.representative_point()  # always inside the polygon, unlike a centroid
site_snap_m, site_node = tree.query(np.column_stack([site_pt.x, site_pt.y]))
comp = cafes[cafes["coffee_competitor"]].reset_index(drop=True)
cafe_snap_m, cafe_node = tree.query(np.column_stack([comp.geometry.x, comp.geometry.y]))
on_net = cafe_snap_m <= 500  # cafes in the download box but beyond the network buffer are left out
comp, cafe_node = comp[on_net].reset_index(drop=True), cafe_node[on_net]
print(f"site snap distance: median {np.median(site_snap_m):.0f} m, max {site_snap_m.max():.0f} m; "
      f"competitors on network: {len(comp)} of {on_net.size}")

jobs = pd.read_csv(INTERIM / "tract_features.csv", dtype={"GEOID": str}).set_index("GEOID")["jobs"]
pop = tracts["total_pop"].to_numpy()
tract_jobs = tracts["GEOID"].map(jobs).fillna(0).to_numpy()
is_chain = (comp["segment"] == "chain").to_numpy()
limit, cut = SEARCH_MIN * 60, CATCHMENT_MIN * 60

out = []
for start in range(0, len(tracts), 50):  # 50 sources at a time keeps the distance matrix ~100 MB
    src = site_node[start:start + 50]
    T = dijkstra(A_to, indices=src, limit=limit)
    reach = T[:, site_node] <= cut
    t_cafe = T[:, cafe_node]
    near = t_cafe <= cut
    out.append(pd.DataFrame({
        "reach_pop_10": reach @ pop,
        "reach_jobs_10": reach @ tract_jobs,
        "cafes_10": near.sum(1),
        "chain_cafes_10": near[:, is_chain].sum(1),
        "nearest_cafe_min": np.minimum(t_cafe.min(1), limit) / 60,
    }))
    print(f"  {min(start + 50, len(tracts))}/{len(tracts)} tracts")

res = pd.concat(out, ignore_index=True)
res.insert(0, "GEOID", tracts["GEOID"].to_numpy())
res.to_csv(INTERIM / "catchments.csv", index=False)
print(res.describe().round(1).to_string())
