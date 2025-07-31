import asyncio
from ATR import fetch_asset_candles, calculate_atr
from Step import analyze_candle
from Correlation import calculate_correlation
from Lag import detect_lag

async def main():
    print("=== RUNNING STRATEGY ===")

    # Получение свечей BTC
    btc_df = await fetch_asset_candles("BTCUSDT")

    # Расчёт ATR
    atr = calculate_atr(btc_df)
    print(f"ATR = {atr:.2f} USDT")

    # Анализ текущей 5-минутной свечи
    if not await analyze_candle(btc_df, atr):
        print("Свеча не превысила 50% ATR.")
        return
    print("Свеча превысила 50% ATR. Запуск расчёта корреляции...")

    # Получение данных по остальным монетам
    other_symbols = ["ETHUSDT", "SOLUSDT", "ADAUSDT", "AVAXUSDT", "XRPUSDT"]
    other_assets = {}
    for symbol in other_symbols:
        other_assets[symbol] = await fetch_asset_candles(symbol)

    # Расчёт корреляции
    correlation_results = calculate_correlation(btc_df, other_assets)
    print("Результаты корреляции:")
    for symbol, value in correlation_results.items():
        print(f"{symbol}: {value}")

    # Выбор топ-2 по корреляции
    top_symbols = sorted(correlation_results, key=correlation_results.get, reverse=True)[:2]

    # Поиск лага
    lagging_symbol = detect_lag(btc_df, other_assets, top_symbols)
    if lagging_symbol:
        print(f"Готовность к сделке по монете: {lagging_symbol}")
        # Здесь в будущем будет блок сделки
    else:
        print("Переход к ожиданию следующего сигнала...")

# Запуск
if __name__ == "__main__":
    asyncio.run(main())
