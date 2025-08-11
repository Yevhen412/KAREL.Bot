from collections import deque
from config import TICK_SIZE, TIME_STOP_SEC, MIN_SPREAD_TICKS, IMPULSE_TICKS, IMPULSE_WINDOW
from utils import now_ms
from telegram import log

class OrderManager:
    def __init__(self, simulator, side: str="long"):
        ...
        self.mid_history = deque(maxlen=IMPULSE_WINDOW)

    def _has_impulse(self) -> bool:
        if len(self.mid_history) < 3:
            return False
        first = self.mid_history[0]
        last  = self.mid_history[-1]
        delta = last - first
        ticks = delta / TICK_SIZE
        return (ticks >= IMPULSE_TICKS) if self.side == "long" else (ticks <= -IMPULSE_TICKS)

    def on_orderbook(self, best_bid: float, best_ask: float):
        # обновляем историю mid
        mid = (best_bid + best_ask) / 2
        self.mid_history.append(mid)

        # фильтр спреда
        spread_ticks = (best_ask - best_bid) / TICK_SIZE
        if spread_ticks < MIN_SPREAD_TICKS:
            # отменяем висящую лимитку, если спред схлопнулся
            if self.sim.open_order is not None:
                self.sim.cancel_entry()
                log("CANCEL: spread < MIN_SPREAD_TICKS")
                self.current_price = None
                self.last_place_ts = None
            return

        # импульс обязателен
        if not self._has_impulse():
            return

        # не ставим новую, если есть позиция
        if self.sim.position is not None:
            return

        price = self.desired_price(best_bid, best_ask)

        if self.sim.open_order is None:
            log(f"PLACE entry {self.side} @ {price:.1f} (spread_ticks={spread_ticks:.0f})")
            self.sim.place_entry_limit(self.side, price)
            self.current_price = price
            self.last_place_ts = now_ms()
            return

        if abs(price - (self.current_price or 0)) >= TICK_SIZE:
            log(f"REPLACE entry {self.side}: {self.current_price:.1f} → {price:.1f}")
            self.sim.cancel_entry()
            self.sim.place_entry_limit(self.side, price)
            self.current_price = price
            self.last_place_ts = now_ms()
            return

        if self.last_place_ts and now_ms() - self.last_place_ts > ORDER_LIFETIME * 1000:
            log(f"REFRESH entry {self.side} @ {price:.1f}")
            self.sim.cancel_entry()
            self.sim.place_entry_limit(self.side, price)
            self.current_price = price
            self.last_place_ts = now_ms()
            return
