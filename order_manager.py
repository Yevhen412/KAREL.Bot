# order_manager.py
from config import TICK_SIZE
from telegram import log

class OrderManager:
    def __init__(self, simulator):
        self.sim = simulator
        self.last_bid = None
        self.last_ask = None

    def on_orderbook(self, best_bid: float, best_ask: float):
        if best_bid is None or best_ask is None:
            return

        spread_ticks = (best_ask - best_bid) / TICK_SIZE
        if spread_ticks < 2:
            return

        # --- BID ---
        bid_price = best_bid
        placed_bid = False
        if getattr(self.sim, "open_buy_order", None) is None:
            self.sim.place_entry_limit("long", bid_price)
            self.last_bid = bid_price
            placed_bid = True
        elif abs(bid_price - (self.last_bid or bid_price)) >= TICK_SIZE:
            if hasattr(self.sim, "cancel_buy"): self.sim.cancel_buy()
            self.sim.place_entry_limit("long", bid_price)
            self.last_bid = bid_price
            placed_bid = True  # тоже считаем как «событие»

        # --- ASK ---
        ask_price = best_ask
        placed_ask = False
        if getattr(self.sim, "open_sell_order", None) is None:
            self.sim.place_entry_limit("short", ask_price)
            self.last_ask = ask_price
            placed_ask = True
        elif abs(ask_price - (self.last_ask or ask_price)) >= TICK_SIZE:
            if hasattr(self.sim, "cancel_sell"): self.sim.cancel_sell()
            self.sim.place_entry_limit("short", ask_price)
            self.last_ask = ask_price
            placed_ask = True

        # ЕДИНЫЙ ЛОГ — не съестся лимитером TG
        if placed_bid or placed_ask:
            log(f"📥 Bid {bid_price} | 📤 Ask {ask_price} | spread={spread_ticks:.0f}t")
