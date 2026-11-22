import time

import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder


class AprioriMiner:
    def __init__(self, min_support=0.03, min_confidence=0.5, min_lift=1.0, max_heroes=5):
        self.min_support = min_support
        self.min_confidence = min_confidence
        self.min_lift = min_lift
        self.max_heroes = max_heroes
        self.execution_time = 0.0

    @staticmethod
    def encode_transactions(transactions):
        encoder = TransactionEncoder()
        encoded = encoder.fit(transactions).transform(transactions)
        return pd.DataFrame(encoded, columns=encoder.columns_)

    def run_mining(self, transactions):
        started = time.perf_counter()
        encoded = self.encode_transactions(transactions)
        itemsets = apriori(encoded, min_support=self.min_support, use_colnames=True, max_len=self.max_heroes + 1)
        itemsets = itemsets[itemsets["itemsets"].apply(
            lambda values: sum(str(value).startswith("HERO::") for value in values) <= self.max_heroes
            and sum(str(value).startswith("RESULT::") for value in values) <= 1
        )].copy()
        rules = pd.DataFrame()
        if not itemsets.empty:
            rules = association_rules(itemsets, metric="confidence", min_threshold=self.min_confidence)
            if self.min_lift > 0 and not rules.empty:
                rules = rules[rules["lift"] >= self.min_lift].copy()
        self.execution_time = time.perf_counter() - started
        return itemsets, rules

    @staticmethod
    def filter_result_rules(rules, result):
        if rules.empty:
            return pd.DataFrame(columns=rules.columns)
        target = f"RESULT::{result}"
        return rules[
            rules["antecedents"].apply(lambda values: bool(values) and all(str(x).startswith("HERO::") for x in values))
            & rules["antecedents"].apply(lambda values: 2 <= len(values) <= 5)
            & rules["consequents"].apply(lambda values: set(values) == {target})
        ].copy()

    def filter_win_rules(self, rules):
        return self.filter_result_rules(rules, "WIN")
