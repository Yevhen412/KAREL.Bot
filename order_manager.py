from typing import Optional
from config import TICK_SIZE, ORDER_LIFETIME, MAKER_FEE
from utils import now_ms
from telegram import log

class OrderManager:
    """
    Маркет-мейкер:
      - Ставит лимитку на покупку по bid
      - Ставит лимитку на продажу по ask
      - При исполнении одной стороны, закрывает её встречной сделкой
    """
    def __init__(self, simulator):
        self.sim = simulator
        self.last_place_ts: Optional[int] = None
        self.current_bid_price: Optional[float] = None
        self.current_ask_price: Optional[float] = None

    def on_orderbook(self, best_bid: float, best_ask: float):
        spread = round(best_ask - best_bid, 10)

        # Не лезем, если спред меньше 2 тиков (невыгодно)
        if spread < 2 * TICK_SIZE:
            return

        # --- Лимитка на покупку ---
        bid_price = best_bid
        if self.sim.open_buy_order is None:
            self.sim.place_entry_limit("long", bid_price)
            self.current_bid_price = bid_price
            log(f"📥 Bid лимитка {bid_price}")
        elif abs(bid_price - (self.current_bid_price or 0)) >= TICK_SIZE:
            self.sim.cancel_buy()
            self.sim.place_entry_limit("long", bid_price)
            self.current_bid_price = bid_price
            log(f"♻ Переставили Bid {bid_price}")

        # --- Лимитка на продажу ---
        ask_price = best_ask
        if self.sim.open_sell_order is None:
            self.sim.place_entry_limit("short", ask_price)
            self.current_ask_price = ask_price
            log(f"📤 Ask лимитка {ask_price}")
        elif abs(ask_price - (self.current_ask_price or 0)) >= TICK_SIZE:
            self.sim.cancel_sell()
            self.sim.place_entry_limit("short", ask_price)
            self.current_ask_price = ask_price
            log(f"♻ Переставили Ask {ask_price}")
