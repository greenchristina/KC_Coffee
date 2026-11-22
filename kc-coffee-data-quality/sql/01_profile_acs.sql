-- Profile ACS tract data. Census codes missing values as large negatives (e.g. -666666666), which silently wreck averages.

-- 1. Row counts and key integrity
SELECT count(*) AS rows, count(DISTINCT geoid) AS distinct_geoids, count(*) - count(DISTINCT geoid) AS duplicate_geoids
FROM acs_tracts;

-- 2. Null and sentinel rates per column
SELECT 'median_income' AS col, count(*) AS n,
       sum(CASE WHEN median_income IS NULL THEN 1 ELSE 0 END) AS nulls,
       sum(CASE WHEN median_income < 0 THEN 1 ELSE 0 END) AS sentinel_negatives
FROM acs_tracts
UNION ALL
SELECT 'total_pop', count(*), sum(CASE WHEN total_pop IS NULL THEN 1 ELSE 0 END), sum(CASE WHEN total_pop < 0 THEN 1 ELSE 0 END) FROM acs_tracts
UNION ALL
SELECT 'median_home_value', count(*), sum(CASE WHEN median_home_value IS NULL THEN 1 ELSE 0 END), sum(CASE WHEN median_home_value < 0 THEN 1 ELSE 0 END) FROM acs_tracts;

-- 3. Zero-population tracts (parks, industrial areas, airports): usually not valid for demand analysis
SELECT geoid, NAME, total_pop, median_income FROM acs_tracts WHERE total_pop = 0 ORDER BY geoid;

-- 4. Outliers in income using the 1.5 x IQR rule, valid values only
WITH valid AS (SELECT * FROM acs_tracts WHERE median_income > 0),
     q AS (SELECT quantile_cont(median_income, 0.25) AS q1, quantile_cont(median_income, 0.75) AS q3 FROM valid)
SELECT v.geoid, v.NAME, v.median_income
FROM valid v, q
WHERE v.median_income > q.q3 + 1.5 * (q.q3 - q.q1) OR v.median_income < q.q1 - 1.5 * (q.q3 - q.q1)
ORDER BY v.median_income DESC;

-- 5. Impact of ignoring sentinels: average income with vs. without them
SELECT avg(median_income) AS naive_avg, avg(CASE WHEN median_income > 0 THEN median_income END) AS clean_avg FROM acs_tracts;

-- 6. Coverage by county
SELECT state, county, count(*) AS tracts, sum(CASE WHEN median_income > 0 THEN 1 ELSE 0 END) AS tracts_with_income
FROM acs_tracts GROUP BY state, county ORDER BY state, county;
