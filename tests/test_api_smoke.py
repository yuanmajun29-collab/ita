from ita import __version__


def test_health_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == __version__


def test_history_empty(client):
    resp = client.get("/api/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["result"]["total"] == 0
    assert data["result"]["records"] == []


def test_trend_empty(client):
    resp = client.get("/api/trend?days=7")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["result"]["days"] == 7
    assert data["result"]["records"] == []


def test_uv_advice_basic(client):
    resp = client.post(
        "/api/uv-advice",
        params={"ita": 35.2, "fitzpatrick": "II-III", "month": 6, "hour": 11},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "vitd" in data["result"]
    assert "recommendations" in data["result"]


def test_analyze_rejects_invalid_extension(client):
    files = {"file": ("invalid.txt", b"not an image", "text/plain")}
    resp = client.post("/api/analyze", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "不支持的文件格式" in data["message"]
