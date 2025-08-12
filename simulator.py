from config import MAKER_FEE, TAKER_FEE, TICK_SIZE
from telegram import log

class Simulator:
    def __init__(self):
        self.open_buy_order = None   # Лимитка на покупку
        self.open_sell_order = None  # Лимитка на продажу
        self.position_buy = None     # Купленная позиция (лонг)
        self.position_sell = None    # Проданная позиция (шорт)
        self.pnl = 0.0

    # --- Создание лимиток ---
    def place_entry_limit(self, side, price):
        if side == "long":
            self.open_buy_order = price
        elif side == "short":
            self.open_sell_order = price

    # --- Отмена лимиток ---
    def cancel_buy(self):
        self.open_buy_order = None

    def cancel_sell(self):
        self.open_sell_order = None

    # --- Обработка стакана ---
    def on_orderbook(self, bid, ask):
        # Если лимитка на покупку исполнилась
        if self.open_buy_order is not None and bid >= self.open_buy_order:
            self.position_buy = self.open_buy_order
            self.open_buy_order = None
            log(f"✅ ЛОНГ открыт по {self.position_buy}")

        # Если лимитка на продажу исполнилась
        if self.open_sell_order is not None and ask <= self.open_sell_order:
            self.position_sell = self.open_sell_order
            self.open_sell_order = None
            log(f"✅ ШОРТ открыт по {self.position_sell}")

        # --- Закрытие лонга ---
        if self.position_buy is not None and ask >= self.position_buy + TICK_SIZE:
            entry = self.position_buy
            exit_price = self.position_buy + TICK_SIZE
            profit = (exit_price - entry) - (entry * MAKER_FEE) - (exit_price * MAKER_FEE)
            self.pnl += profit
            log(f"📤 ЛОНГ закрылся: entry={entry}, exit={exit_price}, pnl={profit:.4f}")
            self.position_buy = None

        # --- Закрытие шорта ---
        if self.position_sell is not None and bid <= self.position_sell - TICK_SIZE:
            entry = self.position_sell
            exit_price = self.position_sell - TICK_SIZE
            profit = (entry - exit_price) - (entry * MAKER_FEE) - (exit_price * MAKER_FEE)
            self.pnl += profit
            log(f"📥 ШОРТ закрылся: entry={entry}, exit={exit_price}, pnl={profit:.4f}")
            self.position_sell = None
