import base64
from pathlib import Path

from tests.conftest import sample_mapping


def create_project(client, headers, name="Project"):
    response = client.post("/projects", json={"name": name, "description": ""}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def import_csv(client, project_id, headers, filename, version):
    text = Path(f"../sample-data/{filename}").read_text()
    response = client.post(f"/projects/{project_id}/imports", json={"filename": filename, "version_label": version, "csv_text": text, "mapping": sample_mapping()}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def create_comparison(client, project_id, headers):
    detail = client.get(f"/projects/{project_id}", headers=headers).json()
    response = client.post(f"/projects/{project_id}/comparisons", json={"baseline_import_id": detail["imports"][0]["id"], "comparison_import_id": detail["imports"][1]["id"]}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def prepared_comparison(client, headers):
    project = create_project(client, headers)
    import_csv(client, project["id"], headers, "requirements-v1.csv", "V1")
    import_csv(client, project["id"], headers, "requirements-v2.csv", "V2")
    comparison = create_comparison(client, project["id"], headers)
    return project, comparison


def test_api_workflow_counts_review_history_and_exports(client, user_headers):
    project, comparison = prepared_comparison(client, user_headers)
    assert comparison["summary_json"]["ADDED"] == 2
    assert comparison["summary_json"]["REMOVED"] == 0
    assert comparison["summary_json"]["MODIFIED"] == 16
    assert comparison["summary_json"]["UNCHANGED"] == 20
    result = client.get(f"/projects/{project['id']}/comparisons/{comparison['id']}", headers=user_headers).json()
    assert len(result["changes"]) == 38
    assert result["findings"]
    finding_id = result["findings"][0]["id"]
    confirmed = client.patch(f"/findings/{finding_id}", json={"review_status": "CONFIRMED", "severity": "LOW", "reviewer_note": "Reviewed"}, headers=user_headers)
    assert confirmed.status_code == 200
    assert confirmed.json()["review_status"] == "CONFIRMED"
    assert confirmed.json()["severity"] == "LOW"
    assert confirmed.json()["reviewer_note"] == "Reviewed"
    dismissed = client.patch(f"/findings/{result['findings'][1]['id']}", json={"review_status": "DISMISSED"}, headers=user_headers)
    assert dismissed.json()["review_status"] == "DISMISSED"
    history = client.get(f"/projects/{project['id']}", headers=user_headers).json()
    assert history["comparisons"][0]["id"] == comparison["id"]
    csv_export = client.get(f"/projects/{project['id']}/comparisons/{comparison['id']}/export.csv", headers=user_headers).json()
    pdf_export = client.get(f"/projects/{project['id']}/comparisons/{comparison['id']}/export.pdf", headers=user_headers).json()
    assert csv_export["media_type"] == "text/csv"
    assert pdf_export["media_type"] == "application/pdf"
    assert len(base64.b64decode(csv_export["content_base64"])) > 100
    assert len(base64.b64decode(pdf_export["content_base64"])) > 100


def test_upload_validation_and_plan_limits(client, user_headers):
    project = create_project(client, user_headers)
    second = client.post("/projects", json={"name": "Second", "description": ""}, headers=user_headers)
    assert second.status_code == 403
    bad_type = client.post("/imports/preview", files={"file": ("bad.txt", "x,y\n1,2\n", "text/plain")}, headers=user_headers)
    assert bad_type.status_code == 400
    oversized = client.post("/imports/preview", files={"file": ("big.csv", b"a" * (10 * 1024 * 1024 + 1), "text/csv")}, headers=user_headers)
    assert oversized.status_code == 413
    import_csv(client, project["id"], user_headers, "requirements-v1.csv", "V1")
    import_csv(client, project["id"], user_headers, "requirements-v2.csv", "V2")
    third = client.post(f"/projects/{project['id']}/imports", json={"filename": "requirements-v1.csv", "version_label": "V3", "csv_text": Path("../sample-data/requirements-v1.csv").read_text(), "mapping": sample_mapping()}, headers=user_headers)
    assert third.status_code == 403


def test_csv_formula_injection_protection():
    from app.main import safe_csv

    assert safe_csv("=SUM(A1:A2)") == "'=SUM(A1:A2)"
    assert safe_csv("+cmd") == "'+cmd"
    assert safe_csv("-cmd") == "'-cmd"
    assert safe_csv("@cmd") == "'@cmd"
