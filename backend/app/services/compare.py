import difflib
import re
from collections import Counter, defaultdict
from rapidfuzz import fuzz
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models import ChangeType, Comparison, ImpactFinding, RequirementChange, RequirementSnapshot, Severity


ID_PATTERN = re.compile(r"\b[A-Z]{1,5}-[A-Z0-9]+-\d{1,4}\b|\b(?:REQ|AC|BR|TC|Q)-[A-Z0-9-]+\b")


def readable_diff(old: str, new: str) -> str:
    old_words = old.split()
    new_words = new.split()
    return " ".join(difflib.ndiff(old_words, new_words))


def changed_fields(old: RequirementSnapshot, new: RequirementSnapshot) -> dict:
    fields = ["requirement_type", "title", "description", "status", "parent_external_id", "related_external_ids", "tags", "owner"]
    return {field: {"old": getattr(old, field), "new": getattr(new, field)} for field in fields if getattr(old, field) != getattr(new, field)}


def severity_for(score: int) -> Severity:
    settings = get_settings()
    if score >= settings.high_threshold:
        return Severity.HIGH
    if score >= settings.medium_threshold:
        return Severity.MEDIUM
    return Severity.LOW


def build_comparison(db: Session, comparison: Comparison) -> None:
    old_items = {r.external_id: r for r in db.query(RequirementSnapshot).filter_by(import_batch_id=comparison.baseline_import_id).all()}
    new_items = {r.external_id: r for r in db.query(RequirementSnapshot).filter_by(import_batch_id=comparison.comparison_import_id).all()}
    all_ids = sorted(set(old_items) | set(new_items))
    summary = Counter({"ADDED": 0, "REMOVED": 0, "MODIFIED": 0, "UNCHANGED": 0, "impact_findings": 0, "high_impact": 0})
    changes: list[RequirementChange] = []
    for external_id in all_ids:
        old = old_items.get(external_id)
        new = new_items.get(external_id)
        if old is None:
            change_type = ChangeType.ADDED
        elif new is None:
            change_type = ChangeType.REMOVED
        elif old.content_hash == new.content_hash:
            change_type = ChangeType.UNCHANGED
        else:
            change_type = ChangeType.MODIFIED
        fields = changed_fields(old, new) if old and new and change_type == ChangeType.MODIFIED else {}
        diff = readable_diff(old.normalized_text if old else "", new.normalized_text if new else "")
        change = RequirementChange(comparison_id=comparison.id, external_id=external_id, change_type=change_type, old_snapshot_id=old.id if old else None, new_snapshot_id=new.id if new else None, changed_fields=fields, text_diff=diff)
        db.add(change)
        changes.append(change)
        summary[change_type.value] += 1
    db.flush()
    current = list(new_items.values())
    for change in changes:
        if change.change_type == ChangeType.UNCHANGED:
            continue
        changed_snapshot = new_items.get(change.external_id) or old_items.get(change.external_id)
        if changed_snapshot is None:
            continue
        for finding in detect_impacts(change, changed_snapshot, current):
            db.add(finding)
            summary["impact_findings"] += 1
            if finding.severity == Severity.HIGH:
                summary["high_impact"] += 1
    comparison.summary_json = dict(summary)
    comparison.status = "COMPLETE"
    db.commit()


def detect_impacts(change: RequirementChange, changed: RequirementSnapshot, candidates: list[RequirementSnapshot]) -> list[ImpactFinding]:
    findings = []
    explicit_targets = set(changed.related_external_ids or [])
    if changed.parent_external_id:
        explicit_targets.add(changed.parent_external_id)
    referenced_ids = set(ID_PATTERN.findall(changed.normalized_text.upper()))
    for candidate in candidates:
        if candidate.external_id == changed.external_id:
            continue
        score = 0
        methods = []
        reasons = []
        relation = "possible dependency"
        if candidate.external_id in explicit_targets:
            score += 60
            methods.append("explicit_relationship")
            reasons.append(f"{changed.external_id} directly references {candidate.external_id}.")
            relation = "explicit relationship"
        if changed.external_id in set(candidate.related_external_ids or []) or candidate.parent_external_id == changed.external_id:
            score += 50
            methods.append("reverse_relationship")
            reasons.append(f"{candidate.external_id} references the changed requirement.")
            relation = "reverse relationship"
        if candidate.external_id in referenced_ids:
            score += 45
            methods.append("identifier_reference")
            reasons.append(f"The changed requirement text mentions {candidate.external_id}.")
        if candidate.parent_external_id and candidate.parent_external_id == changed.parent_external_id:
            score += 20
            methods.append("same_parent")
            reasons.append("Both requirements share the same parent.")
        similarity = fuzz.token_set_ratio(changed.normalized_text, candidate.normalized_text)
        if similarity >= 82:
            add = min(30, max(10, int((similarity - 75) / 25 * 30)))
            score += add
            methods.append("text_similarity")
            reasons.append(f"Requirement text is similar ({similarity:.0f}%).")
        if score >= 25:
            findings.append(ImpactFinding(requirement_change_id=change.id, impacted_requirement_external_id=candidate.external_id, severity=severity_for(score), confidence=min(0.98, score / 100), impact_score=score, detection_method="+".join(methods), reason=" ".join(reasons), relationship_type=relation))
    return findings


def summary_for_changes(changes: list[RequirementChange]) -> dict:
    counter = defaultdict(int)
    for change in changes:
        counter[change.change_type.value] += 1
    return dict(counter)
