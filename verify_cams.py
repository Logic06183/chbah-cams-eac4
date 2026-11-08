"""Independent check of out/cams_eac4_daily_chbah.csv against the raw EAC4 zips.
Separate code from extract_cams_eac4_ads.py on purpose (criteria 1, 5, 7 in GOAL.md).
Usage: python verify_cams.py [out_dir]"""
import sys, zipfile, tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr

out = Path(sys.argv[1] if len(sys.argv) > 1 else "out")
raw = out / "raw_eac4"
SITE = (-26.260937696983632, 27.943209582266476)
YEARS = range(2016, 2025)
L = []

# Criterion 1: all 18 files present and readable
def load(zp):
    d = Path(tempfile.mkdtemp())
    with zipfile.ZipFile(zp) as z:
        z.extractall(d)
    return [xr.open_dataset(f).load() for f in sorted(d.glob("*.nc"))]

data, bad = {}, []
for y in YEARS:
    for kind in ("sfc", "ml60"):
        p = raw / f"eac4_{kind}_{y}.zip"
        try:
            data[(kind, y)] = load(p)
        except Exception as e:
            bad.append(f"{p.name}: {type(e).__name__} {e}")
L.append(f"[C1] raw files readable: {len(data)}/18" + ("" if not bad else "\n  " + "\n  ".join(bad)))

# Pull one variable at the cell nearest the site, by explicit great-circle-free index search
def series(dsets, var):
    ds = next(d for d in dsets if var in d.data_vars)
    da = ds[var]
    latn = next(n for n in da.dims if n.startswith("lat"))
    lonn = next(n for n in da.dims if n.startswith("lon"))
    i = int(np.abs(ds[latn].values - SITE[0]).argmin())
    j = int(np.abs(ds[lonn].values - SITE[1]).argmin())
    da = da.isel({latn: i, lonn: j})
    da = da.squeeze(drop=True)
    tn = next(n for n in da.dims)
    cell = (float(ds[latn].values[i]), float(ds[lonn].values[j]))
    return pd.Series(da.values.astype("float64"), index=pd.to_datetime(da[tn].values)), cell

rows, cells = [], set()
for y in YEARS:
    if ("sfc", y) not in data or ("ml60", y) not in data:
        continue
    s, m = data[("sfc", y)], data[("ml60", y)]
    pm, c1 = series(s, "pm2p5"); sp, _ = series(s, "sp"); t2, _ = series(s, "t2m")
    no2, c2 = series(m, "no2"); co, _ = series(m, "co"); so2, _ = series(m, "so2")
    cells |= {c1, c2}
    rho = sp / (287.05 * t2)
    rows.append(pd.DataFrame({"pm25_ugm3": pm * 1e9, "no2_ugm3": no2 * rho * 1e9,
                              "co_ugm3": co * rho * 1e9, "so2_ugm3": so2 * rho * 1e9}))
L.append(f"[C3] grid cell(s) found independently: {sorted(cells)}")

h = pd.concat(rows).sort_index()
h = h[~h.index.duplicated()]
local_day = (h.index + pd.Timedelta(hours=2)).normalize()
ref = pd.concat([h.groupby(local_day).mean().add_suffix("_mean"),
                 h.groupby(local_day).max().add_suffix("_max")], axis=1)

# Criterion 5: sample >= 30 days spread across every year
csv = pd.read_csv(out / "cams_eac4_daily_chbah.csv", index_col=0, parse_dates=True)
rng = np.random.default_rng(20261106)
sample = []
for y in YEARS:
    days = csv.index[csv.index.year == y]
    if len(days):
        sample += list(rng.choice(days, size=min(4, len(days)), replace=False))
sample = pd.DatetimeIndex(sample)
cols = [c for c in ref.columns]
diff = (csv.loc[sample, cols] - ref.loc[sample, cols]).abs()
L.append(f"[C5] sampled days: {len(sample)} across {len({d.year for d in sample})} years; "
         f"max |diff| = {diff.max().max():.4f} ug/m3 -> {'PASS' if diff.max().max() <= 0.01 else 'FAIL'}")
full = (csv[cols] - ref.reindex(csv.index)[cols]).abs().max().max()
L.append(f"     full-series max |diff| (all days) = {full:.4f}")

# Criterion 7: seasonality
for p in ("pm25", "no2", "co"):
    s = csv[f"{p}_ugm3_mean"]
    jja, djf = s[s.index.month.isin([6, 7, 8])].mean(), s[s.index.month.isin([12, 1, 2])].mean()
    L.append(f"[C7] {p}: Jun-Aug mean {jja:.1f}, Dec-Feb mean {djf:.1f} -> winter higher: {'yes' if jja > djf else 'NO'}")

# Criterion 6 helper
pm_mean = csv["pm25_ugm3_mean"].mean()
L.append(f"[C6] PM2.5 2016-2024 mean {pm_mean:.1f} ug/m3 vs ground ref 25-30 -> ratio {pm_mean/27.5:.2f}x of midpoint")

(out / "verify_report.txt").write_text("\n".join(L) + "\n")
print("\n".join(L))
