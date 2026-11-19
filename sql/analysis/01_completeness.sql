-- How many hourly PM10 values does each station have in each year?
-- A full year has 8,760 hours (8,784 in leap years).

SELECT station_code,
       CAST(EXTRACT(YEAR FROM ts) AS INTEGER) AS year,
       COUNT(*) AS n_hours
FROM measurement_hourly
GROUP BY station_code, year
ORDER BY station_code, year;