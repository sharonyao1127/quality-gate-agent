import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from src.web_app import app


client = TestClient(app)


def test_index_page_renders_form():
    response = client.get("/")

    assert response.status_code == 200
    assert "Quality Gate Agent" in response.text
    assert "API Change Summary" in response.text
    assert "Analyze" in response.text


def test_analyze_page_shows_risk_score_impacted_areas_and_pr_comment():
    change_summary = "provider callback timeout delayed"
    response = client.post("/analyze", data={"change_summary": change_summary})

    assert response.status_code == 200
    assert "Risk Score:" in response.text
    assert "Impacted Areas" in response.text
    assert "PR Comment" in response.text
    assert "external provider callback" in response.text
