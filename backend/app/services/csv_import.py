import csv
import hashlib
import io
import re
from dataclasses import dataclass

RADAR_FIELDS = {
    "Requirement ID": ["requirement id", "requirement number", "id", "key", "issue key"],
    "Type": ["type", "category", "requirement type"],
    "Title": ["title", "summary", "name"],
    "Description": ["description", "details", "requirement", "text"],
    "Status": ["status", "state"],
    "Parent ID": ["parent", "parent id", "parent requirement"],
    "Related To": ["related to", "related", "links", "depends on"],
    "Tags": ["tags", "labels"],
    "Owner": ["owner", "assignee"],
}


@dataclass
class ParsedCsv:
    rows: list[dict[str, str]]
    columns: list[str]
    warnings: list[str]


def parse_csv(csv_text: str) -> ParsedCsv:
    sample = csv_text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample) if sample.strip() else csv.excel
        dialect.doublequote = True
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(csv_text), dialect=dialect)
    columns = reader.fieldnames or []
    warnings: list[str] = []
    if len(columns) != len(set(columns)):
        warnings.append("Duplicate column names were detected. Rename duplicate columns before importing.")
    rows = []
    malformed = 0
    for row in reader:
        if None in row:
            malformed += 1
        rows.append({k: (v or "").strip() for k, v in row.items() if k is not None})
    if malformed:
        warnings.append(f"{malformed} malformed rows contain more values than headers.")
    return ParsedCsv(rows=rows, columns=columns, warnings=warnings)


def suggest_mapping(columns: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    normalized = {c: c.lower().strip() for c in columns}
    for radar_field, aliases in RADAR_FIELDS.items():
        for col, norm in normalized.items():
            if norm in aliases or norm.replace("_", " ") in aliases:
                mapping[radar_field] = col
                break
    return mapping


def split_multi(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"[;,|]", value or "") if part.strip()]


def normalize_text(*parts: str) -> str:
    return re.sub(r"\s+", " ", " ".join(p or "" for p in parts)).strip().lower()


def content_hash(payload: dict) -> str:
    material = "|".join(str(payload.get(k, "")) for k in ["external_id", "requirement_type", "title", "description", "status", "parent_external_id", "related_external_ids", "tags", "owner"])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def validate_rows(rows: list[dict[str, str]], mapping: dict[str, str]) -> list[str]:
    warnings: list[str] = []
    id_col = mapping.get("Requirement ID")
    title_col = mapping.get("Title")
    if not id_col or not title_col:
        warnings.append("Requirement ID and Title mappings are required.")
        return warnings
    if not rows:
        warnings.append("CSV contains no requirement rows.")
        return warnings
    columns = set(rows[0])
    missing_columns = [column for column in mapping.values() if column and column not in columns]
    if missing_columns:
        warnings.append(f"Mapped column was not found in the CSV: {', '.join(sorted(set(missing_columns))[:10])}.")
        return warnings
    seen: set[str] = set()
    blanks = 0
    duplicates: set[str] = set()
    for row in rows:
        external_id = (row.get(id_col) or "").strip()
        if not external_id:
            blanks += 1
            continue
        if external_id in seen:
            duplicates.add(external_id)
        seen.add(external_id)
    if blanks:
        warnings.append(f"{blanks} rows are missing a Requirement ID.")
    if duplicates:
        warnings.append(f"Duplicate Requirement IDs detected: {', '.join(sorted(duplicates)[:10])}.")
    return warnings


def normalize_rows(rows: list[dict[str, str]], mapping: dict[str, str]) -> list[dict]:
    normalized = []
    for index, row in enumerate(rows, start=2):
        external_id = row.get(mapping["Requirement ID"], "").strip()
        title = row.get(mapping["Title"], "").strip()
        if not external_id:
            continue
        payload = {
            "external_id": external_id,
            "requirement_type": row.get(mapping.get("Type", ""), "").strip(),
            "title": title,
            "description": row.get(mapping.get("Description", ""), "").strip(),
            "status": row.get(mapping.get("Status", ""), "").strip(),
            "parent_external_id": row.get(mapping.get("Parent ID", ""), "").strip() or None,
            "related_external_ids": split_multi(row.get(mapping.get("Related To", ""), "")),
            "tags": split_multi(row.get(mapping.get("Tags", ""), "")),
            "owner": row.get(mapping.get("Owner", ""), "").strip() or None,
            "source_row_number": index,
            "metadata_json": {k: v for k, v in row.items() if k not in set(mapping.values())},
        }
        payload["normalized_text"] = normalize_text(payload["external_id"], payload["requirement_type"], payload["title"], payload["description"])
        payload["content_hash"] = content_hash(payload)
        normalized.append(payload)
    return normalized


def source_hash(csv_text: str) -> str:
    return hashlib.sha256(csv_text.encode("utf-8")).hexdigest()
