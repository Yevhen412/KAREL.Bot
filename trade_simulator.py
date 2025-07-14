import time

class TradeSimulator:
    def __init__(self):
        self.in_position = False  # === Новый флаг ===
        self.last_report_time = time.time()

    def process(self, event):
        # Логика генерации сигнала
        return self.generate_signal(event)

    def generate_signal(self, event):
        # Заглушка — здесь будет логика анализа
        return {
            "side": "long",  # или "short"
            "symbol": event.get("symbol", "UNKNOWN"),
            "entry_price": float(event["data"]["p"]),
            "timestamp": time.time()
        }

    def simulate_trade(self, signal):
        if self.in_position:
            return None  # === Запрет на вторую сделку ===

        self.in_position = True
        symbol = signal["symbol"]
        side = signal["side"]
        entry = signal["entry_price"]

        # Примитивная симуляция тейка и стопа
        profit = round(0.58 if side == "long" else -0.29, 2)

        self.in_position = False

        # === Тикер в сообщении ===
        return f"🔁 Сделка {symbol} [{side.upper()}] → PnL: {profit}$"

    def generate_hourly_report(self):
        return "🕒 Почасовой отчёт пока не реализован"
