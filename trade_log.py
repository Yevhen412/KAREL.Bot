import pandas as pd

class TradeLogger:
    def __init__(self, trades_df: pd.DataFrame):
        self.df = trades_df

    def summary(self):
        if self.df.empty:
            print("Нет совершённых сделок.")
            return

        total_trades = len(self.df)
        wins = self.df[self.df['result'] == 'profit']
        losses = self.df[self.df['result'] == 'loss']
        win_rate = len(wins) / total_trades * 100
        avg_net = self.df['net'].mean()
        total_net = self.df['net'].sum()

        print("\n📈 Результаты симуляции:")
        print(f"Всего сделок: {total_trades}")
        print(f"Профитных: {len(wins)} | Убыточных: {len(losses)}")
        print(f"Win-rate: {win_rate:.2f}%")
        print(f"Средний net: {avg_net:.5f}")
        print(f"Суммарный net (PnL): {total_net:.5f}")
        print("\n🔍 Последние 5 сделок:")
        print(self.df.tail())
