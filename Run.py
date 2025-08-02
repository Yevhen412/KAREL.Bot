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
    send_telegram_message("🔁 Контейнер перезапущен")

    while True:
        try:
            # 1. Получаем ATR
            try:
                btc_atr = await calculate_atr()
                send_telegram_message(f"🟡 BTC ATR: {btc_atr:.2f}")
            except Exception as e:
                send_telegram_message(f"❌ Ошибка при расчёте ATR: {e}")
                continue

            # 2. Получаем свечу BTC
            try:
                btc_df = await fetch_btc_candles(btc_symbol)
                delta, direction = await analyze_candle(btc_df, btc_atr)
                send_telegram_message(f"🟢 Δ: {delta:.2f}")
            except Exception as e:
                send_telegram_message(f"❌ Ошибка при анализе свечи BTC: {e}")
                continue

            # 3. Проверка на силу импульса
            if delta < btc_atr * 0.5:
                send_telegram_message("⛔️ Δ < 50% ATR — расчёт пропущен")
            else:
                try:
                    alt_data = await fetch_alt_candles_batch(alt_symbols)
                    correlations = calculate_correlation(btc_df, alt_data)
                    lagging_coins = detect_lag(btc_df, alt_data, correlations)
                except Exception as e:
                    send_telegram_message(f"❌ Ошибка при обработке альтов: {e}")
                    continue

                if lagging_coins:
                    try:
                        for coin in lagging_coins:
                            simulate_trade(direction, coin)
                    except Exception as e:
                        send_telegram_message(f"❌ Ошибка при симуляции сделки: {e}")
                else:
                    send_telegram_message("ℹ️ Лаг не обнаружен. Сделка не будет открыта.")

        except Exception as e:
            send_telegram_message(f"🚨 Ошибка в основном цикле: {e}")

        # Пауза до начала следующей свечи
        now = time.time()
        next_candle = 300 - (now % 300)
        send_telegram_message("✅ Цикл завершён — ожидаем следующую 5-минутную свечу")
        await asyncio.sleep(next_candle)

if __name__ == "__main__":
    asyncio.run(main())
