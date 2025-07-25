import pandas as pd

class Strategy:
    def __init__(self, price_data: pd.DataFrame, pairs: pd.DataFrame):
        self.price_data = price_data
        self.pairs = pairs
        self.results = []

    def run(self):
        for _, row in self.pairs.iterrows():
            leader = row['pair1']
            follower = row['pair2']
            self._simulate_pair(leader, follower)
        return pd.DataFrame(self.results)

    def _simulate_pair(self, leader: str, follower: str):
        df = self.price_data[[leader, follower]].copy()
        df['leader_ret'] = df[leader].pct_change()
        df['follower_ret'] = df[follower].pct_change()

        in_position = False
        entry_price = None
        entry_time = None

        for i in range(2, len(df)):
            lead_move = df.iloc[i]['leader_ret']
            foll_price = df.iloc[i][follower]

            if not in_position and lead_move > 0.003:
                in_position = True
                entry_price = foll_price
                entry_time = df.index[i]
                continue

            if in_position:
                price_change = (foll_price - entry_price) / entry_price

                if price_change >= 0.002:
                    self.results.append({
                        "pair": follower,
                        "entry_time": entry_time,
                        "exit_time": df.index[i],
                        "entry": entry_price,
                        "exit": foll_price,
                        "net": round(price_change, 5),
                        "result": "profit"
                    })
                    in_position = False

                elif price_change <= -0.001:
                    self.results.append({
                        "pair": follower,
                        "entry_time": entry_time,
                        "exit_time": df.index[i],
                        "entry": entry_price,
                        "exit": foll_price,
                        "net": round(price_change, 5),
                        "result": "loss"
                    })
                    in_position = False
