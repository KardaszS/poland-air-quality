import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"])

UPSERT_STATION = text("""
    INSERT INTO station (station_code, old_code, intl_code, name, city,
                         station_type, area_type, lat, lon, active_from, active_to)
    SELECT station_code, old_code, intl_code, name, city,
           station_type, area_type,
           lat::double precision, lon::double precision,
           active_from::date, active_to::date
    FROM stg_station
    ON CONFLICT (station_code) DO UPDATE SET
        old_code     = EXCLUDED.old_code,
        intl_code    = EXCLUDED.intl_code,
        name         = EXCLUDED.name,
        city         = EXCLUDED.city,
        station_type = EXCLUDED.station_type,
        area_type    = EXCLUDED.area_type,
        lat          = EXCLUDED.lat,
        lon          = EXCLUDED.lon,
        active_from  = EXCLUDED.active_from,
        active_to    = EXCLUDED.active_to
""")

INSERT_POLICY = text("""
    INSERT INTO policy (city, name, effective_date, scope, source_url, role)
    SELECT city, name, effective_date::date, scope, source_url, role
    FROM stg_policy
""")

UPSERT_MEASUREMENT = text("""
    INSERT INTO measurement_hourly (station_code, pollutant, ts, value, source)
    SELECT station_code, pollutant, ts, value, source
    FROM stg_measurement
    ON CONFLICT (station_code, pollutant, ts) DO UPDATE SET
        value     = EXCLUDED.value,
        source    = EXCLUDED.source,
        loaded_at = now()
    WHERE measurement_hourly.source <> 'archive' OR EXCLUDED.source = 'archive'
""")

UPSERT_WEATHER_STATION = text("""
    INSERT INTO weather_station (weather_station_code, name, lat, lon)
    SELECT weather_station_code, name,
           lat::double precision, lon::double precision
    FROM stg_weather_station
    ON CONFLICT (weather_station_code) DO UPDATE SET
        name = EXCLUDED.name,
        lat  = EXCLUDED.lat,
        lon  = EXCLUDED.lon
""")

UPSERT_WEATHER_DAILY = text("""
    INSERT INTO weather_daily (weather_station_code, day, t_mean, t_min, t_max,
                               wind_mean, precip, snow_depth, humidity)
    SELECT weather_station_code, day::date, t_mean, t_min, t_max,
           wind_mean, precip, snow_depth, humidity
    FROM stg_weather_daily
    ON CONFLICT (weather_station_code, day) DO UPDATE SET
        t_mean     = EXCLUDED.t_mean,
        t_min      = EXCLUDED.t_min,
        t_max      = EXCLUDED.t_max,
        wind_mean  = EXCLUDED.wind_mean,
        precip     = EXCLUDED.precip,
        snow_depth = EXCLUDED.snow_depth,
        humidity   = EXCLUDED.humidity
""")


def load_stations(path: Path = Path("data/reference/stations.csv")) -> int:
    """Insert or update stations from stations.csv."""
    df = pd.read_csv(path, dtype=str)
    with engine.begin() as conn:
        df.to_sql("stg_station", conn, if_exists="replace", index=False)
        result = conn.execute(UPSERT_STATION)
        conn.execute(text("DROP TABLE stg_station"))
    return result.rowcount


def load_policies(path: Path = Path("data/reference/policies.csv")) -> int:
    """Replace all policies with the content of policies.csv."""
    df = pd.read_csv(path, dtype=str)
    with engine.begin() as conn:
        df.to_sql("stg_policy", conn, if_exists="replace", index=False)
        conn.execute(text("TRUNCATE policy RESTART IDENTITY"))
        result = conn.execute(INSERT_POLICY)
        conn.execute(text("DROP TABLE stg_policy"))
    return result.rowcount


def upsert_measurements(df: pd.DataFrame, source: str) -> int:
    """Insert or update hourly measurements. Archive data are never
    overwritten by API data."""
    df = df.assign(source=source)[
        ["station_code", "pollutant", "ts", "value", "source"]
    ]
    with engine.begin() as conn:
        df.to_sql(
            "stg_measurement", conn, if_exists="replace", index=False, chunksize=50_000
        )
        result = conn.execute(UPSERT_MEASUREMENT)
        conn.execute(text("DROP TABLE stg_measurement"))
    return result.rowcount


def start_run(job: str) -> int:
    """Create an etl_run entry and return its id."""
    with engine.begin() as conn:
        return conn.execute(
            text("INSERT INTO etl_run (job) VALUES (:job) RETURNING run_id"),
            {"job": job},
        ).scalar_one()


def finish_run(
    run_id: int,
    status: str,
    rows_loaded: int | None = None,
    rows_rejected: int | None = None,
    error: str | None = None,
) -> None:
    """Mark an etl_run entry as finished."""
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE etl_run
                SET finished_at = now(), status = :status, rows_loaded = :rows_loaded,
                    rows_rejected = :rows_rejected, error = :error
                WHERE run_id = :run_id
            """),
            {
                "run_id": run_id,
                "status": status,
                "rows_loaded": rows_loaded,
                "rows_rejected": rows_rejected,
                "error": error,
            },
        )


def load_archive(path: Path = Path("data/staging/gios_hourly.parquet")) -> int:
    """Load the parsed GIOŚ archive into measurement_hourly and log the run."""
    run_id = start_run("archive_load")
    try:
        df = pd.read_parquet(path)
        n = upsert_measurements(df, source="archive")
    except Exception as e:
        finish_run(run_id, "failed", error=str(e))
        raise
    finish_run(run_id, "success", rows_loaded=n, rows_rejected=0)
    return n


def load_weather_stations(
    path: Path = Path("data/reference/weather_stations.csv"),
) -> int:
    """Insert or update IMGW weather stations from weather_stations.csv."""
    df = pd.read_csv(path, dtype=str)
    with engine.begin() as conn:
        df.to_sql("stg_weather_station", conn, if_exists="replace", index=False)
        result = conn.execute(UPSERT_WEATHER_STATION)
        conn.execute(text("DROP TABLE stg_weather_station"))
    return result.rowcount


def load_weather(path: Path = Path("data/staging/imgw_daily.parquet")) -> int:
    """Load daily IMGW weather data into weather_daily and log the run."""
    run_id = start_run("imgw_load")
    try:
        df = pd.read_parquet(path)
        with engine.begin() as conn:
            df.to_sql("stg_weather_daily", conn, if_exists="replace", index=False)
            n = conn.execute(UPSERT_WEATHER_DAILY).rowcount
            conn.execute(text("DROP TABLE stg_weather_daily"))
    except Exception as e:
        finish_run(run_id, "failed", error=str(e))
        raise
    finish_run(run_id, "success", rows_loaded=n, rows_rejected=0)
    return n


if __name__ == "__main__":
    print("stations:", load_stations())
    print("policies:", load_policies())
    print("measurements:", load_archive())
    print("weather stations:", load_weather_stations())
    print("weather:", load_weather())
