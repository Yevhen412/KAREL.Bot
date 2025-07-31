import asyncio
from ATR import calculate_atr
from Step import analyze_candle
from Lag import detect_lag
from Correlation import calculate_correlation
from Deal import simulate_trade
from AltFetcher import fetch_alt_candles
from Telegram import send_telegram_message

btc_symbol = "BTCUSDT"
alt_symbols = ["ETHUSDT", "SOLUSDT", "ADAUSDT", "AVAXUSDT"]

async def main():
    try:
        # Получаем ATR по BTC
        btc_atr = await calculate_atr()
        print(f"[BTC ATR]: {btc_atr:.2f}")

        # Получаем свечи BTC
    btc_df = await fetch_alt_candles(btc_symbol)
    delta, direction = await analyze_candle(btc_df, btc_atr)

    print(f"\n🟡 BTC ATR: {btc_atr:.2f}")
    dir_text = f"({direction})" if direction else ""
    print(f"🟢 Δ: {delta:.2f} {dir_text}")

    if delta < btc_atr * 0.5:
        print("⛔ Δ < 50% ATR — расчёт пропущен\n")
        return

    except Exception as e:
        print(f"❌ Ошибка в main(): {e}")
        
    # Проверка на импульс
        if delta >= btc_atr * 0.5:
            # Загружаем данные по альткоинам
            alt_data = {}
            for alt in alt_symbols:
                alt_df = await fetch_alt_candles(alt)
                alt_data[alt] = alt_df

            # Вычисляем корреляции
            correlations = calculate_correlation(btc_df, alt_data)
            print(f"[Корреляции]: {correlations}")

            # Проверяем лаг
            lagging_coins = detect_lag(btc_df, alt_data, alt_symbols)

            if lagging_coins:
                for coin in lagging_coins:
                    print(f"[ЛАГ]: {coin}")
                    simulate_trade(direction, coin, alt_data[coin])
            else:
                print("❌ Лаг не обнаружен")

        else:
            print("⏩ Δ меньше 50% ATR – пропускаем расчёт")

    except Exception as e:
        send_telegram_message(f"⚠️ Ошибка в run.py: {e}")
        print(f"Ошибка: {e}")

# Запуск
if __name__ == "__main__":
    asyncio.run(main())
