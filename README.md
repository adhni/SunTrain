# SunTrain

Local analysis workspace for the Victorian train service passenger counts dataset.

## Structure

- `data/raw/`: source CSV
- `data/warehouse/`: full Parquet conversion and DuckDB database
- `data/processed/daily/`: day-level extracts
- `data/processed/werribee/`: Werribee-specific subsets and summaries
- `sql/`: reusable DuckDB queries
- `scripts/`: local analysis scripts
- `reports/`: written findings and generated figures

## Main files

- `data/raw/train_service_passenger_counts_fy_2023_2024.csv`
- `data/warehouse/train_service_passenger_counts_fy_2023_2024.parquet`
- `data/warehouse/suntrain.duckdb`
- `data/processed/werribee/werribee_2023-07-10.parquet`
- `sql/werribee_eda.sql`

## Git Notes

- `data/raw/` is local-only and ignored by git because the source CSV is too large for GitHub.
- The repo tracks the processed subsets, warehouse Parquet, DuckDB file, SQL, scripts, reports, and generated charts.

## Querying

Use `data/warehouse/suntrain.duckdb` in SQLTools and query the view:

```sql
SELECT *
FROM train_service_passenger_counts
WHERE Business_Date = DATE '2023-07-10'
  AND Line_Name = 'Werribee'
LIMIT 20;
```

## EDA Script

Run:

```bash
python3 scripts/werribee_eda.py
```

This reads `data/processed/werribee/werribee_2023-07-10.parquet` and writes charts to `reports/figures/werribee_2023-07-10/`.

## Dashboard

The repo now includes a multi-day Dash app backed directly by DuckDB.

Run locally:

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python app.py
```

Then open `http://127.0.0.1:8050`.

Notes:

- The app queries the warehouse Parquet directly through DuckDB, so it can handle additional dates without rebuilding a single-day dashboard dataset.
- The app reads `SUNTRAIN_PARQUET_GLOB`, so you can later point it at one file or a partition glob under `data/warehouse/`.
- Arrival and departure times are formatted in the UI as `HH:MM`.
- A basic health endpoint is available at `/health`.
- `render.yaml` is included as a starting point for Render deployment later.
