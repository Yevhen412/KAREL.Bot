import asyncio
import json
import websockets

class PumpFunListener:
    def __init__(self, callback):
        self.callback = callback
        self.ws_url = "wss://api.pump.fun/socket/websocket?vsn=2.0.0"

    async def connect(self):
        async with websockets.connect(self.ws_url) as websocket:
            await self.join_channel(websocket)

            while True:
                try:
                    message = await websocket.recv()
                    await self.handle_message(message)
                except websockets.ConnectionClosed:
                    print("[pump_ws.py] 🔁 Соединение закрыто. Переподключение...")
                    await asyncio.sleep(2)
                    await self.connect()

    async def join_channel(self, websocket):
        join_msg = [
            None,
            "1",
            "token:global",
            "phx_join",
            {}
        ]
        await websocket.send(json.dumps(join_msg))
        print("[pump_ws.py] ✅ Подключено к каналу Pump.fun")

    async def handle_message(self, raw_msg):
        try:
            data = json.loads(raw_msg)
            if isinstance(data, list) and len(data) > 4:
                event_type = data[3]
                payload = data[4]
                if event_type == "global_tokens":
                    tokens = payload.get("tokens", [])
                    for token in tokens:
                        await self.callback(token)
        except Exception as e:
            print(f"[pump_ws.py] ⚠️ Ошибка разбора сообщения: {e}")
