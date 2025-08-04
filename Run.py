"""
import asyncio
import time
from ATR import calculate_atr
from Step import fetch_btc_candles, analyze_candle
from AltFetcher import fetch_alt_candles_batch
from Correlation import calculate_correlation
from Deal import simulate_trade
from Telegram import send_telegram_message
from Start_stop import monitor_schedule  # Подключаем модуль расписания

btc_symbol = "BTCUSDT"
alt_symbols = ["ETHUSDT", "SOLUSDT", "ADAUSDT", "AVAXUSDT", "XRPUSDT"]

async def main_loop():
    while True:
        try:
            # Ждём открытия новой свечи
            now = time.time()
            wait = 300 - (now % 300)
            send_telegram_message(f"⏳ Ждём открытия новой свечи: {int(wait)} сек...")
            await asyncio.sleep(wait)

            # 1. Получаем ATR по BTC
            btc_atr = await calculate_atr()
            send_telegram_message(f"🟡 BTC ATR: {btc_atr:.2f}")

            # 2. Следим за текущей 5-мин свечой
            candle_reached_threshold = False
            direction = None
            delta = 0

            while True:
                btc_df = await fetch_btc_candles()
                delta, direction = await analyze_candle(btc_df, btc_atr)

                if direction:
                    send_telegram_message(f"🟢 Δ: {delta:.2f} — достигнуто 50% ATR")
                    candle_reached_threshold = True
                    break
                else:
                    await asyncio.sleep(10)

            if not candle_reached_threshold:
                send_telegram_message("⛔️ Свеча не достигла 50% ATR — переходим к следующей.")
                continue

            # 3. Получаем данные по альтам
            alt_data = await fetch_alt_candles_batch(alt_symbols)
            correlations = calculate_correlation(btc_df, alt_data)
            
            if delta >= btc_atr * 0.5:
            # Получаем альты
                alt_data = await fetch_alt_candles_batch(alt_symbols)
                correlations = calculate_correlation(btc_df, alt_data)

            # Фильтруем по высокой корреляции
                highly_correlated = [symbol for symbol, corr in correlations.items() if corr >= 0.8]

                if highly_correlated:
                    for symbol in highly_correlated:
                        simulate_trade(direction, symbol)
                else:
                    send_telegram_message("ℹ️ Высокой корреляции не обнаружено — сделка не открыта.")

        except Exception as e:
            send_telegram_message(f"❌ Ошибка в основном цикле: {e}")

        send_telegram_message("✅ Цикл завершён — ожидаем следующую 5-минутную свечу")

async def main():
    await asyncio.gather(
        main_loop(),
        monitor_schedule()
    )

if __name__ == "__main__":
    asyncio.run(main())
