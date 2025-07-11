import time
from telegram_bot import notify_telegram

class TradeSimulator:
    def __init__(self):
        self.buffer = {}
        self.open_trades = {}

    def process(self, event):
        # Dummy processing for MVP
        return {"pair": "ETHUSDT", "direction": "long", "price": 3100.0}

    def simulate_trade(self, signal):
        entry_price = signal["price"]
        take_profit = entry_price * 1.002
        stop_loss = entry_price * 0.997
        notify_telegram(f"Trade simulated: {signal['pair']} at {entry_price}\nTP: {take_profit}, SL: {stop_loss}")