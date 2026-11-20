import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

BASE_URL = ("https://danepubliczne.imgw.pl/data/dane_pomiarowo_obserwacyjne/"
            "dane_meteorologiczne")

# Column names from IMGW format descriptions
# (s_d_format.txt, s_d_t_format.txt, s_t_format.txt)
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
S_T_COLUMNS = [
    "NSP", "POST", "ROK", "MC", "DZ", "GG", "HPOD", "WHPOD", "HPON", "WHPON", "HPOW",
    "WHPOW", "HTXT", "POM1", "POM2", "WID", "WWID", "WIDO", "WWIDO", "WIDA", "WWIDA",
    "NOG", "WNOG", "KRWR", "WKRWR", "FWR", "WFWR", "PORW", "WPORW", "TEMP", "WTEMP",
    "TTZW", "WTTZW", "WENT", "TWLW", "CPW", "WCPW", "WLGW", "WWLGW", "TPTR", "WTPTR",
    "PPPS", "WPPPS", "PPPM", "WPPPM", "TECH", "APP", "WAPP", "WO6G", "WWO6G", "ROPT",
    "WROPT", "POGB", "POGU", "CLCM", "WCLCM", "CHCL", "WCHCL", "CHLT", "CHCM", "WCHCM",
    "CHMT", "CHCH", "WCHCH", "CHHT", "SGRN", "WSGRN", "DEFI", "WDEFI", "USLN", "WUSLN",
    "ROSW", "WROSW", "PORK", "WPORK", "GODP", "MINP", "TG05", "WTG05", "TG10", "WTG10",
    "TG20", "WTG20", "TG50", "WTG50", "TG100", "WTG100", "TMIN", "WTMIN", "TMAX", "WTMAX",
    "TGMI", "WTGMI", "RWSN", "WRWSN", "PKSN", "WPKSN", "HSS", "WHSS", "GRSN", "WGRSN",
    "GATS", "UKPO", "HPRO", "WHPRO", "CIPR", "WCIPR",
]

S_D_VALUES = {"TMAX": "WTMAX", "TMIN": "WTMIN", "STD": "WSTD", "SMDB": "WSMDB", "PKSN": "WPKSN"}
S_D_T_VALUES = {"FWS": "WFWS", "WLGS": "WWLGS"}
S_T_VALUES = {"FWR": "WFWR", "WLGW": "WWLGW"}
KEYS = ["NSP", "ROK", "MC", "DZ"]
MIN_HOURS = 18  # minimum valid hours for a daily mean

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


def read_synop_hourly(s_t_path: Path) -> pd.DataFrame:
    """Read one station-year of IMGW hourly synoptic data and return daily means
    of wind speed and humidity (only days with at least MIN_HOURS valid hours)."""
    usecols = KEYS + list(S_T_VALUES) + list(S_T_VALUES.values())
    s_t = pd.read_csv(s_t_path, encoding="cp1250", header=None,
                      names=S_T_COLUMNS, usecols=usecols)
    for val, status in S_T_VALUES.items():
        s_t.loc[s_t[status] == 8, val] = np.nan

    daily = s_t.groupby(KEYS).agg(
        wind_mean=("FWR", "mean"),
        wind_n=("FWR", "count"),
        humidity=("WLGW", "mean"),
        humidity_n=("WLGW", "count"),
    ).reset_index()

    daily.loc[daily["wind_n"] < MIN_HOURS, "wind_mean"] = np.nan
    daily.loc[daily["humidity_n"] < MIN_HOURS, "humidity"] = np.nan

    daily["day"] = pd.to_datetime({"year": daily["ROK"], "month": daily["MC"], "day": daily["DZ"]})
    daily = daily.rename(columns={"NSP": "weather_station_code"})
    daily["weather_station_code"] = daily["weather_station_code"].astype(str)
    return daily[["weather_station_code", "day", "wind_mean", "humidity"]]


def build_imgw_hourly_daily(
    raw_dir: Path = Path("data/raw/imgw_hourly"),
    stations_path: Path = Path("data/reference/weather_stations.csv"),
    years: range = range(2024, 2026),
) -> pd.DataFrame:
    """Daily wind and humidity means from hourly synoptic data
    for all selected stations and years."""
    stations = pd.read_csv(stations_path, dtype=str)
    file_codes = stations["file_code"]

    frames = []
    for year in years:
        for code in file_codes:
            s_t_path = raw_dir / str(year) / f"s_t_{code}_{year}.csv"
            frames.append(read_synop_hourly(s_t_path))

    return pd.concat(frames, ignore_index=True)


def build_imgw_staging(
    raw_dir: Path = Path("data/raw/imgw"),
    stations_path: Path = Path("data/reference/weather_stations.csv"),
    output_path: Path = Path("data/staging/imgw_daily.parquet"),
) -> pd.DataFrame:
    """Parse daily synoptic data for all selected IMGW stations and years,
    fill missing wind and humidity from hourly data and save the result to Parquet."""
    stations = pd.read_csv(stations_path, dtype=str)
    file_codes = stations["file_code"]

    frames = []
    for year in range(2015, 2026):
        for code in file_codes:
            s_d_path = raw_dir / str(year) / f"s_d_{code}_{year}.csv"
            s_d_t_path = raw_dir / str(year) / f"s_d_t_{code}_{year}.csv"
            frames.append(read_synop_daily(s_d_path, s_d_t_path))
    weather = pd.concat(frames, ignore_index=True)

    # IMGW stopped publishing daily wind/humidity after June 2024:
    # fill the gaps with daily means computed from hourly data
    hourly = build_imgw_hourly_daily(stations_path=stations_path)
    weather = weather.merge(hourly, on=["weather_station_code", "day"],
                            how="left", suffixes=("", "_hourly"))
    weather["wind_mean"] = weather["wind_mean"].fillna(weather["wind_mean_hourly"])
    weather["humidity"] = weather["humidity"].fillna(weather["humidity_hourly"])
    weather = weather.drop(columns=["wind_mean_hourly", "humidity_hourly"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    weather.to_parquet(output_path, index=False)
    return weather


if __name__ == "__main__":
    weather = build_imgw_staging()
    print(weather.shape)