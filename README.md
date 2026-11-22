# Kansas City Coffeehouse Site Selection

A three-part analytics project that uses only public data. **Portfolio site:** `index.html` (served by GitHub Pages).

| Part | Folder | What it answers | Tools |
|---|---|---|---|
| 1. Data quality profile | [kc-coffee-data-quality](kc-coffee-data-quality) | Is the public data reliable enough to support a site decision? | Python, DuckDB, SQL |
| 2. Site-suitability model | [kc-coffee-site-suitability](kc-coffee-site-suitability) | Which of 551 census tracts are the strongest candidates? | Python, GeoPandas, OSMnx, R Shiny |
| 3. Decision memo | [in part 2's README](kc-coffee-site-suitability/README.md#decision-memo-where-to-open-the-next-5-coffeehouses-in-kc-and-why) | Where should the next five stores open, and what could go wrong? | Plain language, one page |

## Publishing the site
1. Push this folder as the root of a GitHub repository (default branch `main`).
2. Settings → Pages → Deploy from a branch → `main` / root.
3. Code links on the site point to this repository automatically once it is served from `github.io`.

Preview locally with `python -m http.server`, then open http://localhost:8000. The maps load their data with `fetch`, which browsers block when you open `index.html` directly as a file.
