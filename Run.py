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
            # 1. Расчёт ATR
            btc_atr = await calculate_atr()
            send_telegram_message(f"🟡 BTC ATR: {btc_atr:.2f}")

            # 2. Получаем текущую свечу
            btc_df = await fetch_btc_candles(btc_symbol)
            delta, direction = await analyze_candle(btc_df, btc_atr)
            send_telegram_message(f"🟢 Δ: {delta:.2f}")

            # 3. Проверка на импульс
            if delta < btc_atr * 0.5:
                send_telegram_message("⛔️ Δ < 50% ATR — расчёт пропущен")
            else:
                send_telegram_message("🚀 Δ >= 50% ATR — начинаем анализ альтов")

                # 4. Данные по альткоинам
                alt_data = await fetch_alt_candles_batch(alt_symbols)
                send_telegram_message(f"📊 Получены данные по альтам: {list(alt_data.keys())}")

                # 5. Расчёт корреляции
                correlations = calculate_correlation(btc_df, alt_data)
                send_telegram_message(f"📈 Корреляции: {correlations}")

                # 6. Анализ лага
                lagging_coins = detect_lag(btc_df, alt_data, correlations)
                if lagging_coins:
                    send_telegram_message(f"🐌 Обнаружен лаг у: {lagging_coins}")
                    for coin in lagging_coins:
                        simulate_trade(direction, coin)
                        send_telegram_message(f"💰 Симулирована сделка по {coin} в направлении {direction}")
                else:
                    send_telegram_message("🔕 Лаг не обнаружен — сделка не совершена")

        except Exception as e:
            send_telegram_message(f"❌ Ошибка в основном цикле: {e}")

        # 7. Ждём до начала следующей свечи
        now = time.time()
        next_candle = 300 - (now % 300)
        send_telegram_message("✅ Цикл завершён — ожидаем следующую 5-минутную свечу")
        await asyncio.sleep(next_candle)

if __name__ == "__main__":
    asyncio.run(main())
