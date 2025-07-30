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
    try:
        print("=== RUNNING STRATEGY ===")
        df = await get_ohlcv()
        print("✅ OHLCV data loaded")

        atr_value = calculate_atr(df)
        print(f"✅ ATR calculated: {atr_value:.4f}")

        match, info = await analyze_candle(atr_value)

        if match:
            print("🔥 Импульс обнаружен:")
            print(info)
        else:
            print("❄️ Импульса нет.")

    except Exception as e:
        print("❌ ERROR in main():", str(e))

# Запуск
if __name__ == "__main__":
    asyncio.run(main())
