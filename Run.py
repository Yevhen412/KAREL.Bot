import asyncio
import time
from ATR import calculate_atr
from Step import fetch_btc_candles, analyze_candle
from AltFetcher import fetch_alt_candles_batch
from Correlation import calculate_correlation
from Lag import detect_lag
from Deal import simulate_trade
from Telegram import send_telegram_message

btc_symbol = "BTCUSDT"
alt_symbols = ["ETHUSDT", "SOLUSDT", "ADAUSDT", "AVAXUSDT", "XRPUSDT"]

async def main():
    while True:
        try:
            # 1. Ждём открытия новой свечи
            now = time.time()
            seconds_to_next_candle = 300 - (now % 300)
            send_telegram_message(f"⏳ Ждём открытия новой свечи: {int(seconds_to_next_candle)} сек...")
            await asyncio.sleep(seconds_to_next_candle)

            # 2. Получаем ATR
            btc_atr = await calculate_atr()
            send_telegram_message(f"🟡 BTC ATR: {btc_atr:.2f}")

            # 3. Следим за новой 5-мин свечой в реальном времени (до её закрытия)
            candle_reached_threshold = False
            candle_start_time = time.time()
            while time.time() - candle_start_time < 300:
                btc_df = await fetch_btc_candles(btc_symbol)
                delta, direction = await analyze_candle(btc_df, btc_atr)

                if direction:
                    send_telegram_message(f"🟢 Δ: {delta:.2f} — достигнуто 50% ATR")
                    candle_reached_threshold = True
                    break  # Переходим к анализу альтов
                else:
                    await asyncio.sleep(10)  # Проверяем дельту каждые 10 секунд

            if not candle_reached_threshold:
                send_telegram_message("⛔️ Свеча не достигла 50% ATR — переходим к следующей.")
                continue

            # 4. Работаем с альтами
            alt_data = await fetch_alt_candles_batch(alt_symbols)
            correlations = calculate_correlation(btc_df, alt_data)
            lagging_coins = detect_lag(btc_df, alt_data, correlations)

            # 5. Сделка
            if lagging_coins:
                for coin in lagging_coins:
                    simulate_trade(direction, coin)

        except Exception as e:
            send_telegram_message(f"❌ Ошибка в основном цикле: {e}")

if __name__ == "__main__":
    asyncio.run(main())
