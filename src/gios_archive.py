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
    long["value"] = pd.to_numeric( long["value"].astype(str).str.replace(",", ".", regex=False),
    errors="coerce",)
    long = long.dropna(subset=["value"])
    long["pollutant"] = pollutant

    return long[["station_code", "pollutant", "ts", "value"]]



def build_gios_staging(raw_dir: Path = Path("data/raw/gios"),stations_path: Path = Path("data/reference/stations.csv"),
                       output_path: Path = Path("data/staging/gios_hourly.parquet"),) -> pd.DataFrame:
    frames = []
    for year in range(2015, 2026):
        frames.append(load_gios_hourly(raw_dir / str(year) / f"{year}_PM10_1g.xlsx"))
    df = pd.concat(frames, ignore_index=True)

    stations = pd.read_csv(stations_path)
    pairs = stations[["station_code", "old_code"]].copy()
    pairs["old_code"] = pairs["old_code"].str.split(", ")
    pairs = pairs.explode("old_code")
    code_map = dict(zip(pairs["old_code"], pairs["station_code"]))
    df["station_code"] = df["station_code"].replace(code_map)
    df = df[df["station_code"].isin(stations["station_code"])]

    n_negative = (df["value"] < 0).sum()
    print(f"Dropped {n_negative} negative values")
    df = df[df["value"] >= 0]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)
    return df


if __name__ == "__main__":
    df = build_gios_staging()
    print(df.shape)