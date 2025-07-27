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

# Храним последние цены и время последнего alive-сообщения
price_history = []
last_alive_time = 0

async def handle_socket():
    global last_alive_time
    url = "wss://stream.bybit.com/v5/public/spot"

    await send_message("✅ Бот запущен и ждёт импульс...")

    async with websockets.connect(url) as ws:
        await ws.send(json.dumps({
            "op": "subscribe",
            "args": [f"publicTrade.{SYMBOL}"]
        }))
        await send_message(f"✅ Подключен к WebSocket по {SYMBOL}")

        while True:
            try:
                message = await asyncio.wait_for(ws.recv(), timeout=30)
                data = json.loads(message)

                if "data" in data:
                    for trade in data["data"]:
                        price = float(trade["p"])
                        timestamp = time.time()
                        price_history.append((timestamp, price))

                        # Удаляем устаревшие записи
                        price_history[:] = [
                            (t, p) for t, p in price_history
                            if timestamp - t <= IMPULSE_WINDOW_SECONDS
                        ]

                        prices = [p for _, p in price_history]
                        if prices:
                            min_price = min(prices)
                            max_price = max(prices)
                            change_percent = (max_price - min_price) / min_price * 100

                            if change_percent >= IMPULSE_THRESHOLD_PERCENT:
                                direction = "вверх" if prices[-1] > prices[0] else "вниз"
                                await send_message(f"🚀 Импульс {direction}! Цена изменилась на {change_percent:.2f}% за последние {IMPULSE_WINDOW_SECONDS} сек.")

                # Alive-сообщение раз в N минут
                now = time.time()
                if now - last_alive_time > ALIVE_NOTIFICATION_INTERVAL_MINUTES * 60:
                    await send_message(f"⏳ Бот активен. Ждём импульс по {SYMBOL}...")
                    last_alive_time = now

            except asyncio.TimeoutError:
                await send_message("⚠️ Таймаут WebSocket. Переподключение...")
                break  # выйдем из цикла, пересоздастся соединение

async def main():
    while True:
        try:
            await handle_socket()
        except Exception as e:
            await send_message(f"❌ Ошибка в боте: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
