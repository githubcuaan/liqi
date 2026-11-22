"""Encode post-draft games and fit simple train-only baselines."""

from dataclasses import dataclass
from typing import Protocol, Sequence

from liqily.prediction.data import Game


class FeatureInput(Protocol):
    """Fields observable before a game; never include the outcome label."""

    team_a_heroes: frozenset[str]
    team_b_heroes: frozenset[str]
    team_a_side: str
    patch_id: str


@dataclass(frozen=True)
class FeatureEncoder:
    hero_ids: tuple[str, ...]
    patch_ids: tuple[str, ...]

    @classmethod
    def fit(cls, train_games: list[Game]) -> "FeatureEncoder":
        """Build a fixed vocabulary using training games only."""
        if not train_games:
            raise ValueError("Training games must not be empty")

        hero_ids = {
            hero_id
            for game in train_games
            for hero_id in game.team_a_heroes | game.team_b_heroes
        }
        patch_ids = {game.patch_id for game in train_games}

        return cls(hero_ids=tuple(sorted(hero_ids)), patch_ids=tuple(sorted(patch_ids)))

    @property
    def feature_names(self) -> tuple[str, ...]:
        """Return feature names in the same order as transform_one()."""
        names: list[str] = []

        names.extend(f"team_a_hero={hero_id}" for hero_id in self.hero_ids)
        names.append("team_a_unknown_hero_count")

        names.extend(f"team_b_hero={hero_id}" for hero_id in self.hero_ids)
        names.append("team_b_unknown_hero_count")

        names.append("team_a_is_blue")
        names.extend(f"patch={patch_id}" for patch_id in self.patch_ids)
        names.append("patch_is_unknown")

        return tuple(names)

    def transform_one(self, game: FeatureInput) -> list[int]:
        """Encode a game without changing the training vocabulary."""
        known_heroes = set(self.hero_ids)
        known_patches = set(self.patch_ids)

        values: list[int] = []

        # Team A hero indicators and unknown count.
        values.extend(int(hero_id in game.team_a_heroes) for hero_id in self.hero_ids)
        values.append(len(game.team_a_heroes - known_heroes))

        # Team B hero indicators and unknown count.
        values.extend(int(hero_id in game.team_b_heroes) for hero_id in self.hero_ids)
        values.append(len(game.team_b_heroes - known_heroes))

        # Side and patch indicators.
        values.append(int(game.team_a_side == "blue"))
        values.extend(int(game.patch_id == patch_id) for patch_id in self.patch_ids)
        values.append(int(game.patch_id not in known_patches))

        return values

    def transform(self, games: Sequence[FeatureInput]) -> list[list[int]]:
        """Encode games with the same columns used for training."""
        return [self.transform_one(game) for game in games]

    def unknown_categories(self, game: FeatureInput) -> dict[str, object]:
        """Return unseen categories for later inference warnings."""
        known_heroes = set(self.hero_ids)

        return {
            "team_a_heroes": sorted(game.team_a_heroes - known_heroes),
            "team_b_heroes": sorted(game.team_b_heroes - known_heroes),
            "patch_id": (
                game.patch_id if game.patch_id not in self.patch_ids else None
            ),
        }


def labels(games: list[Game]) -> list[int]:
    """Keep targets separate from the feature matrix."""
    return [int(game.team_a_win) for game in games]


@dataclass(frozen=True)
class MajorityBaseline:
    probability: float

    @classmethod
    def fit(cls, train_games: list[Game]) -> "MajorityBaseline":
        """Estimate the win probability from training labels only."""
        if not train_games:
            raise ValueError("Training games must not be empty")
        probability = sum(game.team_a_win for game in train_games) / len(train_games)
        return cls(probability=probability)

    def predict_proba(self, games: Sequence[FeatureInput]) -> list[float]:
        """Return the same probability for every game."""
        return [self.probability] * len(games)


@dataclass(frozen=True)
class SideBaseline:
    prior: float
    blue_probability: float | None
    red_probability: float | None

    @classmethod
    def fit(cls, train_games: list[Game]) -> "SideBaseline":
        """Estimate win probabilities by side from training labels only."""
        prior = MajorityBaseline.fit(train_games).probability
        by_side = {
            side: [game.team_a_win for game in train_games if game.team_a_side == side]
            for side in ("blue", "red")
        }

        def rate(outcomes: list[bool]) -> float | None:
            return sum(outcomes) / len(outcomes) if outcomes else None

        return cls(
            prior=prior,
            blue_probability=rate(by_side["blue"]),
            red_probability=rate(by_side["red"]),
        )

    def predict_proba(self, games: Sequence[FeatureInput]) -> list[float]:
        """Use the overall prior if a side had no training examples."""
        probabilities: list[float] = []

        for game in games:
            side_probability = (
                self.blue_probability
                if game.team_a_side == "blue"
                else self.red_probability
            )
            probabilities.append(
                self.prior if side_probability is None else side_probability
            )

        return probabilities
