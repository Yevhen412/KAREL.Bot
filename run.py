"""
import time
from websocket_client import BybitWebSocket
from simulator import Simulator
from order_manager import OrderManager
from telegram import log

PNL_PING_SEC = 3600  # раз в 5 минут шлём текущий PnL (можешь поставить 0, чтобы отключить)

def main():
    log("Starting market-maker (SIMULATION MODE)")
    ws = BybitWebSocket()
    sim = Simulator()
    om = OrderManager(simulator=sim)

    ws.start()
    time.sleep(1.0)  # дать сокету подключиться

    last_pnl_ping = time.time()

    while True:
        bid, ask = ws.best_bid, ws.best_ask
        if bid and ask:
            # менеджер держит две лимитки (bid/ask), переставляет по стакану
            om.on_orderbook(bid, ask)
            # симулятор обрабатывает исполнения позиций и закрытия (TP по 1 тику)
            sim.on_orderbook(bid, ask)

        # периодический пинг по PnL
        if PNL_PING_SEC and (time.time() - last_pnl_ping) >= PNL_PING_SEC:
            try:
                log(f"💰 Current PnL: {sim.pnl:.4f} USDT")
            except Exception:
                pass
            last_pnl_ping = time.time()

        time.sleep(0.05)  # ~20 циклов/сек

if __name__ == "__main__":
    main()
