import asyncio
import pandas as pd
from ATR import calculate_atr
from Step import analyze_candle
import aiohttp

async def get_ohlcv():
    url = "https://api.bybit.com/v5/market/kline"
    params = {
        "category": "linear",
        "symbol": "BTCUSDT",
        "interval": "5",
        "limit": 100
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            data = await resp.json()
            ohlcv = data["result"]["list"]
            df = pd.DataFrame(ohlcv, columns=[
                "timestamp", "open", "high", "low", "close", "volume", "turnover"
            ])
            df["open"] = df["open"].astype(float)
            df["high"] = df["high"].astype(float)
            df["low"] = df["low"].astype(float)
            df["close"] = df["close"].astype(float)
            return df

async def main():
    print("=== RUNNING STRATEGY ===")
    
    # 1. Получаем свечи
    df = await get_ohlcv()

    # 2. Вычисляем ATR
    atr_value = await calculate_atr(df)

    # 3. Анализируем последнюю свечу
    match, candle_info = await analyze_candle(atr_value)

    # 4. Выводим результат
    if match:
        print("🔥 Свеча превысила 50% ATR:")
        print(candle_info)
    else:
        print("❄️ Нет импульса: свеча слишком слабая.")

# Запуск
if __name__ == "__main__":
    asyncio.run(main())
