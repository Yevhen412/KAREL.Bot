import asyncio
import time
from ATR import calculate_atr
from Step import fetch_btc_candles, analyze_candle
from Deal import simulate_trade
from Telegram import send_telegram_message
from Start_stop import monitor_schedule  # ⬅️ Подключаем планировщик времени

btc_symbol = "BTCUSDT"

async def main():
    # Запускаем мониторинг времени в фоновом режиме
    asyncio.create_task(monitor_schedule())

    while True:
        try:
            # Ждём открытия новой свечи
            now = time.time()
            wait = 300 - (now % 300)
            send_telegram_message(f"⏳ Ждём открытия новой свечи: {int(wait)} сек...")
            await asyncio.sleep(wait)

            # 1. Расчёт ATR
            btc_atr = await calculate_atr()
            send_telegram_message(f"🟡 BTC ATR: {btc_atr:.2f}")

            # 2. Наблюдение за текущей 5-мин свечой
            delta = 0
            direction = None

            while True:
                btc_df = await fetch_btc_candles()
                delta, direction = await analyze_candle(btc_df, btc_atr)

                if delta >= 0.25 * btc_atr:
                    send_telegram_message(f"📈 Δ достиг 25% ATR — открытие сделки")
                    await simulate_trade(direction, delta, btc_atr)  # ⬅️ await обязательно!
                    break
                else:
                    await asyncio.sleep(10)

        except Exception as e:
            send_telegram_message(f"❌ Ошибка в основном цикле: {e}")

        send_telegram_message("✅ Цикл завершён — ожидание следующей свечи")

if __name__ == "__main__":
    asyncio.run(main())
