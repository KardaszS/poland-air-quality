CREATE OR REPLACE VIEW pm_daily AS
SELECT
    station_code,
    (ts - INTERVAL '1 hour')::date AS day,
    ROUND(AVG(value)::numeric, 2) AS pm10_mean,
    COUNT(*) AS n_hours,
    AVG(value) > 50 AS exceeds_limit
FROM measurement_hourly
WHERE pollutant = 'PM10'
GROUP BY station_code, day
HAVING COUNT(*) >= 18;


CREATE OR REPLACE VIEW city_daily AS
WITH city_pm AS (
    SELECT
        s.city,
        m.weather_station_code,
        pd.day,
        ROUND(AVG(pd.pm10_mean), 2) AS pm10_mean,
        COUNT(*) AS n_stations
    FROM pm_daily pd
    JOIN station s USING (station_code)
    JOIN station_weather_map m USING (station_code)
    GROUP BY s.city, m.weather_station_code, pd.day
)
SELECT
    c.city,
    day,
    c.pm10_mean,
    c.n_stations,
    w.t_mean,
    w.t_min,
    w.t_max,
    w.wind_mean,
    w.precip,
    w.snow_depth,
    w.humidity
FROM city_pm c
LEFT JOIN weather_daily w USING (weather_station_code, day)

