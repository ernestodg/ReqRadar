from app.core.db import SessionLocal
from app.models import Project, Workspace
from tests.test_api_workflow import prepared_comparison


def test_workspace_a_cannot_access_workspace_b_api_resources(client):
    user_a = {"x-dev-user-id": "tenant-a"}
    user_b = {"x-dev-user-id": "tenant-b"}
    project_b, comparison_b = prepared_comparison(client, user_b)
    result_b = client.get(f"/projects/{project_b['id']}/comparisons/{comparison_b['id']}", headers=user_b).json()
    finding_b = result_b["findings"][0]["id"]

    assert client.get(f"/projects/{project_b['id']}", headers=user_a).status_code == 404
    assert client.get(f"/projects/{project_b['id']}/comparisons/{comparison_b['id']}", headers=user_a).status_code == 404
    assert client.patch(f"/findings/{finding_b}", json={"review_status": "CONFIRMED"}, headers=user_a).status_code == 404
    assert client.get(f"/projects/{project_b['id']}/comparisons/{comparison_b['id']}/export.csv", headers=user_a).status_code == 404
    assert client.get(f"/projects/{project_b['id']}/comparisons/{comparison_b['id']}/export.pdf", headers=user_a).status_code == 404
    assert client.post(f"/projects/{project_b['id']}/comparisons", json={"baseline_import_id": result_b["comparison"]["baseline_import_id"], "comparison_import_id": result_b["comparison"]["comparison_import_id"]}, headers=user_a).status_code == 404


def test_same_workspace_nested_resources_must_match_parent_project(client):
    user = {"x-dev-user-id": "tenant-nested"}
    project_b, comparison_b = prepared_comparison(client, user)
    client.get("/me", headers=user)
    with SessionLocal() as db:
        workspace = db.query(Workspace).filter_by(owner_user_id="tenant-nested").one()
        project_a = Project(workspace_id=workspace.id, name="Sibling Project", description="")
        db.add(project_a)
        db.commit()
        sibling_project_id = project_a.id

    assert client.get(f"/projects/{sibling_project_id}/comparisons/{comparison_b['id']}", headers=user).status_code == 404
    assert client.get(f"/projects/{sibling_project_id}/comparisons/{comparison_b['id']}/export.csv", headers=user).status_code == 404
    assert client.get(f"/projects/{sibling_project_id}/comparisons/{comparison_b['id']}/export.pdf", headers=user).status_code == 404
