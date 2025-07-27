import asyncio
import websockets
import json
import time
from telegram_notifier import send_message

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

        async for message in ws:
            data = json.loads(message)
            if 'data' in data:
                trades = data['data']
                prices = [float(t['p']) for t in trades]
                if len(prices) >= 2:
                    percent_change = abs(prices[-1] - prices[0]) / prices[0] * 100
                    if percent_change >= 0.3:
                        now = time.time()
                        if now - last_impulse_time > 10:
                            last_impulse_time = now
                            impulse_detected = True
                            await send_message(f"🚀 Обнаружен импульс по BTCUSDT: {percent_change:.2f}%")

async def main():
    await asyncio.gather(
        listen_to_websocket(),
        check_keepalive()
    )

if __name__ == "__main__":
    asyncio.run(main())
