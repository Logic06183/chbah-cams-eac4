"""QC for the CAMS EAC4 daily file. Usage: python qc_cams.py out/cams_eac4_daily_chbah.csv"""
import sys
import pandas as pd

p = sys.argv[1] if len(sys.argv) > 1 else "out/cams_eac4_daily_chbah.csv"
d = pd.read_csv(p, index_col=0, parse_dates=True)
L = []
exp = pd.date_range("2016-01-01", "2024-12-31")
L.append(f"Rows: {len(d)} (expected {len(exp)}); missing dates: {len(exp.difference(d.index))}; duplicates: {d.index.duplicated().sum()}")
L.append(f"Days with n_fields != 8: {(d.n_fields != 8).sum()}")
L.append(f"Missing values:\n{d.isna().sum().to_string()}")
vals = d.drop(columns="n_fields")
L.append(f"Non-positive values: {(vals <= 0).sum().sum()}")
L.append("\nDistribution (ug/m3):\n" + vals.describe(percentiles=[.05, .5, .95]).T[["mean", "5%", "50%", "95%", "max"]].round(1).to_string())
L.append("\nMonthly means:\n" + vals.filter(like="_mean").groupby(d.index.month).mean().round(1).to_string())
L.append("\nAnnual means:\n" + vals.filter(like="_mean").groupby(d.index.year).mean().round(1).to_string())
L.append("\nReference: Johannesburg ground monitors average roughly 25-30 ug/m3 PM2.5 (Zhang et al. 2021, "
         "Remote Sens Environ 266:112713). A much higher EAC4 mean points to model bias at this grid cell: "
         "report it, do not 'correct' it.")
L.append("Expect winter (Jun-Aug) peaks in PM2.5, NO2 and CO in Johannesburg.")
out = p.replace(".csv", "_qc.txt")
open(out, "w").write("\n".join(L))
print("\n".join(L))
