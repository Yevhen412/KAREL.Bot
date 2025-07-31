import asyncio
from ATR import calculate_atr
from Step import analyze_candle
from AltFetcher import fetch_alt_candles
from Correlation import calculate_correlation
from Lag import detect_lag
from Deal import simulate_trade

btc_symbol = "BTCUSDT"
alt_symbols = ["ETHUSDT", "SOLUSDT", "ADAUSDT", "AVAXUSDT", "XRPUSDT"]

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
            print("⛔️ Δ < 50% ATR — расчёт пропущен\n")
            return

        # Проверка на импульс
        if delta >= btc_atr * 0.5:
            # Загружаем данные по альткоинам
            alt_data = {}
            for alt in alt_symbols:
                alt_df = await fetch_alt_candles(alt)
                alt_data[alt] = alt_df

            # Вычисляем корреляции
            correlations = calculate_correlations(btc_df, alt_data)
            print(f"[Корреляции]: {correlations}")

            # Проверяем лаг
            lagging_coins = detect_lag(btc_df, alt_data, correlations)
            if lagging_coins:
                for coin in lagging_coins:
                    print(f"[ЛАГ]: {coin}")
                    simulate_trade(direction, coin)
            else:
                print("❌ Лаг не обнаружен")

    except Exception as e:
        print(f"❌ Ошибка в main(): {e}")

if __name__ == "__main__":
    asyncio.run(main())
