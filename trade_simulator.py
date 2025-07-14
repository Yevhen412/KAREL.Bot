class TradeSimulator:
    def __init__(self):
        self.in_trade = False

    def process(self, event):
        return self.generate_signal(event)

    def generate_signal(self, event):
        try:
            data = event.get("data", None)
            if not isinstance(data, list) or not data:
                print("⚠️ event['data'] некорректен:", data)
                return None

            trade = data[0]
            entry_price_raw = trade.get("p")
            if entry_price_raw is None:
                print("❌ В trade нет ключа 'p':", trade)
                return None

            entry_price = float(entry_price_raw)
            print(f"[✅] Entry price: {entry_price}")
            return {
                "entry_price": entry_price,
                "side": trade.get("S", "UNKNOWN"),
                "symbol": trade.get("s", "UNKNOWN")
            }

        except Exception as e:
            print(f"🔥 Ошибка в generate_signal: {e}")
            return None

    def simulate_trade(self, signal):
        if self.in_trade:
            print("⏸ Уже есть открытая сделка. Пропускаем.")
            return None

        self.in_trade = True
        try:
            entry = signal["entry_price"]
            exit_price = round(entry * 0.99, 4)  # Условная симуляция
            gross = 1.4
            fee = round(gross * 0.285, 4)
            net = round(gross - fee, 4)
            result = "✅ PROFIT" if net > 0 else "❌ LOSS"

            report = f"""📉<b>Trade Report</b>
🕒 Time: 2025-07-13 22:43:52 UTC
📉 Side: SHORT
📈 Entry: {entry}
📉 Exit: {exit_price}
🎯 Gross: {gross} USDT
🧾 Fee: {fee} USDT
📊 Net: {net} USDT
📌 Result: {result}"""

            print("[SIMULATION] Сделка симулирована по цене:", entry)
            return report

        finally:
            self.in_trade = False
