import asyncio
from ATR import fetch_btc_candles, calculate_attr
from Step import analyze_candle
from Correlation import calculate_correlation

async def main():
    print("=== RUNNING STRATEGY ===")

    # Получение свечей BTC
    df = await fetch_btc_candles()

    # Расчёт ATR
    atr_value = calculate_attr(df)
    print(f"ATR = {atr_value:.2f} USDT")

    # Анализ текущей 5-минутной свечи
    candle_passed_half_attr = await analyze_candle(df, atr_value)

    # Если свеча прошла более 50% ATR, запускаем корреляцию
    if candle_passed_half_attr:
        print("Свеча превысила 50% ATR. Запуск расчёта корреляции...")
        other_assets = ["ETHUSDT", "SOLUSDT", "ADAUSDT", "AVAXUSDT", "XRPUSDT", "PEPEUSDT"]
        await calculate_correlation(df, other_assets)
    else:
        print("Свеча не превысила 50% ATR. Завершаем анализ.")

# Запуск
if __name__ == "__main__":
    asyncio.run(main())
