import json

class TradeSimulator:
    def __init__(self):
        self.in_trade = False

    def process(self, event):
        return self.generate_signal(event)

    def generate_signal(self, event):
        print("[DEBUG] Event received:", event)

        data = event.get("data")
        if not data or not isinstance(data, list):
            print("❌ Некорректный формат данных:", data)
            return None

        trade = data[0]
        price = trade.get("p")
        if price is None:
            print("⛔ Нет цены в событии:", trade)
            return None

        entry_price = float(price)
        print(f"[✅] Entry price: {entry_price}")
        return {"entry_price": entry_price}
