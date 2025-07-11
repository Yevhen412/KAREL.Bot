import asyncio
import websockets
import json
from collections import defaultdict
import time

class BybitWebSocket:
    def __init__(self):
        self.url = "wss://stream.bybit.com/v5/public/spot"
        self.symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "XRPUSDT", "ADAUSDT"]
        self.prices = defaultdict(list)

    async def _connect(self):
        async with websockets.connect(self.url) as ws:
            subscribe_msg = {
                "op": "subscribe",
                "args": [f"publicTrade.{symbol}" for symbol in self.symbols]
            }
            await ws.send(json.dumps(subscribe_msg))

            while True:
                msg = await ws.recv()
                yield json.loads(msg)

    def listen(self):
        return asyncio.run(self._connect())