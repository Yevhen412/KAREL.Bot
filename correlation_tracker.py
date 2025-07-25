import pandas as pd
import numpy as np

class CorrelationTracker:
    def __init__(self, price_data: pd.DataFrame, window: int = 30):
        self.price_data = price_data
        self.window = window

    def _log_returns(self):
        return np.log(self.price_data / self.price_data.shift(1)).dropna()

    def calculate(self):
        returns = self._log_returns()
        rolling_corr = returns.rolling(window=self.window).corr()
        last_corr = rolling_corr.groupby(level=1).tail(1)
        return last_corr

    def get_top_pairs(self, threshold=0.85, top_n=3):
        latest_corr = self.calculate()
        corr_matrix = latest_corr.reset_index(level=0, drop=True)
        upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
        pairs = (
            upper.stack()
            .reset_index()
            .rename(columns={0: "correlation", "level_0": "pair1", "level_1": "pair2"})
        )
        top = pairs[pairs["correlation"] >= threshold]
        return top.sort_values("correlation", ascending=False).head(top_n)
