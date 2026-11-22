import json
import os

import pandas as pd

from liqily.mining.config import Config


class DataPreprocessor:
    """Read the training association dataset and create one transaction per team."""

    def __init__(self, raw_data_path=None, processed_data_path=None):
        self.raw_data_path = raw_data_path or Config.RAW_DATA_PATH
        self.processed_data_path = processed_data_path or Config.PROCESSED_DATA_PATH

    def load_raw_data(self):
        if not os.path.isfile(self.raw_data_path):
            raise FileNotFoundError(f"Không tìm thấy dataset: {self.raw_data_path}")
        df = pd.read_csv(self.raw_data_path)
        required = {"game_id", "team_id", "hero_ids", "is_winner"}
        missing = required.difference(df.columns)
        if missing:
            raise ValueError(f"Dataset thiếu cột bắt buộc: {', '.join(sorted(missing))}")
        return df

    @staticmethod
    def _parse_winner(value, row_number):
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and value in (0, 1):
            return bool(value)
        normalized = str(value).strip().lower()
        if normalized in {"true", "1", "win", "winner"}:
            return True
        if normalized in {"false", "0", "lose", "loss"}:
            return False
        raise ValueError(f"is_winner không hợp lệ ở dòng {row_number}: {value!r}")

    def process_transactions(self):
        df = self.load_raw_data()
        transactions, processed_rows = [], []
        for idx, row in df.iterrows():
            row_number = idx + 2  # header is the first CSV line
            raw_heroes = row["hero_ids"]
            try:
                hero_ids = json.loads(raw_heroes) if isinstance(raw_heroes, str) else raw_heroes
            except (TypeError, json.JSONDecodeError) as exc:
                raise ValueError(f"hero_ids không phải JSON hợp lệ ở dòng {row_number}") from exc
            if not isinstance(hero_ids, list) or any(not isinstance(hero, str) or not hero.strip() for hero in hero_ids):
                raise ValueError(f"hero_ids phải là danh sách UUID dạng chuỗi ở dòng {row_number}")
            if len(hero_ids) != 5 or len(set(hero.strip() for hero in hero_ids)) != 5:
                raise ValueError(f"Each team row must contain exactly five distinct heroes (row {row_number}).")
            # Keep the source UUIDs unchanged for both mining algorithms.
            hero_items = [f"HERO::{hero.strip()}" for hero in hero_ids]
            is_win = self._parse_winner(row["is_winner"], row_number)
            result_tag = "RESULT::WIN" if is_win else "RESULT::LOSE"
            transaction = hero_items + [result_tag]
            transactions.append(transaction)
            processed_rows.append({
                "game_id": row.get("game_id", idx),
                "team_id": row.get("team_id", ""),
                "is_winner": is_win,
                "hero_count": len(hero_ids),
                "items_str": ",".join(transaction),
            })

        team_rows = pd.DataFrame(processed_rows)
        if team_rows["game_id"].isna().any() or team_rows["team_id"].isna().any():
            raise ValueError("game_id and team_id must not be empty.")
        for game_id, game_rows in team_rows.groupby("game_id", sort=False):
            if game_rows["team_id"].nunique() != 2 or len(game_rows) != 2:
                raise ValueError(f"Game {game_id!r} must have exactly one transaction for each of its two teams.")
            if int(game_rows["is_winner"].sum()) != 1:
                raise ValueError(f"Game {game_id!r} must have exactly one winning team.")
        processed_df = pd.DataFrame(processed_rows)
        output_dir = os.path.dirname(self.processed_data_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        processed_df.to_csv(self.processed_data_path, index=False, encoding="utf-8")
        return transactions, processed_df
