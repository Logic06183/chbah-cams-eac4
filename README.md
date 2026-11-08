# CAMS EAC4 daily air quality at Chris Hani Baragwanath Academic Hospital, 2016 to 2024

Daily PM2.5, NO2, CO and SO2 at Chris Hani Baragwanath Academic Hospital (CHBAH), Soweto. The values come from the CAMS global reanalysis (EAC4). The file is `data/cams_eac4_daily_chbah.csv`.

Read the caveats before using the numbers. PM2.5 from EAC4 runs about 5 times higher than ground monitors in Johannesburg.

## The data

`data/cams_eac4_daily_chbah.csv` has one row per day, 2016-01-01 to 2024-12-31 (3,288 days).

| Column | Meaning |
|---|---|
| `date` | Local day in South African Standard Time (SAST, UTC+2) |
| `n_fields` | Number of 3-hourly values in the day (always 8) |
| `pm25_ugm3_mean`, `pm25_ugm3_max` | PM2.5, µg/m³ |
| `no2_ugm3_mean`, `no2_ugm3_max` | NO2, µg/m³ |
| `co_ugm3_mean`, `co_ugm3_max` | CO, µg/m³ |
| `so2_ugm3_mean`, `so2_ugm3_max` | SO2, µg/m³ |

`data/cams_eac4_daily_chbah_qc.txt` has the QC summary. `data/verify_report.txt` has the independent recompute check.

## How it was made

- **Source:** the CAMS global reanalysis (EAC4) on the Copernicus Atmosphere Data Store, dataset `cams-global-reanalysis-eac4`. Downloaded 6 to 7 November 2026.
- **Grid:** EAC4 has a 0.75° grid with values every 3 hours (00 to 21 UTC). The site (-26.2609, 27.9432) uses the nearest grid cell, (-26.25, 27.75).
- **PM2.5:** taken at the surface and converted from kg/m³ to µg/m³.
- **NO2, CO, SO2:** taken at the lowest model level (level 60, about 10 m above ground) as a mass mixing ratio. They are converted to µg/m³ using surface air density, ρ = surface pressure / (287.05 × 2 m temperature).
- **Days:** UTC times shifted by 2 hours to SAST. Each SAST day holds the 8 values stamped 00 to 21 UTC on the same date. The daily max is the highest of those 8.

## Checks

| Check | Result |
|---|---|
| Rows | 3,288 of 3,288. No missing or duplicate dates. |
| Values per day | 8 on every day |
| Missing or non-positive values | none |
| Recompute from the raw files, separate code | 36 random days across all 9 years agree within 0.0008 µg/m³. All days agree within 0.003 µg/m³ (rounding). |
| Second recompute by an independent reviewer | All days agree within 0.00075 µg/m³. Units, model level and time convention confirmed against the NetCDF metadata. |

## Caveats

- **PM2.5 is strongly biased high.** The 2016 to 2024 mean is 154 µg/m³, and Johannesburg ground monitors average roughly 25 to 30 µg/m³. That makes EAC4 about 5.6 times higher. The June to August mean is 259 µg/m³, and the December to February mean is 59 µg/m³. CO and SO2 also look high for an urban site. The numbers here are not corrected. Use them for day-to-day variation, not absolute exposure.
- **The seasonal pattern is as expected.** PM2.5, NO2 and CO are all higher in winter (June to August) than in summer (December to February).
- **The daily max is a lower bound.** It is the highest of 8 three-hourly values, not a true hourly peak.
- **The values are regional background.** The grid cell is about 80 km across, and its centre is about 19 km west of CHBAH. These are not measurements at the hospital.
- **The gas conversion is approximate.** It uses surface air density at model level 60.

## Reproduce it

You need an Atmosphere Data Store (ADS) account and API key. Put them in `~/.cdsapirc`, or in any file you point `CDSAPI_RC` at:

```
url: https://ads.atmosphere.copernicus.eu/api
key: <your key>
```

Then run:

```
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python extract_cams_eac4_ads.py --years 2016-2024 --out out
.venv/bin/python qc_cams.py out/cams_eac4_daily_chbah.csv
.venv/bin/python verify_cams.py out
```

The extract sends 18 requests to ADS, one at a time. It took about 8 minutes per request when the queue was quiet. Finished years are cached in `out/raw_eac4/`, so a rerun picks up where it stopped.

## Licence and attribution

Generated using Copernicus Atmosphere Monitoring Service information (2026). Neither the European Commission nor ECMWF is responsible for any use of this information. When you use the data, cite the CAMS reanalysis: Inness, A. et al. (2019), The CAMS reanalysis of atmospheric composition, *Atmospheric Chemistry and Physics*, 19, 3515–3556.

Contact: Craig Parker, Wits Planetary Health Research.
