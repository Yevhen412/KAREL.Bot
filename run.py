"""
import time
from websocket_client import BybitWebSocket
from simulator import Simulator
from order_manager import OrderManager
from telegram import log

TRADE_SIDE = "long"   # "long" или "short"

def main():
    log("Starting maker-bot (SIMULATION MODE)")
    ws = BybitWebSocket()
    sim = Simulator()
    om = OrderManager(simulator=sim, side=TRADE_SIDE)

    ws.start()
    time.sleep(1.0)  # даём сокету подключиться

    while True:
        bid, ask = ws.best_bid, ws.best_ask
        if bid and ask:
            # 1) решаем, куда ставить/переставлять лимитку
            om.on_orderbook(bid, ask)
            # 2) проверяем исполнение входа/TP/SL в симуляции
            sim.on_orderbook(bid, ask)
        time.sleep(0.1)

if __name__ == "__main__":
    main()
