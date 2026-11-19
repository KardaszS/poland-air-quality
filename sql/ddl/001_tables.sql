CREATE TABLE IF NOT EXISTS station (
    station_code     TEXT PRIMARY KEY,
    old_code         TEXT,
    intl_code        TEXT,
    gios_station_id  INTEGER,
    name             TEXT NOT NULL,
    city             TEXT NOT NULL,
    station_type     TEXT,
    area_type        TEXT,
    lat              DOUBLE PRECISION,
    lon              DOUBLE PRECISION,
    active_from      DATE,
    active_to        DATE,
    selected         BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS sensor (
    sensor_id     INTEGER PRIMARY KEY,
    station_code  TEXT NOT NULL REFERENCES station(station_code),
    pollutant     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS measurement_hourly (
    station_code  TEXT NOT NULL REFERENCES station(station_code),
    pollutant     TEXT NOT NULL CHECK (pollutant IN ('PM10', 'PM2.5', 'NO2')),
    ts            TIMESTAMP NOT NULL,
    value         DOUBLE PRECISION NOT NULL CHECK (value >= 0),
    source        TEXT NOT NULL CHECK (source IN ('archive', 'api')),
    loaded_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (station_code, pollutant, ts)
);

CREATE TABLE IF NOT EXISTS weather_station (
    weather_station_code  TEXT PRIMARY KEY,
    name                  TEXT NOT NULL,
    lat                   DOUBLE PRECISION,
    lon                   DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS weather_daily (
    weather_station_code  TEXT NOT NULL REFERENCES weather_station(weather_station_code),
    day         DATE NOT NULL,
    t_mean      DOUBLE PRECISION,
    t_min       DOUBLE PRECISION,
    t_max       DOUBLE PRECISION,
    wind_mean   DOUBLE PRECISION,
    precip      DOUBLE PRECISION,
    snow_depth  DOUBLE PRECISION,
    humidity    DOUBLE PRECISION,
    source      TEXT NOT NULL DEFAULT 'imgw',
    PRIMARY KEY (weather_station_code, day)
);

CREATE TABLE IF NOT EXISTS station_weather_map (
    station_code          TEXT PRIMARY KEY REFERENCES station(station_code),
    weather_station_code  TEXT NOT NULL REFERENCES weather_station(weather_station_code),
    distance_km           DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS policy (
    policy_id       SERIAL PRIMARY KEY,
    city            TEXT NOT NULL,
    name            TEXT NOT NULL,
    effective_date  DATE,
    scope           TEXT,
    source_url      TEXT NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('treated', 'control', 'excluded', 'reserve'))
);

CREATE TABLE IF NOT EXISTS etl_run (
    run_id         SERIAL PRIMARY KEY,
    started_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at    TIMESTAMPTZ,
    job            TEXT NOT NULL,
    rows_loaded    INTEGER,
    rows_rejected  INTEGER,
    status         TEXT,
    error          TEXT
);