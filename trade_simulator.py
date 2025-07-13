from telegram_bot import notify_telegram
from datetime import datetime
from collections import deque

class TradeSimulator:
    def __init__(self):
        self.history = deque(maxlen=500)

    def process(self, event):
        try:
            data = event["data"][0]
            symbol = data["s"]
            price = float(data["p"])
            side = "LONG" if data["S"] == "Buy" else "SHORT"
            return {"symbol": symbol, "side": side, "price": price}
        except Exception:
            return None

    def simulate_trade(self, signal):
        entry = signal["price"]
        side = signal["side"]
        symbol = signal["symbol"]
        amount = 200
        qty = amount / entry

        # 2:1 Risk/Reward
        risk_pct = 0.0035  # 0.35%
        tp = entry * (1 + 2 * risk_pct) if side == "LONG" else entry * (1 - 2 * risk_pct)
        sl = entry * (1 - risk_pct) if side == "LONG" else entry * (1 + risk_pct)

        # simulate exit at TP
        exit_price = tp
        gross = (exit_price - entry) * qty if side == "LONG" else (entry - exit_price) * qty

        # fees
        fee_rate = 0.0018 if side == "LONG" else 0.001
        fee_total = entry * qty * fee_rate + exit_price * qty * fee_rate
        net = gross - fee_total

        # log result
        status = "✅ PROFIT" if net > 0 else "❌ LOSS"
        result = {
            "timestamp": datetime.utcnow(),
            "symbol": symbol,
            "side": side,
            "entry": entry,
            "exit": exit_price,
            "gross": gross,
            "net": net,
            "fee": fee_total,
            "status": status
        }
        self.history.append(result)

        return (
            f"📈 <b>Trade Report</b>\n"
            f"🕒 Time: {result['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
            f"🔁 Side: {side}\n"
            f"💰 Entry: {entry:.4f}\n"
            f"🎯 Exit: {exit_price:.4f}\n"
            f"📉 Gross: {gross:.4f} USDT\n"
            f"💸 Fee: {fee_total:.4f} USDT\n"
            f"📊 Net: {net:.4f} USDT\n"
            f"📌 Result: {status}"
        )

    def generate_hourly_report(self):
        if not self.history:
            return None
        total = len(self.history)
        wins = sum(1 for t in self.history if t["net"] > 0)
        losses = total - wins
        pnl = sum(t["net"] for t in self.history)
        return (
            f"📊 <b>Hourly Summary</b>\n"
            f"Total trades: {total}\n"
            f"✅ Wins: {wins} | ❌ Losses: {losses}\n"
            f"💰 Net PnL: {pnl:.4f} USDT"
        )
