import csv
from io import StringIO

from app.services.csv_import import content_hash, normalize_rows, parse_csv, split_multi, suggest_mapping, validate_rows


def test_mapping_and_normalization():
    parsed = parse_csv("Requirement ID,Type,Title,Description,Related To\nREQ-1,Rule,Title,Body,AC-1;TC-1\n")
    mapping = suggest_mapping(parsed.columns)
    assert mapping["Requirement ID"] == "Requirement ID"
    assert validate_rows(parsed.rows, mapping) == []
    rows = normalize_rows(parsed.rows, mapping)
    assert rows[0]["external_id"] == "REQ-1"
    assert rows[0]["related_external_ids"] == ["AC-1", "TC-1"]


def test_duplicate_ids_warn():
    parsed = parse_csv("Requirement ID,Title\nREQ-1,A\nREQ-1,B\n")
    warnings = validate_rows(parsed.rows, {"Requirement ID": "Requirement ID", "Title": "Title"})
    assert any("Duplicate Requirement IDs" in warning for warning in warnings)


def test_common_name_mapping_and_blank_ids_and_malformed_rows():
    parsed = parse_csv("Requirement Number,Summary,Category\nREQ-1,A,Rule\n,B,Rule\nREQ-2,C,Rule,extra\n")
    mapping = suggest_mapping(parsed.columns)
    assert mapping["Requirement ID"] == "Requirement Number"
    assert mapping["Title"] == "Summary"
    assert mapping["Type"] == "Category"
    warnings = parsed.warnings + validate_rows(parsed.rows, mapping)
    assert any("malformed rows" in warning for warning in warnings)
    assert any("missing a Requirement ID" in warning for warning in warnings)


def test_header_only_csv_warns_no_requirement_rows():
    parsed = parse_csv("Requirement ID,Title\n")
    warnings = validate_rows(parsed.rows, {"Requirement ID": "Requirement ID", "Title": "Title"})
    assert warnings == ["CSV contains no requirement rows."]


def test_missing_mapped_column_warns_before_normalization():
    parsed = parse_csv("Requirement ID,Title\nREQ-1,A\n")
    warnings = validate_rows(parsed.rows, {"Requirement ID": "Requirement ID", "Title": "Missing Title"})
    assert any("Mapped column was not found" in warning for warning in warnings)


def test_csv_parser_preserves_quoted_commas_quotes_and_newlines():
    handle = StringIO()
    writer = csv.writer(handle)
    writer.writerow(["Requirement ID", "Title", "Description"])
    writer.writerow(["REQ-1", "Title, with comma", 'Line one\nLine "two"'])
    parsed = parse_csv(handle.getvalue())
    rows = normalize_rows(parsed.rows, {"Requirement ID": "Requirement ID", "Title": "Title", "Description": "Description"})
    assert rows[0]["title"] == "Title, with comma"
    assert rows[0]["description"] == 'Line one\nLine "two"'


def test_relationship_delimiter_normalization():
    assert split_multi("AC-1, TC-1|BR-1; Q-1") == ["AC-1", "TC-1", "BR-1", "Q-1"]


def test_content_hash_uses_meaningful_requirement_content_only():
    base = {"external_id": "REQ-1", "requirement_type": "Rule", "title": "Title", "description": "Body", "status": "Approved", "parent_external_id": None, "related_external_ids": ["AC-1"], "tags": [], "owner": "A", "source_row_number": 2, "import_batch_id": "batch-1"}
    changed_volatile = {**base, "source_row_number": 99, "import_batch_id": "batch-2", "metadata_json": {"raw": "ignored"}}
    changed_meaningful = {**base, "description": "Changed"}
    assert content_hash(base) == content_hash(changed_volatile)
    assert content_hash(base) != content_hash(changed_meaningful)
