class TradeSimulator:
    def __init__(self):
        self.active_trade = False

    def generate_signal(self, event):
        try:
            data = event.get("data", {})
            if "p" not in data:
                print("⛔ Нет ключа 'p' в событии:", event)
                return None

            entry_price = float(data["p"])
            # Пример логики генерации сигнала
            signal = {"entry_price": entry_price}
            return signal
        except Exception as e:
            print(f"❌ Ошибка в generate_signal: {e}")
            return None

    def process(self, event):
        return self.generate_signal(event)
