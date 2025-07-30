import aiohttp
import pandas as pd

# Загрузка свечей 5м по указанному символу
async def fetch_asset_candles(symbol: str):
    url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol={symbol}&interval=5&limit=100"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            candles = data["result"]["list"]

            df = pd.DataFrame(candles, columns=[
                "timestamp", "open", "high", "low", "close", "volume", "turnover"
            ])

            df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')
            df = df.astype({
                "open": "float",
                "high": "float",
                "low": "float",
                "close": "float",
            })

            return df

# Расчёт ATR на основе последних 12 свечей
def calculate_atr(df):
    df["high_low"] = df["high"] - df["low"]
    df["high_close"] = (df["high"] - df["close"].shift()).abs()
    df["low_close"] = (df["low"] - df["close"].shift()).abs()
    df["tr"] = df[["high_low", "high_close", "low_close"]].max(axis=1)
    atr = df["tr"].rolling(window=12).mean().iloc[-1]
    return atr
