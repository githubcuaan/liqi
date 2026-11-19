"""Load and audit the post-draft prediction dataset without modifying it."""

import argparse
import csv
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

SPLITS = ("train", "validation", "test")
REQUIRED_COLUMNS = {
    "game_id",
    "series_id",
    "team_a_heroes",
    "team_b_heroes",
    "team_a_side",
    "patch_id",
    "team_a_win",
}
DEFAULT_DATASET = Path(__file__).resolve().parents[3] / "dataset" / "035ce761e53a47db"


@dataclass(frozen=True)
class Game:
    game_id: str
    series_id: str
    team_a_heroes: frozenset[str]
    team_b_heroes: frozenset[str]
    team_a_side: str
    patch_id: str
    team_a_win: bool


@dataclass(frozen=True)
class Issue:
    split: str
    game_id: str
    field: str
    message: str


class InvalidField(ValueError):
    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field


def load_csv(path: Path, required: set[str] = REQUIRED_COLUMNS) -> list[dict]:
    """Read rows as strings; fail on a missing/duplicate header or extra CSV cells."""
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        headers = reader.fieldnames or []
        missing = required - set(headers)

        if missing or len(headers) != len(set(headers)):
            raise ValueError(f"{path}: invalid headers; missing={sorted(missing)}")
        rows = list(reader)

        if any(None in row for row in rows):
            raise ValueError(f"{path}: CSV row has more cells than headers")
        return rows


def parse_heroes(value: str, field: str = "heroes") -> frozenset[str]:
    if not isinstance(value, str):
        raise InvalidField(field, "missing JSON array")
    try:
        heroes = json.loads(value)
    except json.JSONDecodeError as exc:
        raise InvalidField(field, f"invalid JSON: {exc.msg}") from exc
    if not isinstance(heroes, list) or len(heroes) != 5:
        raise InvalidField(field, "expected a JSON array of exactly five heroes")
    if any(
        not isinstance(hero, str) or not hero or hero != hero.strip() for hero in heroes
    ):
        raise InvalidField(
            field, "hero IDs must be nonempty strings without surrounding whitespace"
        )
    if len(set(heroes)) != 5:
        raise InvalidField(field, "duplicate hero within a team")
    return frozenset(heroes)


def parse_game(row: dict) -> Game:
    """Validate one row; keep team compositions unordered and labels boolean."""
    for field in ("game_id", "series_id"):
        if not isinstance(row.get(field), str) or not row[field].strip():
            raise InvalidField(field, "required nonempty ID")
    team_a = parse_heroes(row.get("team_a_heroes"), "team_a_heroes")  # type: ignore
    team_b = parse_heroes(row.get("team_b_heroes"), "team_b_heroes")  # type: ignore
    if team_a & team_b:
        raise InvalidField("team_b_heroes", "hero picked by both teams")

    side = row.get("team_a_side")
    if side not in ("blue", "red"):
        raise InvalidField("team_a_side", "expected blue or red")
    patch_id = row.get("patch_id")
    if not isinstance(patch_id, str) or not patch_id.strip():
        raise InvalidField("patch_id", "required nonempty patch ID")
    label = row.get("team_a_win")
    if label not in ("true", "false"):
        raise InvalidField("team_a_win", "expected literal true or false")

    return Game(
        game_id=row["game_id"].strip(),
        series_id=row["series_id"].strip(),
        team_a_heroes=team_a,
        team_b_heroes=team_b,
        team_a_side=side,
        patch_id=patch_id,
        team_a_win=label == "true",
    )


def load_hero_names(path: Path) -> dict[str, str]:
    """Catalog for validation and display, never a predictive feature."""
    rows = load_csv(path, {"hero_id", "name"})
    names: dict[str, str] = {}
    for row in rows:
        hero_id, name = row["hero_id"], row["name"]
        if not hero_id or not name or hero_id in names:
            raise ValueError(f"{path}: empty or duplicate hero ID/name: {hero_id!r}")
        names[hero_id] = name
    return names


