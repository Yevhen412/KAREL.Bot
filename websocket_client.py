# websocket_client.py
import json
import websocket
import threading
from config import SYMBOL

class BybitWebSocket:
    def __init__(self):
        self.best_bid = None
        self.best_ask = None
        self.ws_url = "wss://stream.bybit.com/v5/public/linear"

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            if "topic" in data and "orderbook" in data["topic"]:
                bids = data["data"]["b"]
                asks = data["data"]["a"]

                if bids and asks:
                    self.best_bid = float(bids[0][0])
                    self.best_ask = float(asks[0][0])
                    print(f"[BID] {self.best_bid}  |  [ASK] {self.best_ask}")
        except Exception as e:
            print(f"[ERROR] on_message: {e}")

    def _on_open(self, ws):
        print("[WS] Connected to Bybit")
        sub_msg = {
            "op": "subscribe",
            "args": [f"orderbook.1.{SYMBOL}"]
        }
        ws.send(json.dumps(sub_msg))

    def _on_close(self, ws, close_status_code, close_msg):
        print("[WS] Disconnected from Bybit")

    def start(self):
        ws = websocket.WebSocketApp(
            self.ws_url,
            on_message=self._on_message,
            on_open=self._on_open,
            on_close=self._on_close
        )
        wst = threading.Thread(target=ws.run_forever)
        wst.daemon = True
        wst.start()
