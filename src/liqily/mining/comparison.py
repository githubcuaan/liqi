import pandas as pd

from liqily.mining.apriori_miner import AprioriMiner
from liqily.mining.fpgrowth_miner import FPGrowthMiner


class AlgorithmComparer:
    """Run both miners with the same dataset and thresholds."""

    def __init__(self, min_support=0.03, min_confidence=0.5, min_lift=1.0, max_heroes=5):
        self.min_support = min_support
        self.min_confidence = min_confidence
        self.min_lift = min_lift
        self.max_heroes = max_heroes

    def compare(self, transactions, include_details=False):
        params = {
            "min_support": self.min_support,
            "min_confidence": self.min_confidence,
            "min_lift": self.min_lift,
            "max_heroes": self.max_heroes,
        }
        runs = {}
        for name, miner_type in (("apriori", AprioriMiner), ("fpgrowth", FPGrowthMiner)):
            miner = miner_type(**params)
            itemsets, rules = miner.run_mining(transactions)
            win_rules = miner.filter_result_rules(rules, "WIN")
            lose_rules = miner.filter_result_rules(rules, "LOSE")
            runs[name] = {
                "miner": miner,
                "itemsets": itemsets,
                "rules": rules,
                "metrics": {
                    "algorithm": name,
                    "execution_time_sec": round(miner.execution_time, 6),
                    "frequent_itemsets_count": len(itemsets),
                    "total_rules_count": len(rules),
                    "win_rules_count": len(win_rules),
                    "lose_rules_count": len(lose_rules),
                    "total_transactions": len(transactions),
                    "parameters": params,
                },
            }

        result = {
            "parameters": {**params, "total_transactions": len(transactions)},
            "apriori": runs["apriori"]["metrics"],
            "fpgrowth": runs["fpgrowth"]["metrics"],
        }
        summary = pd.DataFrame([
            {
                "Algorithm": name,
                "Execution time (sec)": run["metrics"]["execution_time_sec"],
                "Frequent itemsets": run["metrics"]["frequent_itemsets_count"],
                "Association rules": run["metrics"]["total_rules_count"],
                "WIN rules": run["metrics"]["win_rules_count"],
                "LOSE rules": run["metrics"]["lose_rules_count"],
            }
            for name, run in (("Apriori", runs["apriori"]), ("FP-Growth", runs["fpgrowth"]))
        ])
        if include_details:
            return result, summary, runs
        return result, summary
