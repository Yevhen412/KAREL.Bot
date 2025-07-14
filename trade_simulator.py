
import json

class TradeSimulator:
    def __init__(self):
        self.in_trade = False

    def process(self, event):
        return self.generate_signal(event)

    def generate_signal(self, event):
        data = event.get("data")
        if isinstance(data, list) and len(data) > 0 and "p" in data[0]:
            entry_price = float(data[0]["p"])
            print(f"[✅] Entry price: {entry_price}")
            return {"entry_price": entry_price}
        else:
            print(f"❌ Нет ключа 'p' в событии: {json.dumps(event)}")
            return None
