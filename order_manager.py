# order_manager.py
from config import TICK_SIZE
from telegram import log

class OrderManager:
    def __init__(self, simulator):
        self.sim = simulator
        self.last_bid = None
        self.last_ask = None
        self._boot_logged = False  # <- диагностика

    def on_orderbook(self, best_bid: float, best_ask: float):
        if best_bid is None or best_ask is None:
            if not self._boot_logged:
                log("⚠️ best_bid/best_ask отсутствуют")
            return

        spread_ticks = (best_ask - best_bid) / TICK_SIZE
        if spread_ticks < 2:
            # необязательно логировать каждую итерацию, просто иногда
            return

        # ---- BID ----
        bid_price = best_bid
        placed_bid = False
        if getattr(self.sim, "open_buy_order", None) is None:
            self.sim.place_entry_limit("long", bid_price)
            self.last_bid = bid_price
            placed_bid = True
            log(f"📥 Bid лимитка {bid_price}")
        elif abs(bid_price - (self.last_bid or bid_price)) >= TICK_SIZE:
            if hasattr(self.sim, "cancel_buy"): self.sim.cancel_buy()
            self.sim.place_entry_limit("long", bid_price)
            self.last_bid = bid_price
            log(f"♻ Переставили Bid {bid_price}")

        # ---- ASK ----
        ask_price = best_ask
        placed_ask = False
        if getattr(self.sim, "open_sell_order", None) is None:
            self.sim.place_entry_limit("short", ask_price)
            self.last_ask = ask_price
            placed_ask = True
            log(f"📤 Ask лимитка {ask_price}")
        elif abs(ask_price - (self.last_ask or ask_price)) >= TICK_SIZE:
            if hasattr(self.sim, "cancel_sell"): self.sim.cancel_sell()
            self.sim.place_entry_limit("short", ask_price)
            self.last_ask = ask_price
            log(f"♻ Переставили Ask {ask_price}")

        # ---- единый стартовый лог (чтобы не съелось лимитером TG)
        if (placed_bid or placed_ask) and not self._boot_logged:
            log(
                f"🧪 placed_bid={placed_bid} open_buy={self.sim.open_buy_order is not None} | "
                f"placed_ask={placed_ask} open_sell={self.sim.open_sell_order is not None} | "
                f"spread_ticks={spread_ticks:.0f}"
            )
            self._boot_logged = True
