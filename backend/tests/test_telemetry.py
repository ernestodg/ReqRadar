import uuid

from app.core.config import Settings
from app.integrations import analytics
from app.integrations.analytics import safe_properties
from app.integrations.error_monitoring import before_send
from app.models import Feedback
from app.core.db import SessionLocal
from tests.test_api_workflow import create_project, import_csv, prepared_comparison


def test_safe_properties_excludes_sensitive_values():
    properties = safe_properties(
        Settings(app_env="test", app_release="v-test"),
        {
            "workspace_id": "workspace-1",
            "message": "SECRET REQUIREMENT TEXT",
            "authorization": "Bearer secret-token",
            "reviewer_note": "reviewer confidential note",
            "requirement_count": 10,
        },
    )

    assert properties["workspace_id"] == "workspace-1"
    assert properties["requirement_count"] == 10
    assert "SECRET REQUIREMENT TEXT" not in str(properties)
    assert "Bearer secret-token" not in str(properties)
    assert "reviewer confidential note" not in str(properties)


def test_sentry_before_send_filters_sensitive_payloads():
    event = before_send(
        {
            "request": {
                "headers": {"Authorization": "Bearer secret-token", "Cookie": "session=secret", "X-Request-Id": "request-1"},
                "data": {"requirement": "SECRET REQUIREMENT TEXT"},
            },
            "extra": {"DATABASE_URL": "postgresql://secret", "safe": "ok"},
        },
        None,
    )

    assert event["request"]["headers"]["Authorization"] == "[Filtered]"
    assert event["request"]["headers"]["Cookie"] == "[Filtered]"
    assert event["request"]["data"] == "[Filtered]"
    assert event["extra"]["DATABASE_URL"] == "[Filtered]"
    assert event["extra"]["safe"] == "ok"
    assert "SECRET REQUIREMENT TEXT" not in str(event)
    assert "Bearer secret-token" not in str(event)


def test_telemetry_failure_does_not_break_core_workflows(client, user_headers, monkeypatch):
    class FailingAnalytics:
        def capture(self, *args, **kwargs):
            raise RuntimeError("telemetry unavailable")

    analytics.get_analytics.cache_clear()
    monkeypatch.setattr("app.integrations.analytics.get_analytics", lambda: FailingAnalytics())
    project, comparison = prepared_comparison(client, user_headers)

    result = client.get(f"/projects/{project['id']}/comparisons/{comparison['id']}", headers=user_headers).json()
    review = client.patch(f"/findings/{result['findings'][0]['id']}", json={"review_status": "CONFIRMED", "reviewer_note": "reviewer confidential note"}, headers=user_headers)
    executive = client.get(f"/projects/{project['id']}/comparisons/{comparison['id']}/export.pdf?type=executive", headers=user_headers)
    audit = client.get(f"/projects/{project['id']}/comparisons/{comparison['id']}/export.pdf?type=audit", headers=user_headers)

    assert project["id"]
    assert comparison["id"]
    assert review.status_code == 200
    assert executive.status_code == 200
    assert audit.status_code == 200


def test_successful_business_events_emit_safe_metadata(client, user_headers, monkeypatch):
    events = []
    monkeypatch.setattr("app.main.capture_event", lambda user_id, event, properties=None: events.append((user_id, event, properties or {})))

    project = create_project(client, user_headers)
    first_import = import_csv(client, project["id"], user_headers, "requirements-v1.csv", "V1")
    second_import = import_csv(client, project["id"], user_headers, "requirements-v2.csv", "V2")
    comparison = client.post(
        f"/projects/{project['id']}/comparisons",
        json={"baseline_import_id": first_import["id"], "comparison_import_id": second_import["id"]},
        headers=user_headers,
    ).json()
    result = client.get(f"/projects/{project['id']}/comparisons/{comparison['id']}", headers=user_headers).json()
    client.patch(f"/findings/{result['findings'][0]['id']}", json={"review_status": "CONFIRMED", "reviewer_note": "reviewer confidential note"}, headers=user_headers)
    client.get(f"/projects/{project['id']}/comparisons/{comparison['id']}/export.pdf?type=executive", headers=user_headers)
    client.get(f"/projects/{project['id']}/comparisons/{comparison['id']}/export.pdf?type=audit", headers=user_headers)

    event_names = [event for _, event, _ in events]
    assert event_names.count("project_created") == 1
    assert event_names.count("import_completed") == 2
    assert event_names.count("comparison_completed") == 1
    assert event_names.count("finding_reviewed") == 1
    assert event_names.count("executive_report_exported") == 1
    assert event_names.count("full_audit_exported") == 1
    assert any(properties.get("project_import_count") == 2 for _, event, properties in events if event == "import_completed")
    assert "reviewer confidential note" not in str(events)
    assert "requirements-v1.csv" not in str(events)


