import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

BASE_URL = ("https://danepubliczne.imgw.pl/data/dane_pomiarowo_obserwacyjne/"
            "dane_meteorologiczne")

# Column names from IMGW format descriptions (s_d_format.txt, s_d_t_format.txt)
S_D_COLUMNS = [
    "NSP", "POST", "ROK", "MC", "DZ", "TMAX", "WTMAX", "TMIN", "WTMIN", "STD", "WSTD",
    "TMNG", "WTMNG", "SMDB", "WSMDB", "ROOP", "PKSN", "WPKSN", "RWSN", "WRWSN", "USL",
    "WUSL", "DESZ", "WDESZ", "SNEG", "WSNEG", "DISN", "WDISN", "GRAD", "WGRAD", "MGLA",
    "WMGLA", "ZMGL", "WZMGL", "SADZ", "WSADZ", "GOLO", "WGOLO", "ZMNI", "WZMNI", "ZMWS",
    "WZMWS", "ZMET", "WZMET", "FF10", "WFF10", "FF15", "WFF15", "BRZA", "WBRZA", "ROSA",
    "WROSA", "SZRO", "WSZRO", "DZPS", "WDZPS", "DZBL", "WDZBL", "SGR", "IZD", "WIZD",
    "IZG", "WIZG", "AKTN", "WAKTN",
]
S_D_T_COLUMNS = [
    "NSP", "POST", "ROK", "MC", "DZ", "NOS", "WNOS", "FWS", "WFWS", "TEMP", "WTEMP",
    "CPW", "WCPW", "WLGS", "WWLGS", "PPPS", "WPPPS", "PPPM", "WPPPM", "WODZ", "WWODZ",
    "WONO", "WWONO",
]

S_D_VALUES = {"TMAX": "WTMAX", "TMIN": "WTMIN", "STD": "WSTD", "SMDB": "WSMDB", "PKSN": "WPKSN"}
S_D_T_VALUES = {"FWS": "WFWS", "WLGS": "WWLGS"}
KEYS = ["NSP", "ROK", "MC", "DZ"]

RENAME = {
    "NSP": "weather_station_code",
    "STD": "t_mean",
    "TMIN": "t_min",
    "TMAX": "t_max",
    "FWS": "wind_mean",
    "SMDB": "precip",
    "PKSN": "snow_depth",
    "WLGS": "humidity",
}


def download_synop(
    years: range = range(2015, 2026),
    stations_path: Path = Path("data/reference/weather_stations.csv"),
    raw_dir: Path = Path("data/raw/imgw"),
    interval: str = "dobowe",
) -> None:
    """Download and unzip IMGW synoptic data for the selected stations.
    interval: "dobowe" (daily) or "terminowe" (hourly)."""
    codes = pd.read_csv(stations_path, dtype=str)["file_code"]

    for year in years:
        year_dir = raw_dir / str(year)
        year_dir.mkdir(parents=True, exist_ok=True)

        for code in codes:
            name = f"{year}_{code}_s.zip"
            url = f"{BASE_URL}/{interval}/synop/{year}/{name}"
            response = requests.get(url, timeout=30)
            if response.status_code != 200:
                print(f"Missing: {url}")
                continue

            zip_path = year_dir / name
            zip_path.write_bytes(response.content)
            with zipfile.ZipFile(zip_path) as archive:
                archive.extractall(year_dir)


def read_synop_daily(s_d_path, s_d_t_path) -> pd.DataFrame:
    """Read one station-year of IMGW daily synoptic data (main + additional file).
    If the additional file is missing, wind and humidity are left empty."""
    s_d = pd.read_csv(s_d_path, encoding="cp1250", header=None, names=S_D_COLUMNS)
    for val, status in S_D_VALUES.items():
        s_d.loc[s_d[status] == 8, val] = np.nan
    s_d = s_d[KEYS + list(S_D_VALUES)]

    if Path(s_d_t_path).exists():
        s_d_t = pd.read_csv(s_d_t_path, encoding="cp1250", header=None, names=S_D_T_COLUMNS)
        for val, status in S_D_T_VALUES.items():
            s_d_t.loc[s_d_t[status] == 8, val] = np.nan
        df = s_d.merge(s_d_t[KEYS + list(S_D_T_VALUES)], on=KEYS, how="left")
    else:
        df = s_d.copy()
        for val in S_D_T_VALUES:
            df[val] = np.nan

    df["day"] = pd.to_datetime({"year": df["ROK"], "month": df["MC"], "day": df["DZ"]})
    df = df.rename(columns=RENAME)
    df["weather_station_code"] = df["weather_station_code"].astype(str)
    return df[["weather_station_code", "day", "t_mean", "t_min", "t_max",
               "wind_mean", "precip", "snow_depth", "humidity"]]


def build_imgw_staging(
    raw_dir: Path = Path("data/raw/imgw"),
    stations_path: Path = Path("data/reference/weather_stations.csv"),
    output_path: Path = Path("data/staging/imgw_daily.parquet"),
) -> pd.DataFrame:
    """Parse daily synoptic data for all selected IMGW stations and years
    and save the result to Parquet."""
    stations = pd.read_csv(stations_path, dtype=str)
    file_codes = stations["file_code"]

    frames = []
    for year in range(2015, 2026):
        for code in file_codes:
            s_d_path = raw_dir / str(year) / f"s_d_{code}_{year}.csv"
            s_d_t_path = raw_dir / str(year) / f"s_d_t_{code}_{year}.csv"
            frames.append(read_synop_daily(s_d_path, s_d_t_path))

    weather = pd.concat(frames, ignore_index=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    weather.to_parquet(output_path, index=False)
    return weather


if __name__ == "__main__":
    weather = build_imgw_staging()
    print(weather.shape)