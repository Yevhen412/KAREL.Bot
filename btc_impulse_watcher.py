import asyncio
import websockets
import json
import time
from datetime import datetime, timedelta
from config import (
    SYMBOL,
    IMPULSE_THRESHOLD_PERCENT,
    IMPULSE_WINDOW_SECONDS,
    ALIVE_NOTIFICATION_INTERVAL_MINUTES,
)
from telegram_notifier import send_message

# Отправляем стартовое сообщение
asyncio.run(send_message("✅ Бот запущен и ждёт импульс..."))

# Храним последние цены и время последнего alive-сообщения
price_history = []
last_alive_time = datetime.utcnow()

async def handle_socket():
    global last_alive_time
    url = "wss://stream.bybit.com/v5/public/spot"

    async with websockets.connect(url) as ws:
        await send_message(f"✅ Подключен к WebSocket по {SYMBOL}")

        # Подписка на сделки по BTCUSDT
        subscribe_msg = {
            "op": "subscribe",
            "args": [f"publicTrade.{SYMBOL}"]
        }
        await ws.send(json.dumps(subscribe_msg))

        while True:
            try:
                message = await asyncio.wait_for(ws.recv(), timeout=30)
                data = json.loads(message)

                if "data" in data and isinstance(data["data"], list):
                    for trade in data["data"]:
                        price = float(trade["p"])
                        timestamp = datetime.utcnow()
                        price_history.append((timestamp, price))

                # Удаляем старые записи
                cutoff = datetime.utcnow() - timedelta(seconds=IMPULSE_WINDOW_SECONDS)
                price_history[:] = [(ts, p) for ts, p in price_history if ts >= cutoff]

                # Анализ на импульс
                if len(price_history) >= 2:
                    oldest_price = price_history[0][1]
                    newest_price = price_history[-1][1]
                    change_percent = (newest_price - oldest_price) / oldest_price * 100

                    if abs(change_percent) >= IMPULSE_THRESHOLD_PERCENT:
                        direction = "вверх" if change_percent > 0 else "вниз"
                        await send_message(f"⚡ Импульс по BTC: {direction} {change_percent:.2f}% за {IMPULSE_WINDOW_SECONDS} сек")
                        last_alive_time = datetime.utcnow()

                # Alive сообщение раз в 30 минут (или заданное число минут)
                now = datetime.utcnow()
                if now - last_alive_time >= timedelta(minutes=ALIVE_NOTIFICATION_INTERVAL_MINUTES):
                    await send_message("✅ Бот жив, но импульсов пока нет.")
                    last_alive_time = now

            except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed):
                await send_message("⚠️ Потеря соединения с WebSocket. Переподключение...")
                break
            except Exception as e:
                await send_message(f"❌ Ошибка: {str(e)}")
                break

if __name__ == "__main__":
    asyncio.run(handle_socket())
