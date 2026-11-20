import zipfile
from pathlib import Path

import pandas as pd
import requests

BASE_URL = ("https://danepubliczne.imgw.pl/data/dane_pomiarowo_obserwacyjne/"
            "dane_meteorologiczne/dobowe/synop")


def download_synop(
    years: range = range(2015, 2026),
    stations_path: Path = Path("data/reference/weather_stations.csv"),
    raw_dir: Path = Path("data/raw/imgw"),
) -> None:
    """Download and unzip daily synoptic data for the selected IMGW stations."""
    codes = pd.read_csv(stations_path, dtype=str)["weather_station_code"]

    for year in years:
        year_dir = raw_dir / str(year)
        year_dir.mkdir(parents=True, exist_ok=True)

        for code in codes:
            name = f"{year}_{code}_s.zip"
            response = requests.get(f"{BASE_URL}/{year}/{name}", timeout=30)
            if response.status_code != 200:
                print(f"Missing: {name}")
                continue

            zip_path = year_dir / name
            zip_path.write_bytes(response.content)
            with zipfile.ZipFile(zip_path) as archive:
                archive.extractall(year_dir)


if __name__ == "__main__":
    download_synop()