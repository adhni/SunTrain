from __future__ import annotations

import importlib


def test_health_endpoint_reports_app_status(monkeypatch, sample_parquet):
    monkeypatch.setenv("SUNTRAIN_PARQUET_GLOB", str(sample_parquet))

    import dashboard.data as data_module
    import dashboard.app as app_module

    importlib.reload(data_module)
    app_module = importlib.reload(app_module)

    client = app_module.server.test_client()
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "app": "suntrain-dashboard"}
