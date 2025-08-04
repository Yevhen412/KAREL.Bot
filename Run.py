import asyncio
import time
from ATR import calculate_atr
from Step import fetch_btc_candles, analyze_candle
from Telegram import send_telegram_message
from Deal import simulate_trade

btc_symbol = "BTCUSDT"

async def main():
    while True:
        try:
            # 1. Ждём начала новой свечи
            now = time.time()
            wait = 300 - (now % 300)
            send_telegram_message(f"⏳ Ожидание открытия новой свечи: {int(wait)} сек...")
            await asyncio.sleep(wait)

            # 2. Получаем ATR по BTC
            btc_atr = await calculate_atr()
            send_telegram_message(f"🟡 BTC ATR: {btc_atr:.2f}")

            # 3. Следим за текущей свечой — проверка каждые 10 секунд
            candle_triggered = False
            direction = None
            entry_price = 0
            delta = 0

            for _ in range(30):  # 5 минут / 10 сек = 30 попыток
                btc_df = await fetch_btc_candles()
                delta, direction, entry_price = await analyze_candle(btc_df, btc_atr)

                if delta >= 0.25 * btc_atr and direction:
                    send_telegram_message(f"🚀 Δ достигла 25% ATR: {delta:.2f}")
                    candle_triggered = True
                    break
                await asyncio.sleep(10)

            if candle_triggered:
                simulate_trade(direction, entry_price, btc_atr)
            else:
                send_telegram_message("⛔️ Δ < 25% ATR — сделка не открыта.")

        except Exception as e:
            send_telegram_message(f"❌ Ошибка в основном цикле: {e}")

        # Завершение цикла
        send_telegram_message("✅ Цикл завершён — ждём следующую 5-минутную свечу")

if __name__ == "__main__":
    asyncio.run(main())
