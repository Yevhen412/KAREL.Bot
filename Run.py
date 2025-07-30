import asyncio
from ATR import fetch_asset_candles, calculate_atr
from Step import analyze_latest_candle
from Correlation import calculate_correlation

async def main():
    # Получаем данные по BTC (фьючерсы)
    btc_df = await fetch_asset_candles("BTCUSDT")
    atr = calculate_atr(btc_df)

    # Анализ последней свечи
    if not analyze_latest_candle(btc_df, atr):
        print("Свеча не прошла 50% ATR. Завершение.")
        return

    print("Свеча прошла 50% ATR. Рассчитываем корреляции...")

    # Получаем данные по другим активам (фьючерсы)
    eth_df = await fetch_asset_candles("ETHUSDT")
    sol_df = await fetch_asset_candles("SOLUSDT")
    ada_df = await fetch_asset_candles("ADAUSDT")
    avax_df = await fetch_asset_candles("AVAXUSDT")
    xrp_df = await fetch_asset_candles("XRPUSDT")
    pepe_df = await fetch_asset_candles("PEPEUSDT")

    # Формируем словарь активов
    other_assets = {
        "ETH": eth_df,
        "SOL": sol_df,
        "ADA": ada_df,
        "AVAX": avax_df,
        "XRP": xrp_df,
        "PEPE": pepe_df
    }

    # Считаем корреляции
    await calculate_correlation(btc_df, other_assets)

# Запускаем основной цикл
if __name__ == "__main__":
    asyncio.run(main())
