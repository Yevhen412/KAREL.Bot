import aiohttp
import pandas as pd

async def fetch_asset_candles(symbol: str):
    url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol={symbol}&interval=5&limit=200"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            df = pd.DataFrame(data["result"]["list"], columns=[
                "timestamp", "open", "high", "low", "close", "volume", "turnover"
            ])
            df = df.astype(float)
            df["timestamp"] = pd.to_datetime(df["timestamp"].astype(float), unit='ms')
            return df

def calculate_atr(df, period=12):
    df["H-L"] = df["high"] - df["low"]
    df["H-PC"] = abs(df["high"] - df["close"].shift(1))
    df["L-PC"] = abs(df["low"] - df["close"].shift(1))
    tr = df[["H-L", "H-PC", "L-PC"]].max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr.iloc[-1]
