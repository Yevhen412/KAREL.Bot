# order_manager.py
from typing import Optional
from collections import deque
from config import (
    TICK_SIZE, TIME_STOP_SEC,
    MIN_SPREAD_TICKS, IMPULSE_TICKS, IMPULSE_WINDOW,
)
from utils import now_ms
from telegram import log


class OrderManager:
    """
    Лимитки внутри спреда с фильтрами:
      - спред должен быть >= MIN_SPREAD_TICKS
      - микро-импульс в сторону сделки (IMPULSE_TICKS в окне IMPULSE_WINDOW)
      - перестановка по изменению цены и по таймауту
    """
    def __init__(self, simulator, side: str = "long"):
        assert side in ("long", "short")
        self.side = side
        self.sim = simulator
        self.last_place_ts: Optional[int] = None
        self.current_price: Optional[float] = None
        self.mid_history = deque(maxlen=IMPULSE_WINDOW)

    def desired_price(self, best_bid: float, best_ask: float) -> float:
        spread = round(best_ask - best_bid, 10)
        if self.side == "long":
            if spread <= TICK_SIZE:   # спред 1 тик — остаёмся maker на bid
                return best_bid
            return min(best_bid + TICK_SIZE, best_ask - TICK_SIZE)
        else:
            if spread <= TICK_SIZE:
                return best_ask
            return max(best_ask - TICK_SIZE, best_bid + TICK_SIZE)

    def _has_impulse(self) -> bool:
        if len(self.mid_history) < 3:
            return False
        first = self.mid_history[0]
        last = self.mid_history[-1]
        delta = last - first
        ticks = delta / TICK_SIZE
        return (ticks >= IMPULSE_TICKS) if self.side == "long" else (ticks <= -IMPULSE_TICKS)

    def on_orderbook(self, best_bid: float, best_ask: float):
        # если вдруг позиция уже открылась — снимем висящий вход
        if self.sim.position is not None:
            if self.sim.open_order is not None:
                self.sim.cancel_entry("position opened")
                self.current_price = None
                self.last_place_ts = None
            return

        # обновляем историю mid для импульса
        self.mid_history.append((best_bid + best_ask) / 2)
        spread_ticks = (best_ask - best_bid) / TICK_SIZE

        # фильтр по спреду
        if spread_ticks < MIN_SPREAD_TICKS:
            if self.sim.open_order is not None:
                self.sim.cancel_entry(f"spread<{MIN_SPREAD_TICKS} ticks (now={spread_ticks:.0f})")
                self.current_price = None
                self.last_place_ts = None
            return

        # фильтр по микро-импульсу
        if not self._has_impulse():
            return

        price = self.desired_price(best_bid, best_ask)

        # 1) нет лимитки — ставим новую
        if self.sim.open_order is None:
            self.sim.place_entry_limit(self.side, price)
            self.current_price = price
            self.last_place_ts = now_ms()
            log(f"📌 Placed NEW {self.side.upper()} limit @ {price:.1f}")
            return

        # 2) переставить из-за изменения цены (>= 1 тик)
        if abs(price - (self.current_price or 0)) >= TICK_SIZE:
            self.sim.cancel_entry(f"price change {self.current_price:.1f}→{price:.1f}")
            self.sim.place_entry_limit(self.side, price)
            self.current_price = price
            self.last_place_ts = now_ms()
            log(f"♻️ Price change → moved {self.side.UPPER()} limit to {price:.1f}")
            return

        # 3) обновить по таймауту (для приоритета в очереди)
        if self.last_place_ts and now_ms() - self.last_place_ts > TIME_STOP_SEC * 1000:
            self.sim.cancel_entry(f"lifetime>{TIME_STOP_SEC}s")
            self.sim.place_entry_limit(self.side, price)
            self.current_price = price
            self.last_place_ts = now_ms()
            log(f"⏳ Lifetime expired → refreshed {self.side.upper()} limit @ {price:.1f}")
            return
