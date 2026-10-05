from types import SimpleNamespace
from app.models import ChangeType
from app.services.compare import changed_fields, detect_impacts, readable_diff, severity_for


def snap(**kwargs):
    defaults = {
        "external_id": "REQ-1",
        "related_external_ids": [],
        "parent_external_id": None,
        "normalized_text": "",
        "requirement_type": "Rule",
        "title": "",
        "description": "",
        "status": "",
        "tags": [],
        "owner": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_readable_diff_marks_changes():
    diff = readable_diff("supervisors may reopen bookings", "administrators may reopen bookings")
    assert "- supervisors" in diff
    assert "+ administrators" in diff


def test_explicit_relationship_scores_high():
    change = SimpleNamespace(id="change-1", change_type=ChangeType.MODIFIED)
    changed = snap(external_id="BR-STATUS-02", related_external_ids=["AC-BOOK-17"], normalized_text="only administrators may reopen booking")
    candidate = snap(external_id="AC-BOOK-17", normalized_text="supervisor sees reopen action")
    findings = detect_impacts(change, changed, [changed, candidate])
    assert findings
    assert findings[0].impacted_requirement_external_id == "AC-BOOK-17"
    assert findings[0].impact_score >= 60


def test_reverse_relationship_and_identifier_reference_and_severity():
    change = SimpleNamespace(id="change-1", change_type=ChangeType.MODIFIED)
    changed = snap(external_id="BR-STATUS-02", normalized_text="BR-STATUS-02 changes AC-BOOK-17 behavior")
    reverse = snap(external_id="TC-BOOK-22", related_external_ids=["BR-STATUS-02"], normalized_text="test reopens booking")
    identifier = snap(external_id="AC-BOOK-17", normalized_text="acceptance criteria")
    findings = detect_impacts(change, changed, [changed, reverse, identifier])
    by_id = {finding.impacted_requirement_external_id: finding for finding in findings}
    assert by_id["TC-BOOK-22"].impact_score >= 50
    assert by_id["AC-BOOK-17"].impact_score >= 45
    assert severity_for(75).value == "HIGH"
    assert severity_for(45).value == "MEDIUM"
    assert severity_for(10).value == "LOW"


def test_changed_field_identification():
    old = snap(description="Old", status="Approved")
    new = snap(description="New", status="Draft")
    fields = changed_fields(old, new)
    assert fields["description"] == {"old": "Old", "new": "New"}
    assert fields["status"] == {"old": "Approved", "new": "Draft"}
