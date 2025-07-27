import asyncio
import websockets
import json
import time
from telegram_notifier import send_message

IMPULSE_THRESHOLD = 0.3  # Процентное изменение, считающееся импульсом
impulse_detected = False
last_impulse_time = 0

async def check_keepalive():
    while True:
        await asyncio.sleep(1800)  # 30 минут
        if not impulse_detected:
            await send_message("⏳ Бот активен. Ждём импульс по BTCUSDT...")

async def listen_to_websocket():
    global impulse_detected, last_impulse_time

    url = "wss://stream.bybit.com/v5/public/spot"
    async with websockets.connect(url) as ws:
        await send_message("✅ Бот запущен и ждёт импульс...")
        await ws.send(json.dumps({
            "op": "subscribe",
            "args": ["publicTrade.BTCUSDT"]
        }))
        await send_message("✅ Подключен к WebSocket по BTCUSDT")

        prices = []
        timestamps = []

        async for message in ws:
            data = json.loads(message)
            if 'data' in data:
                trades = data['data']
                for trade in trades:
                    price = float(trade['p'])
                    ts = trade['T'] / 1000  # миллисекунды → секунды

                    prices.append(price)
                    timestamps.append(ts)

                    # Удаляем устаревшие записи (старше 10 секунд)
                    while timestamps and (ts - timestamps[0]) > 10:
                        timestamps.pop(0)
                        prices.pop(0)

                    # Проверка импульса
                    if len(prices) >= 2:
                        price_past = prices[0]
                        price_now = prices[-1]
                        percent_change = ((price_now - price_past) / price_past) * 100

                        if abs(percent_change) >= IMPULSE_THRESHOLD:
                            now = time.time()
                            if now - last_impulse_time > 10:
                                last_impulse_time = now
                                impulse_detected = True
                                direction = "выросла" if percent_change > 0 else "упала"
                                emoji = "🚀" if percent_change > 0 else "📉"
                                msg = (
                                    f"{emoji} Импульс по BTCUSDT: цена {direction} на "
                                    f"{abs(percent_change):.2f}% за 10 секунд!"
                                )
                                await send_message(msg)

async def main():
    await asyncio.gather(
        listen_to_websocket(),
        check_keepalive()
    )

if __name__ == "__main__":
    asyncio.run(main())
