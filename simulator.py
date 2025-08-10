# simulator.py
from dataclasses import dataclass
from typing import Optional
from config import TP_USD, SL_USD, TRADE_SIZE, MAKER_FEE, TAKER_FEE, TICK_SIZE
from logger import log

@dataclass
class Position:
    side: str              # "long" or "short"
    entry: float
    qty_btc: float
    tp: float
    sl: float

class Simulator:
    """
    Простая симуляция исполнения:
    - Вход: maker-лимитка (комиссия MAKER_FEE)
    - TP:   maker-лимитка (MAKER_FEE)
    - SL:   маркет-выход   (TAKER_FEE) по лучшему bid/ask
    """
    def __init__(self):
        self.open_order: Optional[dict] = None
        self.position: Optional[Position] = None
        self.realized_pnl: float = 0.0

    def place_entry_limit(self, side: str, price: float):
        self.open_order = {"type": "entry", "side": side, "price": price}
        log(f"ENTRY LIMIT placed: {side} @ {price:.1f}")

    def cancel_entry(self):
        if self.open_order and self.open_order["type"] == "entry":
            log("ENTRY LIMIT cancelled")
        self.open_order = None

    def _fees(self, notional: float, rate: float) -> float:
        return notional * rate

    def on_orderbook(self, best_bid: float, best_ask: float):
        # обработка входа, если есть лимитный ордер
        if self.open_order and self.open_order["type"] == "entry" and self.position is None:
            side = self.open_order["side"]
            price = self.open_order["price"]

            # Условие «сделки» в симуляции:
            # для лонга бид дошёл до нашей цены (нас "забрали"),
            # для шорта аск дошёл до нашей цены.
            if side == "long" and best_bid >= price:
                self._fill_entry(price, side)
            elif side == "short" and best_ask <= price:
                self._fill_entry(price, side)

        # если есть позиция — проверяем TP/SL
        if self.position:
            pos = self.position
            if pos.side == "long":
                # TP лимит: аск >= tp
                if best_ask >= pos.tp:
                    self._fill_tp(pos.tp)
                # SL маркет: если бид <= sl — выходим маркетом по бид
                elif best_bid <= pos.sl:
                    self._fill_sl(best_bid)
            else:  # short
                # TP лимит: бид <= tp (прибыль для шорта)
                if best_bid <= pos.tp:
                    self._fill_tp(pos.tp)
                # SL маркет: если аск >= sl — выходим маркетом по аск
                elif best_ask >= pos.sl:
                    self._fill_sl(best_ask)

    def _fill_entry(self, price: float, side: str):
        notional = TRADE_SIZE
        qty = notional / price
        fee = self._fees(notional, MAKER_FEE)  # maker вход
        self.realized_pnl -= fee
        tp = price + TP_USD if side == "long" else price - TP_USD
        sl = price - SL_USD if side == "long" else price + SL_USD
        self.position = Position(side=side, entry=price, qty_btc=qty, tp=tp, sl=sl)
        self.open_order = None
        log(f"ENTRY FILLED: {side} @ {price:.1f} | qty={qty:.6f} BTC | fee={fee:.4f} USDT "
            f"| TP={tp:.1f} SL={sl:.1f}")

    def _fill_tp(self, price: float):
        pos = self.position
        if not pos: 
            return
        notional_exit = pos.qty_btc * price
        fee = self._fees(notional_exit, MAKER_FEE)  # maker выход
        pnl_move = (price - pos.entry) * pos.qty_btc if pos.side == "long" else (pos.entry - price) * pos.qty_btc
        self.realized_pnl += pnl_move - fee
        log(f"TP FILLED @ {price:.1f} | move_pnl={pnl_move:.4f} | fee={fee:.4f} | net={self.realized_pnl:.4f}")
        self.position = None

    def _fill_sl(self, exec_price: float):
        pos = self.position
        if not pos:
            return
        notional_exit = pos.qty_btc * exec_price
        fee = self._fees(notional_exit, TAKER_FEE)  # taker выход
        pnl_move = (exec_price - pos.entry) * pos.qty_btc if pos.side == "long" else (pos.entry - exec_price) * pos.qty_btc
        self.realized_pnl += pnl_move - fee
        log(f"SL MARKET @ {exec_price:.1f} | move_pnl={pnl_move:.4f} | fee={fee:.4f} | net={self.realized_pnl:.4f}")
        self.position = None
