"""Unified HTTP application over the three existing Python engines."""

import hashlib
import json
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from threading import BoundedSemaphore
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from liqily.draft.vendor.liqi_draft import DraftRecommender
from liqily.mining.config import Config
from liqily.mining.mining_service import MiningService
from liqily.prediction.data import DEFAULT_DATASET, load_hero_names
from liqily.prediction.serving import WinPredictor

ROOT = Path(__file__).resolve().parents[3]
_mining_slots = BoundedSemaphore(1)


def verify_snapshot() -> None:
    manifest = json.loads((DEFAULT_DATASET / "release-manifest.json").read_text(encoding="utf-8"))
    for name in (
        "csv/association_train.csv", "csv/heroes.csv", "csv/train.csv",
        "csv/validation.csv", "csv/test.csv",
    ):
        expected = manifest["files"][name]
        actual = hashlib.sha256((DEFAULT_DATASET / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Dataset checksum mismatch: {name}")


class MiningRequest(BaseModel):
    algorithm: Literal["apriori", "fpgrowth"] = "fpgrowth"
    min_support: float = Field(default=0.01, ge=0.01, le=1)
    min_confidence: float = Field(default=0.5, ge=0, le=1)
    min_lift: float = Field(default=1, ge=0, le=100)
    max_heroes: int = Field(default=5, ge=2, le=5)


class DraftRequest(BaseModel):
    action: Literal["pick", "ban"]
    own_picks: list[str] = Field(default_factory=list)
    enemy_picks: list[str] = Field(default_factory=list)
    banned: list[str] = Field(default_factory=list)
    k: int = Field(default=5, ge=1, le=20, strict=True)

    @model_validator(mode="after")
    def distinct_heroes(self):
        values = self.own_picks + self.enemy_picks + self.banned
        if len(values) != len(set(values)):
            raise ValueError("Một tướng không được xuất hiện ở nhiều vị trí.")
        return self


class PredictionRequest(BaseModel):
    team_a_heroes: list[str] = Field(min_length=5, max_length=5)
    team_b_heroes: list[str] = Field(min_length=5, max_length=5)
    team_a_side: Literal["blue", "red"]
    patch_id: str = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def distinct_heroes(self):
        values = self.team_a_heroes + self.team_b_heroes
        if len(values) != len(set(values)):
            raise ValueError("Hai đội phải có mười tướng khác nhau.")
        return self


@lru_cache(maxsize=1)
def services():
    verify_snapshot()
    heroes = load_hero_names(DEFAULT_DATASET / "csv" / "heroes.csv")
    draft = DraftRecommender()
    predictor = WinPredictor()
    mining = MiningService()
    return heroes, draft, predictor, mining


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Fail deployment before accepting requests when data/artifacts are missing.
    services()
    yield


app = FastAPI(title="Liqily API", version="1.0", lifespan=lifespan)


@app.get("/health")
@app.get("/api/v1/health")
def health():
    services()
    return {"status": "ok"}


@app.get("/api/v1/catalog/heroes")
def heroes():
    names, draft, predictor, _ = services()
    eligibility = {row["hero_id"]: row for row in draft.heroes()}
    known = set(predictor.encoder.hero_ids)
    return [
        {
            "hero_id": hero_id,
            "hero_name": name,
            "pick_candidate": eligibility.get(hero_id, {}).get("pick_candidate", False),
            "ban_candidate": eligibility.get(hero_id, {}).get("ban_candidate", False),
            "seen_in_prediction_train": hero_id in known,
        }
        for hero_id, name in sorted(names.items(), key=lambda pair: pair[1].casefold())
    ]


@app.get("/api/v1/catalog/patches")
def patches():
    _, _, predictor, _ = services()
    return list(predictor.encoder.patch_ids)


@app.get("/api/v1/overview")
def overview():
    _, draft, predictor, mining = services()
    return {
        **mining.get_dashboard_stats(),
        "dataset_version": predictor.metadata["dataset_version"],
        "draft_version": draft.version,
        "prediction_model": predictor.metadata["model_name"],
        "data_scope": "Đấu Trường Danh Vọng mùa xuân 2026 · tập train",
    }


def _mine(run):
    if not _mining_slots.acquire(blocking=False):
        raise HTTPException(status_code=429, detail="Đang có lượt khai phá khác chạy.")
    try:
        return run()
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        _mining_slots.release()


@app.post("/api/v1/mining/run")
def run_mining(request: MiningRequest):
    _, _, _, mining = services()
    params = request.model_dump(exclude={"algorithm"})
    result = _mine(lambda: mining.run_algorithm(request.algorithm, params))
    return {
        **{key: value for key, value in result.items() if key not in ("itemsets", "rules", "win_rules", "lose_rules")},
        "itemsets": result["itemsets"][:300],
        # The discovery screen is about observed hero combinations -> outcome,
        # not generic itemset implications; give these rules priority.
        "rules": (result["win_rules"] + result["lose_rules"])[:300],
        "truncated": len(result["itemsets"]) > 300
        or len(result["win_rules"]) + len(result["lose_rules"]) > 300,
    }


@app.post("/api/v1/mining/compare")
def compare(request: MiningRequest):
    _, _, _, mining = services()
    result = _mine(lambda: mining.run_comparison(request.model_dump(exclude={"algorithm"})))
    return {key: value for key, value in result.items() if key != "composition_overlap"} | {
        "common_compositions": len(result["composition_overlap"]["common"])
    }


@app.get("/api/v1/compositions")
def compositions(
    size: int | None = Query(default=None, ge=2, le=5),
    min_matches: int = Query(default=5, ge=1, le=462),
    sort: Literal["win_rate", "matches"] = "win_rate",
    hero_ids: list[str] = Query(default=[]),
):
    names, _, _, mining = services()
    if any(hero not in names for hero in hero_ids):
        raise HTTPException(status_code=422, detail="Tướng không có trong danh mục.")
    try:
        return mining.get_team_compositions(
            size=size, sort=sort, min_matches=min_matches, selected_heroes=hero_ids
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/draft/recommend")
def recommend(request: DraftRequest):
    _, draft, _, _ = services()
    try:
        return draft.recommend(request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/predictions/win")
def predict(request: PredictionRequest):
    names, _, predictor, _ = services()
    unknown = (set(request.team_a_heroes) | set(request.team_b_heroes)) - names.keys()
    if unknown:
        raise HTTPException(status_code=422, detail=f"ID tướng không có trong danh mục: {sorted(unknown)}")
    return predictor.predict(
        request.team_a_heroes, request.team_b_heroes,
        request.team_a_side, request.patch_id,
    )


@app.get("/api/v1/reports/{report_type}.csv")
def report(
    report_type: Literal[
        "comparison", "apriori_itemsets", "apriori_rules",
        "fpgrowth_itemsets", "fpgrowth_rules",
    ],
    min_support: float = Query(default=0.01, ge=0.01, le=1),
    min_confidence: float = Query(default=0.5, ge=0, le=1),
    min_lift: float = Query(default=1, ge=0, le=100),
    max_heroes: int = Query(default=5, ge=2, le=5),
):
    _, _, _, mining = services()
    try:
        frame = mining.export_frame(report_type, {
            "min_support": min_support, "min_confidence": min_confidence,
            "min_lift": min_lift, "max_heroes": max_heroes,
        })
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        "\ufeff" + frame.to_csv(index=False),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{report_type}.csv"'},
    )


# Vite builds the independent UI into web/dist; API remains usable without it.
DIST = ROOT / "web" / "dist"
if DIST.is_dir():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="web")
