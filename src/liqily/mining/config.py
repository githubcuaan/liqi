"""Paths and thresholds for the imported association-mining code."""

from pathlib import Path

from liqily.prediction.data import DEFAULT_DATASET


class Config:
    BASE_DIR = Path(__file__).resolve().parents[3]
    RAW_DATA_DIR = DEFAULT_DATASET / "csv"
    PROCESSED_DATA_DIR = BASE_DIR / "dataset" / "processed"
    RAW_DATA_PATH = RAW_DATA_DIR / "association_train.csv"
    PROCESSED_DATA_PATH = PROCESSED_DATA_DIR / "processed_transactions.csv"
    MIN_SUPPORT = 0.03
    MIN_CONFIDENCE = 0.5
    MIN_LIFT = 1.0
