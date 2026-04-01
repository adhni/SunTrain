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
