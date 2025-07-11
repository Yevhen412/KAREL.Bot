from bybit_websocket import BybitWebSocket
from simulator import TradeSimulator

if __name__ == "__main__":
    ws = BybitWebSocket()
    simulator = TradeSimulator()

    for event in ws.listen():
        signal = simulator.process(event)
        if signal:
            simulator.simulate_trade(signal)