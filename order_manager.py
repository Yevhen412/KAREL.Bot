# order_manager.py
from typing import Optional
from config import TICK_SIZE, ORDER_LIFETIME
from utils import now_ms
from telegram import log

class OrderManager:
    """
    Микроскальпинг: вход лимиткой внутри спреда, выход лимиткой по TP или SL.
    Обе стороны сделки — Maker, чтобы минимизировать комиссии.
    """

    def __init__(self, simulator, side: str = "long", tp_ticks: int = 2, sl_ticks: int = 2):
        assert side in ("long", "short")
        self.side = side
        self.sim = simulator
        self.tp_ticks = tp_ticks
        self.sl_ticks = sl_ticks
        self.last_place_ts: Optional[int] = None
        self.entry_price: Optional[float] = None
        self.exit_order_id: Optional[str] = None

    def desired_entry_price(self, best_bid: float, best_ask: float) -> float:
        """Определяем цену входа, чтобы быть Maker."""
        spread = round(best_ask - best_bid, 10)
        if self.side == "long":
            if spread <= TICK_SIZE:
                return best_bid
            return min(best_bid + TICK_SIZE, best_ask - TICK_SIZE)
        else:  # short
            if spread <= TICK_SIZE:
                return best_ask
            return max(best_ask - TICK_SIZE, best_bid + TICK_SIZE)

    def on_orderbook(self, best_bid: float, best_ask: float):
        now = now_ms()

        # Если нет позиции и нет открытого входа — ставим новый вход
        if self.sim.position is None and self.sim.open_order is None:
            entry_price = self.desired_entry_price(best_bid, best_ask)
            self.sim.place_entry_limit(self.side, entry_price)
            self.entry_price = entry_price
            self.last_place_ts = now
            log(f"[ENTRY] Placed {self.side.upper()} entry at {entry_price}")
            return

        # Если позиция открыта и нет выхода — ставим TP и SL лимитками
        if self.sim.position is not None and self.exit_order_id is None:
            if self.side == "long":
                tp_price = self.entry_price + self.tp_ticks * TICK_SIZE
                sl_price = self.entry_price - self.sl_ticks * TICK_SIZE
            else:
                tp_price = self.entry_price - self.tp_ticks * TICK_SIZE
                sl_price = self.entry_price + self.sl_ticks * TICK_SIZE

            # Ставим TP
            self.sim.place_exit_limit(tp_price)
            log(f"[TP] Placed exit at {tp_price}")

            # Ставим SL
            self.sim.place_exit_limit(sl_price)
            log(f"[SL] Placed stop at {sl_price}")

            self.exit_order_id = "active"
            return

        # Переставляем вход, если он висит слишком долго
        if self.sim.position is None and self.sim.open_order is not None:
            if now - (self.last_place_ts or 0) > ORDER_LIFETIME * 1000:
                log("[ENTRY] Replacing stale entry order")
                self.sim.cancel_entry()
                entry_price = self.desired_entry_price(best_bid, best_ask)
                self.sim.place_entry_limit(self.side, entry_price)
                self.entry_price = entry_price
                self.last_place_ts = now
                return

        # Если позиция закрыта — сбрасываем выходы
        if self.sim.position is None and self.exit_order_id is not None:
            log("[EXIT] Position closed, clearing exit orders")
            self.exit_order_id = None
            self.entry_price = None
