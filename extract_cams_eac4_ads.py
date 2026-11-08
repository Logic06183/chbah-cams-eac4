"""
Extract CAMS global reanalysis (EAC4) surface air quality for CHBAH, 2016-2024.

EAC4 is not in Google Earth Engine (GEE only holds the CAMS near-real-time forecast,
where NO2/CO/SO2 are total columns). It is pulled from the Copernicus Atmosphere
Data Store (ADS) with cdsapi.

Variables
  PM2.5            single level, kg m-3                     -> ug m-3
  NO2, CO, SO2     lowest model level (60), mass mixing ratio kg kg-1
                   -> ug m-3 using air density rho = p / (Rd * T) at the surface
EAC4 grid is 0.75 deg, 3-hourly (00, 03 ... 21 UTC). The site value is the grid cell
nearest the point. Days are local SAST (UTC+2); a SAST day is built from the 8
three-hourly fields whose timestamps fall inside it.

Usage:  ADS key in ~/.cdsapirc (url: https://ads.atmosphere.copernicus.eu/api)
        python extract_cams_eac4_ads.py --out out_dir
"""
import argparse
from pathlib import Path

import cdsapi
import numpy as np
import pandas as pd
import xarray as xr

LAT, LON = -26.260937696983632, 27.943209582266476
AREA = [-25.0, 27.0, -27.5, 29.25]   # N, W, S, E box around the site
RD = 287.05                           # J kg-1 K-1, dry air
TZ_OFFSET_H = 2


def request(c, year, target, multi):
    common = {"date": [f"{year}-01-01/{year}-12-31"],
              "time": [f"{h:02d}:00" for h in range(0, 24, 3)],
              "area": AREA, "data_format": "netcdf_zip"}
    if multi:
        common |= {"variable": ["nitrogen_dioxide", "carbon_monoxide", "sulphur_dioxide"],
                   "model_level": ["60"]}
    else:
        common |= {"variable": ["particulate_matter_2.5um", "surface_pressure", "2m_temperature"]}
    c.retrieve("cams-global-reanalysis-eac4", common, str(target))


def open_zip(path):
    """netcdf_zip downloads hold one or more .nc files; open and merge them."""
    import zipfile, tempfile
    tmp = Path(tempfile.mkdtemp())
    with zipfile.ZipFile(path) as z:
        z.extractall(tmp)
    return xr.merge([xr.open_dataset(f).load() for f in sorted(tmp.glob("*.nc"))], compat="override")


def nearest(ds):
    lat = "latitude" if "latitude" in ds.dims else "lat"
    lon = "longitude" if "longitude" in ds.dims else "lon"
    return ds.sel({lat: LAT, lon: LON}, method="nearest")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out")
    ap.add_argument("--years", default="2016-2024")
    a = ap.parse_args()
    out = Path(a.out); raw = out / "raw_eac4"; raw.mkdir(parents=True, exist_ok=True)
    y0, y1 = map(int, a.years.split("-"))
    c = cdsapi.Client()

    frames, cells = [], set()
    # SAST day d = UTC fields 00..21 on the same date, so no edge-year pull is needed.
    # Requests go one at a time (ADS asks users not to run them in parallel).
    for y in range(y0, y1 + 1):
        f_s, f_m = raw / f"eac4_sfc_{y}.zip", raw / f"eac4_ml60_{y}.zip"
        # a 0-byte file means an interrupted download, so treat it as missing
        if not f_s.exists() or f_s.stat().st_size == 0: request(c, y, f_s, multi=False)
        if not f_m.exists() or f_m.stat().st_size == 0: request(c, y, f_m, multi=True)
        s, m = nearest(open_zip(f_s)), nearest(open_zip(f_m))
        m = m.squeeze(drop=True) if "model_level" in m.dims else m
        cells.add((float(s[[k for k in s.coords if k.startswith("lat")][0]]),
                   float(s[[k for k in s.coords if k.startswith("lon")][0]])))
        df = xr.merge([s, m], compat="override").to_dataframe().reset_index()
        frames.append(df)

    h = pd.concat(frames, ignore_index=True)
    tcol = "valid_time" if "valid_time" in h else "time"
    h["time_utc"] = pd.to_datetime(h[tcol])
    h = h.drop_duplicates("time_utc").sort_values("time_utc")
    rho = h["sp"] / (RD * h["t2m"])                      # kg m-3
    h["pm25_ugm3"] = h["pm2p5"] * 1e9
    h["no2_ugm3"] = h["no2"] * rho * 1e9
    h["co_ugm3"] = h["co"] * rho * 1e9
    h["so2_ugm3"] = h["so2"] * rho * 1e9
    h["date"] = (h["time_utc"] + pd.Timedelta(hours=TZ_OFFSET_H)).dt.floor("D")
    cols = ["pm25_ugm3", "no2_ugm3", "co_ugm3", "so2_ugm3"]
    g = h.groupby("date")
    d = g[cols].mean().add_suffix("_mean").join(g[cols].max().add_suffix("_max"))
    d.insert(0, "n_fields", g.size())
    d = d.loc[f"{y0}-01-01":f"{y1}-12-31"].round(3)
    d.to_csv(out / "cams_eac4_daily_chbah.csv")
    print("grid cell(s) used:", cells, "| days:", len(d))


if __name__ == "__main__":
    main()
