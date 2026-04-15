"""
快速验证 Demo：
使用 FastAPI TestClient 在本地进程内验证关键 API 可用性。

运行方式：
    python3 scripts/verify_demo.py
"""

from pathlib import Path

from fastapi.testclient import TestClient

from ita.api.main import app
from ita.core.database import Database
from ita.core import database as db_module


def main():
    db_path = Path(__file__).resolve().parent.parent / "demo_verify.db"
    db_module._db_instance = Database(str(db_path))

    client = TestClient(app)
    checks = []

    # 1) health
    health = client.get("/api/health")
    checks.append(("GET /api/health", health.status_code == 200 and health.json().get("status") == "ok"))

    # 2) history (empty)
    history = client.get("/api/history?limit=5")
    h_data = history.json()
    checks.append(("GET /api/history", history.status_code == 200 and h_data.get("success") is True))

    # 3) trend
    trend = client.get("/api/trend?days=7")
    t_data = trend.json()
    checks.append(("GET /api/trend", trend.status_code == 200 and t_data.get("success") is True))

    # 4) uv advice
    uv = client.post(
        "/api/uv-advice",
        params={"ita": 32.5, "fitzpatrick": "II-III", "month": 6, "hour": 11},
    )
    uv_data = uv.json()
    checks.append(("POST /api/uv-advice", uv.status_code == 200 and uv_data.get("success") is True))

    # 5) analyze negative case
    analyze = client.post("/api/analyze", files={"file": ("bad.txt", b"demo", "text/plain")})
    a_data = analyze.json()
    checks.append(("POST /api/analyze (invalid file)", analyze.status_code == 200 and a_data.get("success") is False))

    print("=== ITA Demo 验证结果 ===")
    ok_count = 0
    for name, ok in checks:
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}")
        if ok:
            ok_count += 1

    print(f"\n通过 {ok_count}/{len(checks)} 项")
    if ok_count != len(checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
