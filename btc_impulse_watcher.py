import asyncio
import websockets
import json
import time
from collections import deque

SYMBOL = "BTCUSDT"
WINDOW_SECONDS = 10
THRESHOLD_PERCENT = 0.3
HEARTBEAT_INTERVAL = 600  # 10 минут

price_window = deque()
last_heartbeat = time.time()

async def watch_btc():
    url = "wss://stream.bybit.com/v5/public/linear"

    async with websockets.connect(url) as ws:
        subscribe_msg = {
            "op": "subscribe",
            "args": [f"publicTrade.{SYMBOL}"]
        }
        await ws.send(json.dumps(subscribe_msg))
        print(f"📡 Подключено к WebSocket для {SYMBOL}... Ожидание импульса...")

        while True:
            try:
                message = await ws.recv()
                data = json.loads(message)

                if "data" in data and isinstance(data["data"], list):
                    trade = data["data"][0]
                    price = float(trade["p"])
                    ts = int(trade["T"]) // 1000  # секунды

                    price_window.append((ts, price))
                    while price_window and ts - price_window[0][0] > WINDOW_SECONDS:
                        price_window.popleft()

                    # Расчёт импульса
                    if len(price_window) >= 2:
                        old_price = price_window[0][1]
                        change = (price - old_price) / old_price * 100
                        if abs(change) >= THRESHOLD_PERCENT:
                            direction = "📈 рост" if change > 0 else "📉 падение"
                            print(f"\n🚨 Импульс BTC: {direction} на {change:.2f}% за {WINDOW_SECONDS} сек (цена: {old_price:.2f} → {price:.2f})\n")
                            price_window.clear()
                            last_heartbeat = time.time()  # сбросим таймер

                    # Проверка heartbeat
                    if time.time() - last_heartbeat > HEARTBEAT_INTERVAL:
                        print(f"⌛ Бот работает. Ожидание импульса... Текущая цена: {price}")
                        last_heartbeat = time.time()

            except Exception as e:
                print("Ошибка:", e)
                await asyncio.sleep(5)

asyncio.run(watch_btc())