# order_manager.py
from typing import Optional
from collections import deque
from config import (
    TICK_SIZE, TIME_STOP_SEC,
    MIN_SPREAD_TICKS, IMPULSE_TICKS, IMPULSE_WINDOW
)
from utils import now_ms
from telegram import log

class OrderManager:
    """
    Лимитки внутри спреда с фильтрами: спред, микро-импульс, таймаут.
    """

    def __init__(self, simulator, side: str = "long"):
        assert side in ("long", "short")
        self.side = side
        self.sim = simulator                  # <<< ВАЖНО: сохраняем симулятор
        self.last_place_ts: Optional[int] = None
        self.current_price: Optional[float] = None
        self.mid_history = deque(maxlen=IMPULSE_WINDOW)

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

    def _has_impulse(self) -> bool:
        if len(self.mid_history) < 3:
            return False
        first = self.mid_history[0]
        last  = self.mid_history[-1]
        delta = last - first
        ticks = delta / TICK_SIZE
        return (ticks >= IMPULSE_TICKS) if self.side == "long" else (ticks <= -IMPULSE_TICKS)

    def on_orderbook(self, best_bid: float, best_ask: float):
        # защита, если вдруг конструктор не отработал
        if not hasattr(self, "sim") or self.sim is None:
            log("OrderManager misconfigured: self.sim is None")
            return

        # обновляем mid и фильтры
        self.mid_history.append((best_bid + best_ask) / 2)
        spread_ticks = (best_ask - best_bid) / TICK_SIZE

        # если позиция открыта — не ставим новые входы
        if self.sim.position is not None:
            return

        # фильтр спреда
        if spread_ticks < MIN_SPREAD_TICKS:
            if self.sim.open_order is not None:
                self.sim.cancel_entry()
                log("CANCEL: spread < MIN_SPREAD_TICKS")
                self.current_price = None
                self.last_place_ts = None
            return

        # фильтр микро-импульса
        if not self._has_impulse():
            return

        price = self.desired_price(best_bid, best_ask)

        # нет активной лимитки — ставим
        if self.sim.open_order is None:
            log(f"PLACE entry limit: side={self.side} price={price:.1f} (spread_ticks={spread_ticks:.0f})")
            self.sim.place_entry_limit(self.side, price)
            self.current_price = price
            self.last_place_ts = now_ms()
            return

        # перестановка по изменению цены
        if abs(price - (self.current_price or 0)) >= TICK_SIZE:
            log(f"REPLACE entry limit: {self.current_price:.1f} → {price:.1f}")
            self.sim.cancel_entry()
            self.sim.place_entry_limit(self.side, price)
            self.current_price = price
            self.last_place_ts = now_ms()
            return

        # обновление по таймауту
        if self.last_place_ts and now_ms() - self.last_place_ts > ORDER_LIFETIME * 1000:
            log(f"REFRESH entry limit @ {price:.1f}")
            self.sim.cancel_entry()
            self.sim.place_entry_limit(self.side, price)
            self.current_price = price
            self.last_place_ts = now_ms()