def test_failed_operations_do_not_emit_success_events(client, user_headers, monkeypatch):
    events = []
    monkeypatch.setattr("app.main.capture_event", lambda user_id, event, properties=None: events.append(event))

    project = create_project(client, user_headers)
    events.clear()

    failed_project = client.post("/projects", json={"name": "Second", "description": ""}, headers=user_headers)
    failed_import = client.post(
        f"/projects/{project['id']}/imports",
        json={"filename": "bad.csv", "version_label": "Bad", "csv_text": "Requirement ID,Title\nREQ-1,A\nREQ-1,B\n", "mapping": {"Requirement ID": "Requirement ID", "Title": "Title"}},
        headers=user_headers,
    )
    failed_comparison = client.post(
        f"/projects/{project['id']}/comparisons",
        json={"baseline_import_id": str(uuid.uuid4()), "comparison_import_id": str(uuid.uuid4())},
        headers=user_headers,
    )
    failed_review = client.patch(f"/findings/{uuid.uuid4()}", json={"review_status": "CONFIRMED"}, headers=user_headers)
    failed_export = client.get(f"/projects/{project['id']}/comparisons/{uuid.uuid4()}/export.pdf?type=executive", headers=user_headers)

    assert failed_project.status_code == 403
    assert failed_import.status_code == 400
    assert failed_comparison.status_code == 404
    assert failed_review.status_code == 404
    assert failed_export.status_code == 404
    assert events == []


def test_idempotent_comparison_retry_does_not_emit_second_completion(client, user_headers, monkeypatch):
    events = []
    monkeypatch.setattr("app.main.capture_event", lambda user_id, event, properties=None: events.append(event))

    project = create_project(client, user_headers)
    first_import = import_csv(client, project["id"], user_headers, "requirements-v1.csv", "V1")
    second_import = import_csv(client, project["id"], user_headers, "requirements-v2.csv", "V2")
    payload = {"baseline_import_id": first_import["id"], "comparison_import_id": second_import["id"]}
    first = client.post(f"/projects/{project['id']}/comparisons", json=payload, headers=user_headers)
    retry = client.post(f"/projects/{project['id']}/comparisons", json=payload, headers=user_headers)

    assert first.status_code == 200
    assert retry.status_code == 200
    assert events.count("comparison_completed") == 1


def test_feedback_persists_and_emits_without_message_in_telemetry(client, user_headers, monkeypatch):
    events = []
    monkeypatch.setattr("app.main.capture_event", lambda user_id, event, properties=None: events.append((event, properties or {})))

    response = client.post("/feedback", json={"feedback_type": "Bug", "message": "SECRET REQUIREMENT TEXT in feedback only", "screen": "comparison"}, headers=user_headers)

    assert response.status_code == 200, response.text
    assert len(events) == 1
    assert events[0][0] == "feedback_submitted"
    assert events[0][1]["feedback_type"] == "Bug"
    assert events[0][1]["screen"] == "comparison"
    assert "workspace_id" in events[0][1]
    assert "SECRET REQUIREMENT TEXT" not in str(events)
    with SessionLocal() as db:
        saved = db.query(Feedback).filter_by(id=uuid.UUID(response.json()["id"])).one()
        assert saved.message == "SECRET REQUIREMENT TEXT in feedback only"
