import asyncio
import websockets
import json
import time
from datetime import datetime
from config import (
    SYMBOL,
    IMPULSE_THRESHOLD_PERCENT,
    IMPULSE_WINDOW_SECONDS,
    ALIVE_NOTIFICATION_INTERVAL_MINUTES,
)
from telegram_notifier import send_message

send_message("✅ Бот запущен и ждёт импульс...")

price_history = []
last_alive_time = 0

async def handle_socket():
    global last_alive_time
    url = "wss://stream.bybit.com/v5/public/spot"

    while True:
        try:
            async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
                await ws.send(json.dumps({
                    "op": "subscribe",
                    "args": [f"publicTrade.{SYMBOL}"]
                }))
                send_message(f"✅ Подключен к WebSocket по {SYMBOL}")

                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    # тут твоя логика анализа

        except Exception as e:
            send_message(f"❌ Ошибка WebSocket: {e}\nПереподключение через 5 сек...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(handle_socket())
