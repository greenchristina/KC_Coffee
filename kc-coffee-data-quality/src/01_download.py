"""Download public data for the KC metro: ACS 5-year tract data (Census API) and cafes (OpenStreetMap Overpass)."""
import json, os, requests

YEAR = 2023  # ACS 5-year vintage
# (state FIPS, county FIPS, name): Johnson KS, Wyandotte KS, Jackson MO, Clay MO, Platte MO, Cass MO
COUNTIES = [("20", "091", "Johnson KS"), ("20", "209", "Wyandotte KS"), ("29", "095", "Jackson MO"),
            ("29", "047", "Clay MO"), ("29", "165", "Platte MO"), ("29", "037", "Cass MO")]
VARS = "NAME,B19013_001E,B01003_001E,B25077_001E"  # median HH income, total pop, median home value
KEY = os.environ.get("CENSUS_API_KEY")  # required now, free at api.census.gov/data/key_signup.html

def download_acs():
    if not KEY:
        raise SystemExit("CENSUS_API_KEY is not set. Get a free key at https://api.census.gov/data/key_signup.html, "
                         "then in PowerShell run: $env:CENSUS_API_KEY = 'your_key'")
    os.makedirs("data/raw", exist_ok=True)
    rows = []
    for st, co, label in COUNTIES:
        url = f"https://api.census.gov/data/{YEAR}/acs/acs5?get={VARS}&for=tract:*&in=state:{st}&in=county:{co}"
        if KEY: url += f"&key={KEY}"
        r = requests.get(url, timeout=60); r.raise_for_status()
        if "json" not in r.headers.get("content-type", ""):
            raise SystemExit(f"Census API did not return JSON (invalid/missing key?): {r.text[:200]}")
        data = r.json(); header, body = data[0], data[1:]
        rows += [dict(zip(header, b)) for b in body]
        print(label, len(body), "tracts")
    json.dump(rows, open("data/raw/acs_tracts.json", "w"))

def download_cafes():
    # Bounding box (south, west, north, east) roughly covering the six counties
    bbox = "38.55,-95.10,39.50,-94.10"
    q = f'[out:json][timeout:180];(node["amenity"="cafe"]({bbox});way["amenity"="cafe"]({bbox}););out center tags;'
    r = requests.post("https://overpass-api.de/api/interpreter", data={"data": q},
                      headers={"User-Agent": "kc-coffee-data-quality/1.0", "Accept": "application/json"}, timeout=240); r.raise_for_status()
    json.dump(r.json(), open("data/raw/osm_cafes.json", "w"))
    print(len(r.json()["elements"]), "cafe elements")

if __name__ == "__main__":
    download_acs()
    download_cafes()