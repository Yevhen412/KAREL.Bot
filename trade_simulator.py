import json

class TradeSimulator:
    def __init__(self):
        self.in_trade = False  # Флаг: находимся ли в позиции

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

            entry_price_raw = trade.get("p")
            if entry_price_raw is None:
                print("❌ В trade нет ключа 'p':", trade)
                return None

            try:
                entry_price = float(entry_price_raw)
            except (ValueError, TypeError) as e:
                print(f"❌ Невозможно преобразовать 'p' в число: {entry_price_raw} — {e}")
                return None

            print(f"[✅] Entry price: {entry_price}")
            return {"entry_price": entry_price}

        except Exception as e:
            print(f"🔥 Ошибка в generate_signal: {e}")
            return None

    def simulate_trade(self, signal):
        """Метод заглушка — можно расширить под реальную симуляцию."""
        if not signal:
            return "❌ Сигнал не получен."

        entry_price = signal.get("entry_price")
        if entry_price is None:
            return "❌ Нет цены входа."

        # Здесь можно расширить: расчет прибыли/убытка и т.д.
        print(f"[SIMULATION] Сделка открыта по цене: {entry_price}")
        return f"✅ Сделка симулирована по цене: {entry_price}"
