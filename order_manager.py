# order_manager.py
from time import time
from config import TICK_SIZE
from telegram import log

class OrderManager:
    """
    Диагностический маркет-мейкер:
      • Ставит обе лимитки (bid/ask) когда спред >= 2 тиков.
      • Переставляет при сдвиге топа >= 1 тик.
      • Явно логирует, ПОЧЕМУ не ставит ордера.
    """
    def __init__(self, simulator):
        self.sim = simulator
        self.last_bid = None
        self.last_ask = None

        # антиспам для диагностик
        self._last_diag = {}
        self._cooldown = 2.0  # сек между одинаковыми сообщениями

    def _diag(self, key: str, msg: str):
        now = time()
        if now - self._last_diag.get(key, 0) >= self._cooldown:
            log(msg)
            self._last_diag[key] = now

    def on_orderbook(self, best_bid: float, best_ask: float):
        # 1) проверка входных данных
        if best_bid is None or best_ask is None:
            self._diag("no_ba", "⚠️ Нет bid/ask из сокета (best_bid/best_ask is None)")
            return
        if best_ask < best_bid:
            self._diag("bad_ba", f"⚠️ Некорректные котировки: bid={best_bid} > ask={best_ask}")
            return

        spread = best_ask - best_bid
        spread_ticks = spread / TICK_SIZE

        # 2) спред слишком мал — ничего не ставим
        if spread_ticks < 2:
            self._diag(
                "small_spread",
                f"⏸ Спред мал: {spread_ticks:.2f} тика (bid={best_bid}, ask={best_ask}, tick={TICK_SIZE})"
            )
            return

        # ===== BID сторона =====
        bid_price = best_bid
        if getattr(self.sim, "open_buy_order", None) is None:
            self.sim.place_entry_limit("long", bid_price)
            self.last_bid = bid_price
            log(f"📥 Bid лимитка {bid_price}")
        elif abs(bid_price - (self.last_bid or bid_price)) >= TICK_SIZE:
            # переставляем, если ушли >= 1 тик
            if hasattr(self.sim, "cancel_buy"):
                self.sim.cancel_buy()
            self.sim.place_entry_limit("long", bid_price)
            self.last_bid = bid_price
            log(f"♻ Переставили Bid {bid_price}")

        # ===== ASK сторона =====
        ask_price = best_ask
        if not hasattr(self.sim, "open_sell_order"):
            self._diag("no_sell_attr", "❗ В simulator.py нет open_sell_order — Ask не будет поставлен")
            return

        if getattr(self.sim, "open_sell_order", None) is None:
            self.sim.place_entry_limit("short", ask_price)
            self.last_ask = ask_price
            log(f"📤 Ask лимитка {ask_price}")
        elif abs(ask_price - (self.last_ask or ask_price)) >= TICK_SIZE:
            if hasattr(self.sim, "cancel_sell"):
                self.sim.cancel_sell()
            self.sim.place_entry_limit("short", ask_price)
            self.last_ask = ask_price
            log(f"♻ Переставили Ask {ask_price}")
