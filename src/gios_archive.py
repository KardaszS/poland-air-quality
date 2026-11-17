from pathlib import Path

import pandas as pd

def load_gios_hourly(path:Path, pollutant: str = "PM10") -> pd.DataFrame:

    raw = pd.read_excel(path, header=None)

    first = raw.iloc[:,0]
    row = first[first == "Kod stacji"].index[0]
    codes = raw.iloc[row,1:].tolist()

    dates = pd.to_datetime(raw[0],errors = 'coerce', format='mixed')
    data = raw[dates.notna()].copy()
    data.columns = ["ts"] + codes
    data["ts"] = pd.to_datetime(data["ts"]).dt.round("h")

    long = data.melt(id_vars="ts", var_name="station_code", value_name="value")
    long["value"] = pd.to_numeric(long["value"], errors="coerce")
    long = long.dropna(subset=["value"])
    long["pollutant"] = pollutant

    return long[["station_code", "pollutant", "ts", "value"]]

