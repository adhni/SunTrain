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
- `render.yaml` is included for Render deployment.

## Deploying To Render

The repo is ready to deploy as a Python web service.

### Option 1: Use `render.yaml`

1. Push the repo to GitHub.
2. In Render, choose `New +` -> `Blueprint`.
3. Connect the GitHub repo and select this repository.
4. Render will read `render.yaml` and create the web service automatically.

### Option 2: Create The Web Service Manually

Use these settings:

- Environment: `Python`
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120 dashboard.app:server`
- Health Check Path: `/health`

Set this environment variable:

- `SUNTRAIN_PARQUET_GLOB=data/warehouse/train_service_passenger_counts*.parquet`

### Deployment Notes

- The current tracked Parquet warehouse file is included in the repo, so the first deploy can run without an external database.
- If you later add much larger Parquet files, consider moving the warehouse onto a Render disk or object storage instead of keeping all data in git.
