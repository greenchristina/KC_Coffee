-- Profile OpenStreetMap cafe points.

-- 1. Counts by OSM element type and missing coordinates
SELECT osm_type, count(*) AS n, sum(CASE WHEN lat IS NULL OR lon IS NULL THEN 1 ELSE 0 END) AS missing_coords FROM osm_cafes GROUP BY osm_type;

-- 2. Completeness of key attributes (share of rows populated)
SELECT round(100.0 * count(name) / count(*), 1) AS pct_name,
       round(100.0 * count(brand) / count(*), 1) AS pct_brand,
       round(100.0 * count(opening_hours) / count(*), 1) AS pct_hours,
       round(100.0 * count(street) / count(*), 1) AS pct_street
FROM osm_cafes;

-- 3. Same place mapped twice: same name within roughly 50 m (0.0005 deg lat, 0.0006 deg lon)
SELECT a.osm_id AS id_a, b.osm_id AS id_b, a.name, a.lat, a.lon
FROM osm_cafes a JOIN osm_cafes b
  ON a.osm_id < b.osm_id AND lower(trim(a.name)) = lower(trim(b.name))
 AND abs(a.lat - b.lat) < 0.0005 AND abs(a.lon - b.lon) < 0.0006
WHERE a.name IS NOT NULL;

-- 4. Inconsistent naming: same name after lower-casing/trimming but different spellings
SELECT lower(trim(name)) AS normalized, count(DISTINCT name) AS spellings, count(*) AS rows
FROM osm_cafes WHERE name IS NOT NULL
GROUP BY 1 HAVING count(DISTINCT name) > 1 ORDER BY rows DESC;

-- 5. Names with leading/trailing whitespace
SELECT osm_id, name FROM osm_cafes WHERE name IS NOT NULL AND name <> trim(name);

-- 6. Chain vs. independent (brand populated) and top repeated names
SELECT CASE WHEN brand IS NOT NULL THEN 'branded' ELSE 'unbranded' END AS segment, count(*) AS n FROM osm_cafes GROUP BY 1;
SELECT name, count(*) AS locations FROM osm_cafes WHERE name IS NOT NULL GROUP BY name HAVING count(*) > 1 ORDER BY locations DESC LIMIT 15;

-- 7. Coordinates outside the download box (should be 0 rows)
SELECT osm_id, name, lat, lon FROM osm_cafes WHERE lat NOT BETWEEN 38.55 AND 39.50 OR lon NOT BETWEEN -95.10 AND -94.10;
