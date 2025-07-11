import asyncio
import websockets
import json
from collections import defaultdict

class BybitWebSocket:
    def __init__(self):
        self.url = "wss://stream.bybit.com/v5/public/spot"
        self.symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "XRPUSDT", "ADAUSDT"]
        self.prices = defaultdict(list)

    async def _connect(self):
        self.ws = await websockets.connect(self.url)
        subscribe_msg = {
            "op": "subscribe",
            "args": [f"publicTrade.{symbol}" for symbol in self.symbols]
        }
        await self.ws.send(json.dumps(subscribe_msg))

    async def listen(self):
        await self._connect()

        async for message in self.ws:
            data = json.loads(message)
            yield data
