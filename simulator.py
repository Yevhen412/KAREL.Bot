# simulator.py
import time
from typing import Optional
from config import MAKER_FEE, TAKER_FEE, TP_TICKS, SL_TICKS, TICK_SIZE, ORDER_SIZE_USD
from utils import now_ms
from telegram import log


class Position:
    def __init__(self, side: str, entry: float, qty_btc: float):
        self.side = side
        self.entry = entry
        self.qty_btc = qty_btc


class Simulator:
    def __init__(self):
        self.open_order: Optional[dict] = None
        self.position: Optional[Position] = None
        self.realized_pnl: float = 0.0

        # Для статистики
        self.hourly_stats = {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "sum_net": 0.0
        }
        self.last_report_time = time.time()

    def _fees(self, notional: float, fee_rate: float) -> float:
        return notional * fee_rate

    def place_entry_limit(self, side: str, price: float):
        qty_btc = ORDER_SIZE_USD / price
        self.open_order = {"side": side, "price": price, "qty": qty_btc}
        log(f"PLACE entry limit: side={side} price={price:.1f}")
    
    def cancel_entry(self):
        if self.open_order:
            log(f"CANCEL entry order at {self.open_order['price']:.1f}")
        self.open_order = None

    def _record_trade(self, trade_net: float):
        self.hourly_stats["trades"] += 1
        if trade_net > 0:
            self.hourly_stats["wins"] += 1
        else:
            self.hourly_stats["losses"] += 1
        self.hourly_stats["sum_net"] += trade_net

    def _maybe_send_report(self):
        now_t = time.time()
        if now_t - self.last_report_time >= 3600:  # 1 час
            trades = self.hourly_stats["trades"]
            wins = self.hourly_stats["wins"]
            losses = self.hourly_stats["losses"]
            sum_net = self.hourly_stats["sum_net"]
            win_rate = (wins / trades * 100) if trades > 0 else 0
            avg_trade = (sum_net / trades) if trades > 0 else 0
            net_percent = (avg_trade / (ORDER_SIZE_USD)) * 100 if trades > 0 else 0

            log(
                f"📊 Hourly Report:\n"
                f"Trades: {trades}\n"
                f"Wins: {wins}\n"
                f"Losses: {losses}\n"
                f"Win rate: {win_rate:.2f}%\n"
                f"Cum_net: {sum_net:.4f} USDT\n"
                f"Avg per trade: {avg_trade:.4f} USDT\n"
                f"Avg per trade (%): {net_percent:.4f}%"
            )

            # сброс
            self.hourly_stats = {"trades": 0, "wins": 0, "losses": 0, "sum_net": 0.0}
            self.last_report_time = now_t

    def _fill_tp(self, price: float):
        pos = self.position
        if not pos:
            return
        notional_exit = pos.qty_btc * price
        fee_out = self._fees(notional_exit, MAKER_FEE)
        move_pnl = (price - pos.entry) * pos.qty_btc if pos.side == "long" else (pos.entry - price) * pos.qty_btc
        trade_net = move_pnl - fee_out
        self.realized_pnl += trade_net

        self._record_trade(trade_net)
        self._maybe_send_report()

        log(f"CLOSED TP: {pos.side.upper()} @ {price:.1f} "
            f"| trade_net={trade_net:.4f} USDT "
            f"| cum_net={self.realized_pnl:.4f} USDT")

        self.position = None

    def _fill_sl(self, exec_price: float):
        pos = self.position
        if not pos:
            return
        notional_exit = pos.qty_btc * exec_price
        fee_out = self._fees(notional_exit, TAKER_FEE)
        move_pnl = (exec_price - pos.entry) * pos.qty_btc if pos.side == "long" else (pos.entry - exec_price) * pos.qty_btc
        trade_net = move_pnl - fee_out
        self.realized_pnl += trade_net

        self._record_trade(trade_net)
        self._maybe_send_report()

        log(f"CLOSED SL: {pos.side.upper()} @ {exec_price:.1f} "
            f"| trade_net={trade_net:.4f} USDT "
            f"| cum_net={self.realized_pnl:.4f} USDT")

        self.position = None

    def on_orderbook(self, best_bid: float, best_ask: float):
        now = now_ms()

        # Исполнение лимитки входа
        if self.open_order:
            if self.open_order["side"] == "long" and best_ask <= self.open_order["price"]:
                fee_in = self._fees(self.open_order["qty"] * self.open_order["price"], MAKER_FEE)
                self.position = Position("long", self.open_order["price"], self.open_order["qty"])
                log(f"EXECUTED: LONG @ {self.open_order['price']:.1f} | fee_in={fee_in:.4f}")
                self.open_order = None
            elif self.open_order["side"] == "short" and best_bid >= self.open_order["price"]:
                fee_in = self._fees(self.open_order["qty"] * self.open_order["price"], MAKER_FEE)
                self.position = Position("short", self.open_order["price"], self.open_order["qty"])
                log(f"EXECUTED: SHORT @ {self.open_order['price']:.1f} | fee_in={fee_in:.4f}")
                self.open_order = None

        # Исполнение TP / SL
        if self.position:
            if self.position.side == "long":
                if best_bid >= self.position.entry + TP_TICKS * TICK_SIZE:
                    self._fill_tp(best_bid)
                elif best_bid <= self.position.entry - SL_TICKS * TICK_SIZE:
                    self._fill_sl(best_bid)
            elif self.position.side == "short":
                if best_ask <= self.position.entry - TP_TICKS * TICK_SIZE:
                    self._fill_tp(best_ask)
                elif best_ask >= self.position.entry + SL_TICKS * TICK_SIZE:
                    self._fill_sl(best_ask)
