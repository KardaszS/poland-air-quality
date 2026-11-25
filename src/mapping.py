from pathlib import Path

import numpy as np
import pandas as pd

EARTH_RADIUS_KM = 6371


def haversine(lat1, lon1, lat2, lon2):
    """Great-circle distance in km between points given in decimal degrees."""
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    a = (
        np.sin((lat2 - lat1) / 2) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def build_station_weather_map(
    stations_path: Path = Path("data/reference/stations.csv"),
    weather_stations_path: Path = Path("data/reference/weather_stations.csv"),
) -> pd.DataFrame:
    """Match each GIOŚ station to the IMGW station of the same city
    and compute the distance between them."""
    stations = pd.read_csv(stations_path, dtype=str)
    weather = pd.read_csv(weather_stations_path, dtype=str)

    weather["lat"] = weather["lat"].astype(float)
    weather["lon"] = weather["lon"].astype(float)

    stations["lat"] = stations["lat"].astype(float)
    stations["lon"] = stations["lon"].astype(float)

    matched = stations.merge(weather, how="left", on="city", suffixes=("", "_weather"))
    matched["distance_km"] = haversine(
        matched["lat"], matched["lon"], matched["lat_weather"], matched["lon_weather"]
    )

    matched["distance_km"] = matched["distance_km"].round(1)
    return matched[["station_code", "weather_station_code", "distance_km"]]


if __name__ == "__main__":
    print(build_station_weather_map())
