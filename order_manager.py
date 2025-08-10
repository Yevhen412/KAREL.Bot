# order_manager.py
from typing import Optional
from config import TICK_SIZE, ORDER_LIFETIME
from utils import now_ms
from telegram import log

class OrderManager:
    """
    Отвечает за выбор стороны и цены входа, постановку и перестановку лимитки.
    Правило цены (чтобы оставаться maker):
      - Для ЛОНГ: ставим цену = min(best_bid + тик, best_ask - тик).
      - Если спред = 1 тик, остаёмся на best_bid (иначе станет taker).
      - Для ШОРТ аналогично от ask-тика.
    """
    def __init__(self, simulator, side: str = "long"):
        assert side in ("long", "short")
        self.side = side
        self.sim = simulator
        self.last_place_ts: Optional[int] = None
        self.current_price: Optional[float] = None

    def desired_price(self, best_bid: float, best_ask: float) -> float:
        spread = round(best_ask - best_bid, 10)
        if self.side == "long":
            if spread <= TICK_SIZE:           # спред 1 тик — остаёмся на bid
                return best_bid
            return min(best_bid + TICK_SIZE, best_ask - TICK_SIZE)
        else:
            if spread <= TICK_SIZE:
                return best_ask
            return max(best_ask - TICK_SIZE, best_bid + TICK_SIZE)

    def on_orderbook(self, best_bid: float, best_ask: float):
        # если есть позиция — входы не ставим
        if self.sim.position is not None:
            return

        price = self.desired_price(best_bid, best_ask)

        # если нет активной лимитки — ставим
        if self.sim.open_order is None:
            self.sim.place_entry_limit(self.side, price)
            self.current_price = price
            self.last_place_ts = now_ms()
            return

        # если лимитка есть, но цена сменилась заметно — переставим
        if abs(price - (self.current_price or 0)) >= TICK_SIZE:
            self.sim.cancel_entry()
            self.sim.place_entry_limit(self.side, price)
            self.current_price = price
            self.last_place_ts = now_ms()
            return

        # если висим дольше срока — переставим для приоритета в очереди
        if self.last_place_ts and now_ms() - self.last_place_ts > ORDER_LIFETIME * 1000:
            self.sim.cancel_entry()
            self.sim.place_entry_limit(self.side, price)
            self.current_price = price
            self.last_place_ts = now_ms()
            return
