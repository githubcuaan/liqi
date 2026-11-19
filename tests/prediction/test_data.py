import csv
import json

import pytest

from liqily.prediction.data import (
    DEFAULT_DATASET,
    InvalidField,
    audit_dataset,
    load_csv,
    parse_game,
    parse_heroes,
)


def valid_row(game_id="game-1", series_id="series-1"):
    return {
        "game_id": game_id,
        "series_id": series_id,
        "team_a_heroes": json.dumps(["a1", "a2", "a3", "a4", "a5"]),
        "team_b_heroes": json.dumps(["b1", "b2", "b3", "b4", "b5"]),
        "team_a_side": "blue",
        "patch_id": "aov:vn:2026-02-14",
        "team_a_win": "false",
        "split": "train",
    }


def make_dataset(tmp_path, by_split):
    csv_dir = tmp_path / "csv"
    csv_dir.mkdir()
    with (csv_dir / "heroes.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["hero_id", "name"])
        writer.writeheader()
        writer.writerows(
            {"hero_id": f"{prefix}{i}", "name": f"{prefix}{i}"}
            for prefix in ("a", "b")
            for i in range(1, 6)
        )
    assignments = []
    counts = {}
    for split in ("train", "validation", "test"):
        rows = by_split.get(split, [])
        with (csv_dir / f"{split}.csv").open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(valid_row()))
            writer.writeheader()
            writer.writerows(rows)
        assigned = {item["series_id"] for item in assignments}
        assignments += [
            {"series_id": series_id, "split": split}
            for series_id in {row["series_id"] for row in rows} - assigned
        ]
        counts[split] = {
            "series": len({row["series_id"] for row in rows}),
            "games": len(rows),
            "labels": {
                "false": sum(row["team_a_win"] == "false" for row in rows),
                "true": sum(row["team_a_win"] == "true" for row in rows),
            },
        }
    (tmp_path / "split_manifest.json").write_text(
        json.dumps({"assignments": assignments, "split_counts": counts})
    )
    return tmp_path


def test_false_string_is_false_boolean():
    assert parse_game(valid_row()).team_a_win is False


def test_hero_order_does_not_change_the_team():
    row = valid_row()
    reversed_row = row.copy()
    reversed_row["team_a_heroes"] = json.dumps(["a5", "a4", "a3", "a2", "a1"])
    assert parse_game(row).team_a_heroes == parse_game(reversed_row).team_a_heroes


@pytest.mark.parametrize(
    "value",
    [
        "not json",
        '{"hero": "a1"}',
        '["a1", "a2", "a3", "a4"]',
        '["a1", "a2", "a3", "a4", "a5", "a6"]',
        '["a1", "a1", "a3", "a4", "a5"]',
        '["a1", "a2", "a3", "a4", 5]',
        '[" a1", "a2", "a3", "a4", "a5"]',
    ],
)
def test_invalid_hero_lists(value):
    with pytest.raises(InvalidField):
        parse_heroes(value)


def test_same_hero_on_both_teams_is_rejected():
    row = valid_row()
    row["team_b_heroes"] = json.dumps(["a1", "b2", "b3", "b4", "b5"])
    with pytest.raises(InvalidField, match="both teams"):
        parse_game(row)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("team_a_side", "green"),
        ("patch_id", ""),
        ("team_a_win", "yes"),
        ("team_a_win", "True"),
        ("game_id", ""),
    ],
)
def test_invalid_fields(field, value):
    row = valid_row()
    row[field] = value
    with pytest.raises(InvalidField) as exc:
        parse_game(row)
    assert exc.value.field == field


def test_audit_detects_duplicate_game_and_cross_split_series(tmp_path):
    train = valid_row()
    validation = valid_row(series_id="series-1")
    validation["split"] = "validation"
    dataset = make_dataset(tmp_path, {"train": [train], "validation": [validation]})
    _, issues = audit_dataset(dataset)
    assert {"game_id", "series_id"} <= {issue.field for issue in issues}


def test_audit_reports_invalid_rows_without_dropping_silently(tmp_path):
    broken = valid_row()
    broken["team_a_win"] = "unknown"
    dataset = make_dataset(tmp_path, {"train": [broken]})
    games, issues = audit_dataset(dataset)
    assert games["train"] == []
    assert {"team_a_win", "split_counts"} <= {issue.field for issue in issues}


def test_audit_reports_unknown_catalog_id(tmp_path):
    row = valid_row()
    row["team_a_heroes"] = json.dumps(["a1", "a2", "a3", "a4", "new"])
    dataset = make_dataset(tmp_path, {"train": [row]})
    _, issues = audit_dataset(dataset)
    assert any(issue.field == "heroes" and "new" in issue.message for issue in issues)


def test_audit_detects_manifest_count_mismatch(tmp_path):
    dataset = make_dataset(tmp_path, {"train": [valid_row()]})
    path = dataset / "split_manifest.json"
    manifest = json.loads(path.read_text())
    manifest["split_counts"]["train"]["games"] = 2
    path.write_text(json.dumps(manifest))
    _, issues = audit_dataset(dataset)
    assert {"row_count", "split_counts"} <= {issue.field for issue in issues}


def test_audit_detects_missing_manifest_series(tmp_path):
    dataset = make_dataset(tmp_path, {"train": [valid_row()]})
    path = dataset / "split_manifest.json"
    manifest = json.loads(path.read_text())
    manifest["assignments"].append({"series_id": "series-missing", "split": "train"})
    path.write_text(json.dumps(manifest))
    _, issues = audit_dataset(dataset)
    assert any("missing manifest series" in issue.message for issue in issues)


def test_load_csv_rejects_missing_required_columns(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("game_id,team_a_win\nx,true\n")
    with pytest.raises(ValueError, match="invalid headers"):
        load_csv(path)


def test_real_snapshot_passes_audit():
    games, issues = audit_dataset(DEFAULT_DATASET)
    assert not issues
    assert {split: len(rows) for split, rows in games.items()} == {
        "train": 231,
        "validation": 28,
        "test": 40,
    }
