import json
import math
import os
from itertools import combinations

import pandas as pd

from liqily.mining.config import Config
from liqily.mining.hero_mapping_service import HeroMappingService
from liqily.mining.preprocessing import DataPreprocessor
from liqily.mining.apriori_miner import AprioriMiner
from liqily.mining.comparison import AlgorithmComparer
from liqily.mining.fpgrowth_miner import FPGrowthMiner


class MiningService:
    DEFAULTS = {
        "min_support": Config.MIN_SUPPORT,
        "min_confidence": Config.MIN_CONFIDENCE,
        "min_lift": Config.MIN_LIFT,
        "max_heroes": 5,
    }

    def __init__(self):
        self.preprocessor = DataPreprocessor()
        self.hero_mapper = HeroMappingService()
        self._results = {}
        self._comparisons = {}

    @staticmethod
    def _key(params):
        return (
            tuple(float(params[key]) for key in ("min_support", "min_confidence", "min_lift"))
            + (int(params["max_heroes"]),)
        )

    @staticmethod
    def _validate_params(params):
        normalized = {}
        for key in ("min_support", "min_confidence", "min_lift"):
            try:
                value = float(params.get(key, MiningService.DEFAULTS[key]))
            except (TypeError, ValueError):
                raise ValueError(f"Tham số {key} phải là số.")
            if not math.isfinite(value):
                raise ValueError(f"Tham số {key} phải là số hữu hạn.")
            normalized[key] = value
        try:
            normalized["max_heroes"] = int(params.get("max_heroes", MiningService.DEFAULTS["max_heroes"]))
        except (TypeError, ValueError):
            raise ValueError("Maximum hero count must be a whole number from 2 to 5.")
        if normalized["max_heroes"] < 2 or normalized["max_heroes"] > 5:
            raise ValueError("Maximum hero count must be between 2 and 5.")
        if not 0 <= normalized["min_support"] <= 1:
            raise ValueError("Minimum Support phải nằm trong khoảng 0 đến 1.")
        if not 0 <= normalized["min_confidence"] <= 1:
            raise ValueError("Minimum Confidence phải nằm trong khoảng 0 đến 1.")
        if normalized["min_lift"] < 0:
            raise ValueError("Minimum Lift phải lớn hơn hoặc bằng 0.")
        # Zero support can enumerate an impractically large powerset through
        # the public API; the training split has 462 team transactions.
        if normalized["min_support"] < 0.01:
            raise ValueError("Minimum Support phải ít nhất là 0.01.")
        return normalized

    def _format_itemset(self, values):
        ordered = sorted(str(value) for value in values)
        return {
            "items": ordered,
            "display_items": self.hero_mapper.display_items(ordered),
            "label": self.hero_mapper.format_items(ordered),
        }

    def _serialize_itemsets(self, itemsets, transaction_count):
        rows = []
        for _, row in itemsets.iterrows():
            formatted = self._format_itemset(row["itemsets"])
            support = float(row["support"])
            rows.append({
                **formatted,
                "size": len(formatted["items"]),
                "support": support,
                "count": int(round(support * transaction_count)),
            })
        return sorted(rows, key=lambda row: (row["size"], -row["support"], row["label"]))

    def _serialize_rules(self, rules):
        rows = []
        for _, row in rules.iterrows():
            antecedents = self._format_itemset(row["antecedents"])
            consequents = self._format_itemset(row["consequents"])
            result = None
            if set(consequents["items"]) == {"RESULT::WIN"}:
                result = "WIN"
            elif set(consequents["items"]) == {"RESULT::LOSE"}:
                result = "LOSE"
            rows.append({
                "antecedents": antecedents["items"],
                "antecedent_names": antecedents["display_items"],
                "antecedent_label": antecedents["label"],
                "consequents": consequents["items"],
                "consequent_names": consequents["display_items"],
                "consequent_label": consequents["label"],
                "result": result,
                "support": float(row["support"]),
                "confidence": float(row["confidence"]),
                "lift": float(row["lift"]),
            })
        return sorted(rows, key=lambda row: (-row["confidence"], -row["lift"], -row["support"]))

    def _build_result(self, algorithm, params, transactions, miner, itemsets, rules):
        win_rules = miner.filter_result_rules(rules, "WIN")
        lose_rules = miner.filter_result_rules(rules, "LOSE")
        return {
            "algorithm": algorithm,
            "parameters": params,
            "total_transactions": len(transactions),
            "execution_time_sec": round(miner.execution_time, 6),
            "frequent_itemsets_count": len(itemsets),
            "total_rules_count": len(rules),
            "win_rules_count": len(win_rules),
            "lose_rules_count": len(lose_rules),
            "itemsets": self._serialize_itemsets(itemsets, len(transactions)),
            "rules": self._serialize_rules(rules),
            "win_rules": self._serialize_rules(win_rules),
            "lose_rules": self._serialize_rules(lose_rules),
        }

    def _run_one(self, algorithm, params, transactions=None):
        params = self._validate_params(params)
        transactions = transactions if transactions is not None else self.preprocessor.process_transactions()[0]
        miner_cls = AprioriMiner if algorithm == "apriori" else FPGrowthMiner
        miner = miner_cls(**params)
        itemsets, rules = miner.run_mining(transactions)
        result = self._build_result(algorithm, params, transactions, miner, itemsets, rules)
        self._results[(algorithm, self._key(params))] = result
        return result

    def get_dashboard_stats(self):
        transactions, processed = self.preprocessor.process_transactions()
        wins = int(processed["is_winner"].sum()) if not processed.empty else 0
        heroes = {item[6:] for tx in transactions for item in tx if item.startswith("HERO::")}
        ids = self.hero_mapper.mapping()
        return {
            "total_games": int(pd.read_csv(Config.RAW_DATA_PATH)["game_id"].nunique()),
            "total_teams": len(transactions),
            "unique_heroes": len(heroes),
            "total_transactions": len(transactions),
            "win_count": wins,
            "lose_count": len(transactions) - wins,
            "unmapped_hero_ids": len(heroes.difference(ids)),
        }

    def get_preprocessing_data(self, page=1, per_page=25):
        transactions, processed = self.preprocessor.process_transactions()
        raw = self.preprocessor.load_raw_data()
        all_hero_ids = {item[6:] for tx in transactions for item in tx if item.startswith("HERO::")}
        mapping = self.hero_mapper.mapping()
        rows = []
        for idx, tx in enumerate(transactions):
            heroes = [item for item in tx if item.startswith("HERO::")]
            result = next(item.split("::", 1)[1] for item in tx if item.startswith("RESULT::"))
            rows.append({
                "index": idx + 1,
                "game_id": str(processed.iloc[idx]["game_id"]),
                "team_id": str(processed.iloc[idx]["team_id"]),
                "hero_ids": [item[6:] for item in heroes],
                "heroes": [self.hero_mapper.display_item(item) for item in heroes],
                "hero_count": len(heroes),
                "result": result,
                "items": tx,
            })
        total = len(rows)
        page = max(1, int(page))
        per_page = min(100, max(1, int(per_page)))
        start = (page - 1) * per_page
        return {
            "stats": {
                "total_transactions": total,
                "unique_heroes": len(all_hero_ids),
                "win_count": sum(row["result"] == "WIN" for row in rows),
                "lose_count": sum(row["result"] == "LOSE" for row in rows),
                "complete_five_heroes": sum(row["hero_count"] == 5 for row in rows),
                "unmapped_hero_ids": len(all_hero_ids.difference(mapping)),
                "source_rows": len(raw),
            },
            "steps": [
                "Đọc association_train.csv (mỗi dòng là một đội).",
                "Parse hero_ids từ JSON và giữ nguyên UUID gốc.",
                "Thêm tiền tố HERO:: cho từng tướng.",
                "Chuyển is_winner thành RESULT::WIN hoặc RESULT::LOSE.",
                "Tạo đúng một transaction cho mỗi dòng/đội; tên tướng chỉ dùng khi hiển thị.",
            ],
            "page": page,
            "per_page": per_page,
            "total_pages": max(1, (total + per_page - 1) // per_page),
            "rows": rows[start:start + per_page],
        }

    def run_algorithm(self, algorithm, params):
        if algorithm not in {"apriori", "fpgrowth"}:
            raise ValueError("Thuật toán không hợp lệ.")
        params = self._validate_params(params)
        return self._run_one(algorithm, params)

    def run_comparison(self, params):
        params = self._validate_params(params)
        key = self._key(params)
        transactions = self.preprocessor.process_transactions()[0]
        comparer = AlgorithmComparer(**params)
        comparison, _, runs = comparer.compare(transactions, include_details=True)
        composition_sets = {}
        for algorithm, run in runs.items():
            plain, wins = set(), set()
            for itemset in run["itemsets"]["itemsets"]:
                values = set(itemset)
                heroes = {value for value in values if str(value).startswith("HERO::")}
                result_tags = {value for value in values if str(value).startswith("RESULT::")}
                if 2 <= len(heroes) <= params["max_heroes"]:
                    if not result_tags:
                        plain.add(tuple(sorted(heroes)))
                    elif result_tags == {"RESULT::WIN"}:
                        wins.add(tuple(sorted(heroes)))
            composition_sets[algorithm] = plain
            comparison[algorithm]["team_compositions_count"] = len(plain)
            comparison[algorithm]["winning_team_compositions_count"] = len(wins)
        common = composition_sets["apriori"] & composition_sets["fpgrowth"]
        only_apriori = composition_sets["apriori"] - composition_sets["fpgrowth"]
        only_fpgrowth = composition_sets["fpgrowth"] - composition_sets["apriori"]
        def describe_combinations(values):
            return sorted(({
                "hero_ids": list(combo),
                "label": self.hero_mapper.format_items([f"HERO::{hero}" for hero in combo]),
            } for combo in values), key=lambda row: row["label"])
        comparison["composition_overlap"] = {
            "common": describe_combinations(common),
            "apriori_only": describe_combinations(only_apriori),
            "fpgrowth_only": describe_combinations(only_fpgrowth),
        }
        for algorithm, run in runs.items():
            result = self._build_result(
                algorithm, params, transactions, run["miner"], run["itemsets"], run["rules"]
            )
            self._results[(algorithm, key)] = result
        comparison = {
            "parameters": comparison["parameters"],
            "apriori": comparison["apriori"],
            "fpgrowth": comparison["fpgrowth"],
            "composition_overlap": comparison["composition_overlap"],
        }
        self._comparisons[key] = comparison
        return comparison

    def get_team_compositions(self, size=None, sort="win_rate", min_matches=5, selected_heroes=None):
        """Summarize observed hero combinations by team-side match transactions."""
        transactions, processed = self.preprocessor.process_transactions()
        mapping = self.hero_mapper.mapping()
        catalog_ids = sorted({item[6:] for tx in transactions for item in tx if item.startswith("HERO::")})
        catalog = [{"id": hero_id, "name": mapping.get(hero_id, f"Unknown hero ({hero_id})")} for hero_id in catalog_ids]
        try:
            min_matches = max(1, int(min_matches))
        except (TypeError, ValueError) as exc:
            raise ValueError("Minimum matches must be a whole number greater than zero.") from exc
        try:
            size = int(size) if size not in (None, "", "all") else None
        except (TypeError, ValueError) as exc:
            raise ValueError("Team size must be between 2 and 5.") from exc
        if size is not None and size not in range(2, 6):
            raise ValueError("Team size must be between 2 and 5.")
        if sort not in {"win_rate", "matches"}:
            raise ValueError("Sort must be win_rate or matches.")

        selected = list(dict.fromkeys(str(hero) for hero in (selected_heroes or []) if str(hero)))
        if len(selected) != len(selected_heroes or []) or len(selected) > 5 or len(selected) == 1:
            raise ValueError("Select between two and five distinct heroes.")
        valid_ids = set(catalog_ids)
        if any(hero not in valid_ids for hero in selected):
            raise ValueError("The selected hero is not present in the dataset.")

        counts = {}
        outcomes = {}
        for tx, (_, row) in zip(transactions, processed.iterrows()):
            hero_ids = sorted(item[6:] for item in tx if item.startswith("HERO::"))
            for combo_size in range(2, min(5, len(hero_ids)) + 1):
                for combo in combinations(hero_ids, combo_size):
                    counts[combo] = counts.get(combo, 0) + 1
                    if row["is_winner"]:
                        outcomes[combo] = outcomes.get(combo, 0) + 1

        total = len(transactions)
        overall_win_rate = float(processed["is_winner"].mean()) if total else 0
        rows = []
        for combo, matches in counts.items():
            if size is not None and len(combo) != size:
                continue
            if selected and tuple(sorted(selected)) != combo:
                continue
            if matches < min_matches:
                continue
            wins = outcomes.get(combo, 0)
            win_rate = wins / matches
            support = matches / total if total else 0
            rows.append({
                "hero_ids": list(combo),
                "heroes": [mapping.get(hero, f"Unknown hero ({hero})") for hero in combo],
                "label": " + ".join(mapping.get(hero, f"Unknown hero ({hero})") for hero in combo),
                "size": len(combo), "matches": matches, "wins": wins, "losses": matches - wins,
                "win_rate": win_rate, "support": support, "confidence": win_rate,
                "lift": (win_rate / overall_win_rate) if overall_win_rate else 0,
                "ranking_score": self._wilson_lower_bound(wins, matches),
                "rating": "insufficient" if matches < max(10, min_matches) else ("high" if win_rate >= overall_win_rate else "potential"),
            })
        if sort == "matches":
            rows.sort(key=lambda row: (-row["matches"], -row["win_rate"], row["label"]))
        else:
            rows.sort(key=lambda row: (-row["ranking_score"], -row["win_rate"], row["label"]))
        return {
            "total_transactions": total, "overall_win_rate": overall_win_rate,
            "catalog": catalog, "compositions": rows[:100],
            "selected": self._lookup_selected(selected, counts, outcomes, total, overall_win_rate, mapping, min_matches)
                if selected else None,
        }

    @staticmethod
    def _wilson_lower_bound(wins, matches, z=1.96):
        if matches <= 0:
            return 0.0
        rate = wins / matches
        z_squared = z * z
        denominator = 1 + z_squared / matches
        center = rate + z_squared / (2 * matches)
        margin = z * math.sqrt((rate * (1 - rate) + z_squared / (4 * matches)) / matches)
        return (center - margin) / denominator

    @staticmethod
    def _lookup_selected(selected, counts, outcomes, total, overall_win_rate, mapping, min_matches):
        combo = tuple(sorted(selected))
        matches = counts.get(combo, 0)
        wins = outcomes.get(combo, 0)
        if not matches:
            return {"found": False, "hero_ids": list(combo), "heroes": [mapping.get(h, h) for h in combo], "label": " + ".join(mapping.get(h, h) for h in combo)}
        win_rate = wins / matches
        return {
            "found": True, "hero_ids": list(combo), "heroes": [mapping.get(h, h) for h in combo],
            "label": " + ".join(mapping.get(h, h) for h in combo), "matches": matches, "wins": wins,
            "losses": matches - wins, "win_rate": win_rate, "support": matches / total if total else 0,
            "confidence": win_rate, "lift": win_rate / overall_win_rate if overall_win_rate else 0,
            "ranking_score": MiningService._wilson_lower_bound(wins, matches),
            "rating": "insufficient" if matches < max(10, min_matches) else ("high" if win_rate >= overall_win_rate else "potential"),
            "min_matches": min_matches,
        }

    def get_association_overview(self, params):
        self.run_comparison(params)
        key = self._key(self._validate_params(params))
        ap = self._results[("apriori", key)]
        fp = self._results[("fpgrowth", key)]
        # This page is specifically about hero combinations associated with a
        # match result. Keep generic rules (including one hero -> result) on
        # the algorithm detail pages, and show only 2-5 heroes -> WIN/LOSE here.
        apriori_result_rules = ap["win_rules"] + ap["lose_rules"]
        fpgrowth_result_rules = fp["win_rules"] + fp["lose_rules"]
        rules = [{**row, "algorithm": "Apriori"} for row in apriori_result_rules]
        rules += [{**row, "algorithm": "FP-Growth"} for row in fpgrowth_result_rules]
        return {
            "apriori_rules_count": len(apriori_result_rules),
            "fpgrowth_rules_count": len(fpgrowth_result_rules),
            "win_rules_count": sum(row["result"] == "WIN" for row in rules),
            "lose_rules_count": sum(row["result"] == "LOSE" for row in rules),
            "highest_confidence": max(rules, key=lambda x: x["confidence"], default=None),
            "highest_lift": max(rules, key=lambda x: x["lift"], default=None),
            "rules": sorted(rules, key=lambda row: (-row["confidence"], -row["lift"])),
        }

    def get_data_management(self):
        datasets = []
        paths = [Config.RAW_DATA_PATH, Config.PROCESSED_DATA_PATH, self.hero_mapper.heroes_path]
        for path in paths:
            if not os.path.isfile(path):
                datasets.append({"name": os.path.basename(path), "path": os.path.relpath(path, Config.BASE_DIR), "exists": False})
                continue
            df = pd.read_csv(path)
            valid = bool(not df.empty and not df.isna().any().any())
            validation_message = "Không có ô thiếu giá trị." if valid else "File rỗng hoặc còn giá trị thiếu."
            if path == Config.RAW_DATA_PATH:
                required = {"game_id", "team_id", "hero_ids", "is_winner"}
                valid = valid and required.issubset(df.columns)
                if valid:
                    try:
                        for idx, row in df.iterrows():
                            heroes = row["hero_ids"]
                            heroes = json.loads(heroes) if isinstance(heroes, str) else heroes
                            if not isinstance(heroes, list) or len(heroes) != 5:
                                raise ValueError(f"Dòng {idx + 2} không có đúng 5 tướng.")
                            self.preprocessor._parse_winner(row["is_winner"], idx + 2)
                        validation_message = "Schema hợp lệ; hero_ids là JSON gồm 5 tướng và is_winner có giá trị hợp lệ."
                    except (ValueError, TypeError) as exc:
                        valid = False
                        validation_message = str(exc)
                else:
                    validation_message = "Thiếu một hoặc nhiều cột bắt buộc cho mining."
            elif path == Config.PROCESSED_DATA_PATH:
                required = {"game_id", "team_id", "is_winner", "hero_count", "items_str"}
                valid = valid and required.issubset(df.columns)
                if valid:
                    valid = bool((df["hero_count"] == 5).all())
                validation_message = "Schema hợp lệ, tất cả transaction có đúng 5 tướng." if valid else "Schema không hợp lệ hoặc có transaction thiếu/khác 5 tướng."
            elif path == self.hero_mapper.heroes_path:
                valid = valid and {"hero_id", "name"}.issubset(df.columns)
                validation_message = "Có cột hero_id và name, không thiếu giá trị." if valid else "Thiếu cột ánh xạ hoặc có giá trị thiếu."
            datasets.append({
                "name": os.path.basename(path),
                "path": os.path.relpath(path, Config.BASE_DIR),
                "exists": True,
                "rows": int(len(df)),
                "columns_count": int(len(df.columns)),
                "columns": [{"name": str(col), "dtype": str(df[col].dtype), "missing": int(df[col].isna().sum())} for col in df.columns],
                "missing_total": int(df.isna().sum().sum()),
                "valid": valid,
                "validation_message": validation_message,
            })
        return {"datasets": datasets}

    def get_cached_result(self, algorithm, params):
        params = self._validate_params(params)
        return self._results.get((algorithm, self._key(params)))

    def get_cached_comparison(self, params):
        params = self._validate_params(params)
        return self._comparisons.get(self._key(params))

    def export_frame(self, report_type, params):
        params = self._validate_params(params)
        if report_type == "comparison":
            comparison = self.get_cached_comparison(params)
            if comparison is None:
                raise LookupError("Chưa chạy so sánh với bộ tham số này.")
            return pd.DataFrame([
                {"algorithm": name, **values}
                for name, values in (("Apriori", comparison["apriori"]), ("FP-Growth", comparison["fpgrowth"]))
            ])
        algorithm, kind = report_type.split("_", 1)
        result = self.get_cached_result(algorithm, params)
        if result is None:
            raise LookupError("Chưa chạy thuật toán với bộ tham số này.")
        if kind == "itemsets":
            rows = [{
                "items": row["label"], "item_uuids": " | ".join(row["items"]),
                "item_count": row["size"], "support": row["support"], "transaction_count": row["count"],
            } for row in result["itemsets"]]
        elif kind == "rules":
            rows = [{
                "antecedents": row["antecedent_label"], "antecedent_uuids": " | ".join(row["antecedents"]),
                "consequents": row["consequent_label"], "consequent_uuids": " | ".join(row["consequents"]),
                "result": row["result"], "support": row["support"], "confidence": row["confidence"], "lift": row["lift"],
            } for row in result["rules"]]
        else:
            raise ValueError("Loại báo cáo không hợp lệ.")
        return pd.DataFrame(rows)
