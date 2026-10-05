import base64
import re
import uuid
import zlib
from pathlib import Path

from app.core.db import SessionLocal
from app.models import ChangeType, Comparison, ImpactFinding, ImportBatch, RequirementChange, ReviewStatus, Severity
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


def pdf_bytes(export: dict) -> bytes:
    assert export["media_type"] == "application/pdf"
    content = base64.b64decode(export["content_base64"])
    assert content.startswith(b"%PDF")
    assert len(content) > 1000
    return content


def pdf_text(export: dict) -> str:
    content = pdf_bytes(export)
    chunks = [content]
    for match in re.finditer(rb"(<<.*?>>)\s*stream\r?\n(.*?)\r?\nendstream", content, re.DOTALL):
        header, stream = match.groups()
        data = stream
        if b"ASCII85Decode" in header:
            data = base64.a85decode(data.strip(), adobe=True)
        if b"FlateDecode" in header:
            data = zlib.decompress(data)
        chunks.append(data)
    raw = b"\n".join(chunks).decode("latin-1", errors="ignore")
    strings = re.findall(r"\((?:\\.|[^\\)])*\)", raw)
    decoded = []
    for item in strings:
        value = item[1:-1]
        value = re.sub(r"\\([0-7]{1,3})", lambda match: chr(int(match.group(1), 8)), value)
        value = value.replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\")
        decoded.append(value)
    return "\n".join(decoded) + "\n" + raw


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
    text = pdf_text(pdf_export)
    assert "ReqRadar" in text
    assert "Requirements Impact Analysis" in text
    assert "Project" in text
    assert "MODIFIED" in text
    assert "16" in text
    assert "POTENTIAL IMPACTS" in text
    assert "High Impact Findings" in text
    assert "Medium Impact Findings" in text
    assert "Low Impact Findings" in text
    assert "CONFIRMED" in text
    assert "DISMISSED" in text
    assert "UNREVIEWED" in text
    assert "Reviewed" in text
    assert "Methodology" in text
    assert "Page 1 /" in text


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


def create_empty_comparison(project_id: str) -> str:
    with SessionLocal() as db:
        baseline = ImportBatch(project_id=uuid.UUID(project_id), filename="empty-v1.csv", version_label="V1", row_count=0, source_hash="baseline", mapping_json={}, status="COMPLETE")
        target = ImportBatch(project_id=uuid.UUID(project_id), filename="empty-v2.csv", version_label="V2", row_count=0, source_hash="target", mapping_json={}, status="COMPLETE")
        db.add_all([baseline, target])
        db.flush()
        comparison = Comparison(project_id=uuid.UUID(project_id), baseline_import_id=baseline.id, comparison_import_id=target.id, status="COMPLETE", summary_json={"ADDED": 0, "REMOVED": 0, "MODIFIED": 0, "UNCHANGED": 0, "impact_findings": 0, "high_impact": 0})
        db.add(comparison)
        db.commit()
        return str(comparison.id)


def test_pdf_report_handles_zero_findings(client, user_headers):
    project = create_project(client, user_headers, name="Zero Finding Report")
    comparison_id = create_empty_comparison(project["id"])
    export = client.get(f"/projects/{project['id']}/comparisons/{comparison_id}/export.pdf", headers=user_headers).json()
    text = pdf_text(export)
    assert "Zero Finding Report" in text
    assert "POTENTIAL IMPACTS" in text
    assert "0" in text
    assert "Methodology" in text
    assert "High Impact Findings" not in text


def create_large_low_only_report(project_id: str, count: int = 80) -> str:
    with SessionLocal() as db:
        project_uuid = uuid.UUID(project_id)
        baseline = ImportBatch(project_id=project_uuid, filename="large-v1.csv", version_label="V1", row_count=count, source_hash="large-baseline", mapping_json={}, status="COMPLETE")
        target = ImportBatch(project_id=project_uuid, filename="large-v2.csv", version_label="V2", row_count=count, source_hash="large-target", mapping_json={}, status="COMPLETE")
        db.add_all([baseline, target])
        db.flush()
        comparison = Comparison(project_id=project_uuid, baseline_import_id=baseline.id, comparison_import_id=target.id, status="COMPLETE", summary_json={"ADDED": 0, "REMOVED": 0, "MODIFIED": count, "UNCHANGED": 0, "impact_findings": count, "high_impact": 0})
        db.add(comparison)
        db.flush()
        changes = []
        findings = []
        long_reason = " ".join(["This deliberately long requirements impact explanation wraps safely inside the report card without clipping or overlapping adjacent content."] * 4)
        for index in range(count):
            change = RequirementChange(comparison_id=comparison.id, external_id=f"REQ-LONG-{index:03d}", change_type=ChangeType.MODIFIED, changed_fields={"description": True}, text_diff="long text changed")
            db.add(change)
            changes.append(change)
        db.flush()
        for index, change in enumerate(changes):
            findings.append(ImpactFinding(requirement_change_id=change.id, impacted_requirement_external_id=f"AC-LONG-{index:03d}", severity=Severity.LOW, confidence=0.51, impact_score=51, detection_method="long_text_test", reason=long_reason, relationship_type="text_similarity", review_status=ReviewStatus.UNREVIEWED, reviewer_note="Long reviewer note " + ("with extra context " * 12)))
        db.add_all(findings)
        db.commit()
        return str(comparison.id)


def test_pdf_report_handles_single_severity_long_text_and_large_findings(client, user_headers):
    project = create_project(client, user_headers, name="Large Low Report")
    comparison_id = create_large_low_only_report(project["id"])
    export = client.get(f"/projects/{project['id']}/comparisons/{comparison_id}/export.pdf", headers=user_headers).json()
    content = pdf_bytes(export)
    text = content.decode("latin-1", errors="ignore")
    assert "Large Low Report" in text
    assert "Low Impact Findings" in text
    assert "High Impact Findings" not in text
    assert "REQ-LONG-000" in text
    assert "AC-LONG-079" in text
    assert len(content) > 20_000
