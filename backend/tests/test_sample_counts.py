from pathlib import Path

from app.services.csv_import import normalize_rows, parse_csv, suggest_mapping


def test_sample_v1_to_v2_expected_change_counts():
    data = {}
    for name, path in [("v1", "../sample-data/requirements-v1.csv"), ("v2", "../sample-data/requirements-v2.csv")]:
        parsed = parse_csv(Path(path).read_text())
        mapping = suggest_mapping(parsed.columns)
        data[name] = {row["external_id"]: row for row in normalize_rows(parsed.rows, mapping)}

    added = set(data["v2"]) - set(data["v1"])
    removed = set(data["v1"]) - set(data["v2"])
    common = set(data["v1"]) & set(data["v2"])
    modified = {key for key in common if data["v1"][key]["content_hash"] != data["v2"][key]["content_hash"]}
    unchanged = common - modified

    assert len(added) == 2
    assert len(removed) == 0
    assert len(modified) == 16
    assert len(unchanged) == 20
    assert sorted(added) == ["BR-PERM-02", "Q-004"]
