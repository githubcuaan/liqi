import os

import pandas as pd

from liqily.mining.config import Config


class HeroMappingService:
    """Map UUIDs to names for presentation only; mining keeps original UUIDs."""

    def __init__(self, heroes_path=None):
        self.heroes_path = heroes_path or os.path.join(Config.RAW_DATA_DIR, "heroes.csv")
        self._mapping = None

    def mapping(self):
        if self._mapping is None:
            if not os.path.isfile(self.heroes_path):
                self._mapping = {}
            else:
                heroes = pd.read_csv(self.heroes_path)
                if not {"hero_id", "name"}.issubset(heroes.columns):
                    raise ValueError("heroes.csv cần có các cột hero_id và name")
                self._mapping = {
                    str(row.hero_id): str(row.name)
                    for row in heroes[["hero_id", "name"]].dropna().itertuples(index=False)
                }
        return self._mapping

    def display_item(self, item):
        if str(item) == "RESULT::WIN":
            return "Kết quả: Thắng"
        if str(item) == "RESULT::LOSE":
            return "Kết quả: Thua"
        if not str(item).startswith("HERO::"):
            return str(item)
        hero_id = str(item)[6:]
        name = self.mapping().get(hero_id)
        return name if name else f"Không rõ tướng ({hero_id})"

    def display_items(self, items):
        return [self.display_item(item) for item in sorted(items)]

    def format_items(self, items):
        return " + ".join(self.display_items(items))
