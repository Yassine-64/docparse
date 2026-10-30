import time

import pytest
from fastapi.testclient import TestClient

from docparse.infrastructure.config.settings import Settings
from docparse.interfaces.api.app import create_app

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    app = create_app(Settings(_env_file=None, api_key="secret"))
    with TestClient(app) as c:
        yield c


AUTH = {"Authorization": "Bearer secret"}


def test_health_lists_engines(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and ".pdf" in body["supported"] and "ocr" in body["engines"]


def test_parse_endpoints_and_auth(client, text_pdf):
    files = {"file": ("report.pdf", text_pdf.read_bytes(), "application/pdf")}
    assert client.post("/v1/parse/markdown", files=files).status_code == 401
    r = client.post("/v1/parse/markdown", files=files, headers=AUTH)
    assert r.status_code == 200 and "# Quarterly Report" in r.json()["markdown"]
    r = client.post("/v1/parse/chunks", files=files, headers=AUTH)
    assert r.json()["chunks"][0]["provenance"][0]["page"] == 1
    bad = {"file": ("x.exe", b"nope", "application/octet-stream")}
    assert client.post("/v1/parse", files=bad, headers=AUTH).status_code == 415


def test_job_flow(client, text_pdf):
    files = {"file": ("report.pdf", text_pdf.read_bytes(), "application/pdf")}
    r = client.post("/v1/jobs", files=files, headers=AUTH)
    assert r.status_code == 202
    job_id = r.json()["job_id"]
    for _ in range(50):
        body = client.get(f"/v1/jobs/{job_id}", headers=AUTH).json()
        if body["status"] in {"done", "failed"}:
            break
        time.sleep(0.1)
    assert body["status"] == "done" and body["report"]["passed"] and "Quarterly" in body["markdown"]
    assert client.get("/v1/jobs/nope", headers=AUTH).status_code == 404
