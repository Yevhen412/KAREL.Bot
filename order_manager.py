# order_manager.py
from typing import Optional
from config import TICK_SIZE, TRADE_SIZE, TIME_STOP_SEC
from utils import now_ms
from telegram import log


class OrderManager:
    """
    Управляет постановкой и перестановкой лимиток для стратегии микроскальпинга.
    Логика:
      - ЛОНГ: цена = min(best_bid + тик, best_ask - тик) (чтобы быть maker).
      - Если спред = 1 тик, остаёмся на best_bid.
      - ШОРТ: аналогично, но от ask-тиков.
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
            if spread <= TICK_SIZE:
                return best_bid
            return min(best_bid + TICK_SIZE, best_ask - TICK_SIZE)
        else:
            if spread <= TICK_SIZE:
                return best_ask
            return max(best_ask - TICK_SIZE, best_bid + TICK_SIZE)

    def on_orderbook(self, best_bid: float, best_ask: float):
        # Не ставим вход, если уже есть открытая позиция
        if self.sim.position is not None:
            return

        price = self.desired_price(best_bid, best_ask)

        # 1️⃣ Нет лимитки — ставим новую
        if self.sim.open_order is None:
            self.sim.place_entry_limit(self.side, price)
            self.current_price = price
            self.last_place_ts = now_ms()
            log(f"📌 Placed NEW {self.side.upper()} limit @ {price:.1f}")
            return

        # 2️⃣ Цена изменилась — переставляем
        if abs(price - (self.current_price or 0)) >= TICK_SIZE:
            self.sim.cancel_entry()
            self.sim.place_entry_limit(self.side, price)
            self.current_price = price
            self.last_place_ts = now_ms()
            log(f"♻️ Price change → moved {self.side.upper()} limit to {price:.1f}")
            return

        # 3️⃣ Лимитка висит дольше ORDER_LIFETIME — переставляем для приоритета
        if self.last_place_ts and now_ms() - self.last_place_ts > TIME_STOP_SEC * 1000:
            self.sim.cancel_entry()
            self.sim.place_entry_limit(self.side, price)
            self.current_price = price
            self.last_place_ts = now_ms()
            log(f"⏳ Lifetime expired → refreshed {self.side.upper()} limit @ {price:.1f}")
            return