def audit_dataset(dataset_dir: Path) -> tuple[dict[str, list[Game]], list[Issue]]:
    """Return parsed games and every audit issue; do not drop or repair bad data."""

    # prepared (manifest, hero_names, assignments)
    manifest = json.loads(
        (dataset_dir / "split_manifest.json").read_text(encoding="utf-8")
    )
    hero_names = load_hero_names(dataset_dir / "csv" / "heroes.csv")
    assignments = {item["series_id"]: item["split"] for item in manifest["assignments"]}
    if len(assignments) != len(manifest["assignments"]):
        raise ValueError("split_manifest.json: duplicate series assignment")

    # audit each split
    games_by_split: dict[str, list[Game]] = {}
    issues: list[Issue] = []
    seen_games: dict[str, str] = {}
    seen_series: dict[str, str] = {}

    for split in SPLITS:
        rows = load_csv(dataset_dir / "csv" / f"{split}.csv")
        games: list[Game] = []
        for row_number, row in enumerate(rows, start=2):
            game_id = (row.get("game_id") or "").strip()
            series_id = (row.get("series_id") or "").strip()
            location = game_id or f"row {row_number}"

            # Check identifiers even when another field on this row is invalid.
            if game_id:
                if game_id in seen_games:
                    issues.append(
                        Issue(
                            split,
                            location,
                            "game_id",
                            f"duplicate; first in {seen_games[game_id]}",
                        )
                    )
                else:
                    seen_games[game_id] = split
            if series_id:
                if series_id in seen_series and seen_series[series_id] != split:
                    issues.append(
                        Issue(
                            split,
                            location,
                            "series_id",
                            f"series also in {seen_series[series_id]}",
                        )
                    )
                else:
                    seen_series[series_id] = split
                if assignments.get(series_id) != split:
                    issues.append(
                        Issue(
                            split,
                            location,
                            "series_id",
                            f"manifest split={assignments.get(series_id)!r}",
                        )
                    )
            if row.get("split") is not None and row["split"] != split:
                issues.append(
                    Issue(split, location, "split", f"CSV split={row['split']!r}")
                )

            try:
                game = parse_game(row)
            except InvalidField as exc:
                issues.append(Issue(split, location, exc.field, str(exc)))
                continue

            for hero_id in game.team_a_heroes | game.team_b_heroes:
                if hero_id not in hero_names:
                    issues.append(
                        Issue(
                            split, location, "heroes", f"unknown catalog ID: {hero_id}"
                        )
                    )
            games.append(game)

        games_by_split[split] = games
        expected = manifest["split_counts"][split]
        labels = Counter(game.team_a_win for game in games)
        actual = {
            "series": len({game.series_id for game in games}),
            "games": len(games),
            "labels": {"false": labels[False], "true": labels[True]},
        }
        if len(rows) != expected["games"]:
            issues.append(
                Issue(
                    split,
                    "-",
                    "row_count",
                    f"CSV rows={len(rows)}; manifest={expected['games']}",
                )
            )
        if actual != expected:
            issues.append(
                Issue(
                    split,
                    "-",
                    "split_counts",
                    f"valid rows={actual}; manifest={expected}",
                )
            )

    for series_id in assignments.keys() - seen_series.keys():
        issues.append(
            Issue(
                assignments[series_id],
                "-",
                "series_id",
                f"missing manifest series: {series_id}",
            )
        )
    return games_by_split, issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the Liqily prediction dataset")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)

    args = parser.parse_args()

    try:
        games_by_split, issues = audit_dataset(args.dataset)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Cannot audit dataset: {exc}", file=sys.stderr)
        return 2
    for split, games in games_by_split.items():
        labels = Counter(game.team_a_win for game in games)
        print(
            f"{split:10} games={len(games):3} "
            f"series={len({game.series_id for game in games}):2} "
            f"win={labels[True]:3} lose={labels[False]:3}"
        )
    for issue in issues:
        print(
            f"[ERROR] {issue.split} | {issue.game_id} | {issue.field}: {issue.message}"
        )
    print(f"Total issues: {len(issues)}")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
