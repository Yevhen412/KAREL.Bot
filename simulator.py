# simulator.py
import time
from typing import Optional
from config import (
    MAKER_FEE, TAKER_FEE,
    TP_TICKS, SL_TICKS, TICK_SIZE,
    TRADE_SIZE, TIME_STOP_SEC,
)
from utils import now_ms
from telegram import log


class Position:
    def __init__(self, side: str, entry: float, qty_btc: float):
        self.side = side            # "long" | "short"
        self.entry = entry
        self.qty_btc = qty_btc
        self.opened_ms = now_ms()   # для тайм-стопа


class Simulator:
    """
    Симуляция исполнения:
      - вход: maker лимитка (MAKER_FEE)
      - TP:   maker лимит (MAKER_FEE)
      - SL:   выход по рынку (TAKER_FEE)
    """
    def __init__(self):
        self.open_order: Optional[dict] = None
        self.position: Optional[Position] = None
        self.realized_pnl: float = 0.0

        # Статистика для почасового отчёта
        self.hourly_stats = {"trades": 0, "wins": 0, "losses": 0, "sum_net": 0.0}
        self.last_report_time = time.time()

    # ---------- утилиты ----------
    def _fees(self, notional: float, rate: float) -> float:
        return notional * rate

    def _record_trade(self, trade_net: float):
        self.hourly_stats["trades"] += 1
        if trade_net > 0:
            self.hourly_stats["wins"] += 1
        else:
            self.hourly_stats["losses"] += 1
        self.hourly_stats["sum_net"] += trade_net

    def _maybe_send_report(self):
        now_t = time.time()
        if now_t - self.last_report_time >= 3600:  # раз в час
            trades = self.hourly_stats["trades"]
            wins = self.hourly_stats["wins"]
            losses = self.hourly_stats["losses"]
            sum_net = self.hourly_stats["sum_net"]
            win_rate = (wins / trades * 100) if trades > 0 else 0.0
            avg_trade = (sum_net / trades) if trades > 0 else 0.0
            net_percent = (avg_trade / TRADE_SIZE) * 100 if trades > 0 else 0.0

            log(
                "📊 Hourly Report:\n"
                f"Trades: {trades}\n"
                f"Wins: {wins}\n"
                f"Losses: {losses}\n"
                f"Win rate: {win_rate:.2f}%\n"
                f"Cum_net: {sum_net:.4f} USDT\n"
                f"Avg per trade: {avg_trade:.4f} USDT\n"
                f"Avg per trade (%): {net_percent:.4f}%"
            )
            # сброс статистики
            self.hourly_stats = {"trades": 0, "wins": 0, "losses": 0, "sum_net": 0.0}
            self.last_report_time = now_t

    # ---------- публичные методы ----------
    def place_entry_limit(self, side: str, price: float):
        qty_btc = TRADE_SIZE / price
        self.open_order = {"type": "entry", "side": side, "price": price, "qty": qty_btc}
        log(f"PLACE entry limit: side={side} price={price:.1f}")

    def cancel_entry(self, reason: str = ""):
        if self.open_order:
            px = self.open_order.get("price")
            if px is not None:
                log(f"CANCEL entry order at {px:.1f}" + (f" — {reason}" if reason else ""))
            else:
                log("CANCEL entry order" + (f" — {reason}" if reason else ""))
        self.open_order = None

    # ---------- обработчик стакана ----------
    def on_orderbook(self, best_bid: float, best_ask: float):
        # 1) Исполнение лимитки входа
        if self.open_order and self.open_order.get("type") == "entry" and self.position is None:
            side = self.open_order["side"]
            price = self.open_order["price"]
            qty = self.open_order["qty"]

            # LONG исполняем, когда bid >= price; SHORT — когда ask <= price
            if side == "long" and best_bid >= price:
                fee_in = self._fees(qty * price, MAKER_FEE)
                self.realized_pnl -= fee_in
                self.position = Position("long", price, qty)
                self.open_order = None
                # TP/SL уровни показываем в логике сделки (через тики)
                tp = price + TP_TICKS * TICK_SIZE
                sl = price - SL_TICKS * TICK_SIZE
                log(f"EXECUTED: LONG @ {price:.1f} | qty={qty:.6f} | fee_in={fee_in:.4f} | TP={tp:.1f} | SL={sl:.1f}")

            elif side == "short" and best_ask <= price:
                fee_in = self._fees(qty * price, MAKER_FEE)
                self.realized_pnl -= fee_in
                self.position = Position("short", price, qty)
                self.open_order = None
                tp = price - TP_TICKS * TICK_SIZE
                sl = price + SL_TICKS * TICK_SIZE
                log(f"EXECUTED: SHORT @ {price:.1f} | qty={qty:.6f} | fee_in={fee_in:.4f} | TP={tp:.1f} | SL={sl:.1f}")

        # 2) Сопровождение открытой позиции
        if self.position:
            pos = self.position

            # Тайм-стоп
            if now_ms() - pos.opened_ms >= TIME_STOP_SEC * 1000:
                exec_px = best_bid if pos.side == "long" else best_ask
                self._fill_sl(exec_px)  # рыночный выход
                return

            if pos.side == "long":
                # TP: нужен ask >= entry + TP_TICKS*tick
                if best_ask >= pos.entry + TP_TICKS * TICK_SIZE:
                    self._fill_tp(pos.entry + TP_TICKS * TICK_SIZE)
                # SL: рыночный выход, если bid <= entry - SL_TICKS*tick
                elif best_bid <= pos.entry - SL_TICKS * TICK_SIZE:
                    self._fill_sl(best_bid)
            else:  # short
                # TP: нужен bid <= entry - TP_TICKS*tick
                if best_bid <= pos.entry - TP_TICKS * TICK_SIZE:
                    self._fill_tp(pos.entry - TP_TICKS * TICK_SIZE)
                # SL: рыночный выход, если ask >= entry + SL_TICKS*tick
                elif best_ask >= pos.entry + SL_TICKS * TICK_SIZE:
                    self._fill_sl(best_ask)

    # ---------- закрытия ----------
    def _fill_tp(self, price: float):
        pos = self.position
        if not pos:
            return
        notional_exit = pos.qty_btc * price
        fee_out = self._fees(notional_exit, MAKER_FEE)  # maker выход
        move_pnl = (price - pos.entry) * pos.qty_btc if pos.side == "long" else (pos.entry - price) * pos.qty_btc
        trade_net = move_pnl - fee_out
        self.realized_pnl += trade_net

        self._record_trade(trade_net)
        self._maybe_send_report()

        log(f"CLOSED TP: {pos.side.upper()} @ {price:.1f} | trade_net={trade_net:.4f} USDT | cum_net={self.realized_pnl:.4f} USDT")
        self.position = None

    def _fill_sl(self, exec_price: float):
        pos = self.position
        if not pos:
            return
        notional_exit = pos.qty_btc * exec_price
        fee_out = self._fees(notional_exit, TAKER_FEE)  # taker выход
        move_pnl = (exec_price - pos.entry) * pos.qty_btc if pos.side == "long" else (pos.entry - exec_price) * pos.qty_btc
        trade_net = move_pnl - fee_out
        self.realized_pnl += trade_net

        self._record_trade(trade_net)
        self._maybe_send_report()

        log(f"CLOSED SL: {pos.side.upper()} @ {exec_price:.1f} | trade_net={trade_net:.4f} USDT | cum_net={self.realized_pnl:.4f} USDT")
        self.position = None
