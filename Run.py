import asyncio
from ATR import calculate_atr
from Step import analyze_candle
from Correlation import calculate_correlation
from Lag import detect_lag
from Deal import simulate_trade
from Telegram import send_telegram_message
from fetch_assets import fetch_alt_candles

btc_symbol = "BTCUSDT"
alt_symbols = ["ETHUSDT", "SOLUSDT", "ADAUSDT", "AVAXUSDT", "XRPUSDT"]

try:
    # Получаем ATR по BTC
    btc_atr = await calculate_atr()
    print(f"[BTC ATR]: {btc_atr:.2f}")

    # Отладка перед получением свечей
    print("🔄 Запрашиваем свечи BTC...")

    # Анализ последней свечи BTC
    btc_df = await fetch_alt_candles(btc_symbol)
    print(f"✅ Получены данные BTC: {btc_df.tail()}")

    delta, direction = analyze_current_step(btc_df)
    print(f"[BTC Δ]: {delta:.2f} → направление: {direction}")

    if delta >= btc_atr * 0.5:
        print("🚀 Δ превышает 50% ATR — продолжаем")

        # Загружаем данные по альтам
        alt_data = {}
        for alt in alt_symbols:
            print(f"📥 Загружаем данные по {alt}...")
            alt_df = await fetch_alt_candles(alt)
            alt_data[alt] = alt_df

        # Вычисляем корреляции
        correlations = calculate_correlation(btc_df, alt_data)
        print(f"[Корреляции]: {correlations}")

        # Проверяем лаг
        lagging_coins = detect_lag(btc_df, alt_data, correlations)
        if lagging_coins:
            for coin in lagging_coins:
                print(f"[ЛАГ]: {coin}")
                await simulate_trade(btc_df, alt_data[coin], direction)
        else:
            print("❌ Лаг не обнаружен")

    else:
        print("🕒 Δ меньше 50% ATR — пропускаем расчёт")

except Exception as e:
    print(f"❌ Ошибка до анализа свечи: {e}")
    send_telegram_message(f"⚠️ Ошибка в run.py: {e}")
