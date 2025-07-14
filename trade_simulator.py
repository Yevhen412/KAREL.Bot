
import json

class TradeSimulator:
    def __init__(self):
        self.in_trade = False

    def process(self, event):
        return self.generate_signal(event)

    def generate_signal(self, event):
        print("[DEBUG] Raw event:", event)

        try:
            data = event.get("data", None)

            if not isinstance(data, list):
                print("❌ event['data'] не является списком:", data)
                return None
            if not data:
                print("⚠️ event['data'] — пустой список")
                return None

            trade = data[0]
            if not isinstance(trade, dict):
                print("❌ trade не является словарём:", trade)
                return None

            if "p" not in trade:
                print("❌ В trade нет ключа 'p':", trade)
                return None

            entry_price = float(trade["p"])
            print(f"[✅] Entry price: {entry_price}")
            return {"entry_price": entry_price}

        except Exception as e:
            print(f"🔥 Ошибка в generate_signal: {e}")
            return None
