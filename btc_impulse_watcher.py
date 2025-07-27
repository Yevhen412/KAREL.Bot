import asyncio
import websockets
import json
import time
from datetime import datetime
from config import (
    SYMBOL,
    IMPULSE_THRESHOLD_PERCENT,
    IMPULSE_WINDOW_SECONDS,
    ALIVE_NOTIFICATION_INTERVAL_MINUTES
)
from telegram_notifier import send_message
send_message("✅ Бот запущен и ждёт импульс")

# Храним последние цены и время последнего alive-сообщения
price_history = []
last_alive_time = 0

async def handle_socket():
    global last_alive_time
    url = "wss://stream.bybit.com/v5/public/spot"

    async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
        # Подписка на сделки по BTC
        payload = {
            "op": "subscribe",
            "args": [f"publicTrade.{SYMBOL}"]
        }
        await ws.send(json.dumps(payload))
        print("✅ WebSocket подключен, ожидание импульса...")

        while True:
            try:
                message = await ws.recv()
                data = json.loads(message)

                if "data" not in data:
                    continue

                trades = data["data"]
                for trade in trades:
                    price = float(trade["p"])
                    timestamp = int(trade["T"]) / 1000  # ms to s

                    # Добавляем в историю
                    price_history.append((timestamp, price))

                    # Удаляем старые записи
                    cutoff = timestamp - IMPULSE_WINDOW_SECONDS
                    price_history[:] = [(t, p) for t, p in price_history if t >= cutoff]

                    # Проверка на импульс
                    if price_history:
                        start_price = price_history[0][1]
                        percent_change = (price - start_price) / start_price * 100

                        if abs(percent_change) >= IMPULSE_THRESHOLD_PERCENT:
                            direction = "🔼 вверх" if percent_change > 0 else "🔽 вниз"
                            message = (
                                f"🚨 BTC импульс {direction} на {percent_change:.2f}% "
                                f"за {IMPULSE_WINDOW_SECONDS} сек. (цена: {price:.2f})"
                            )
                            print(message)
                            send_telegram_message(message)

                            # Очищаем историю, чтобы не спамить повторно
                            price_history.clear()

                    # Раз в N минут — сообщение, что бот жив
                    now = time.time()
                    if now - last_alive_time > ALIVE_NOTIFICATION_INTERVAL_MINUTES * 60:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        send_telegram_message(f"🤖 Бот активен. {timestamp}")
                        last_alive_time = now

            except Exception as e:
                print(f"❌ Ошибка WebSocket: {e}")
                await asyncio.sleep(5)  # Подождать перед переподключением

if __name__ == "__main__":
    asyncio.run(handle_socket())
