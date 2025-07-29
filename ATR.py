import aiohttp
import asyncio
import pandas as pd

BYBIT_URL = "https://api.bybit.com/v5/market/kline"

async def fetch_btc_candles():
    params = {
        "category": "linear",
        "symbol": "BTCUSDT",
        "interval": "5",
        "limit": 12
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(BYBIT_URL, params=params) as resp:
            data = await resp.json()
            if data["retCode"] != 0:
                raise Exception("Failed to fetch candles:", data)
            candles = data["result"]["list"]
            df = pd.DataFrame(candles, columns=[
                "timestamp", "open", "high", "low", "close", "volume", "turnover"
            ])
            df = df.astype({
                "high": "float", "low": "float", "close": "float"
            })
            return df

def calculate_atr(df: pd.DataFrame) -> float:
    df["high-low"] = df["high"] - df["low"]
    df["high-close"] = abs(df["high"] - df["close"].shift(1))
    df["low-close"] = abs(df["low"] - df["close"].shift(1))
    df["tr"] = df[["high-low", "high-close", "low-close"]].max(axis=1)
    atr = df["tr"].rolling(window=12).mean().iloc[-1]
    return round(atr, 2)

async def get_current_atr():
    df = await fetch_btc_candles()
    return calculate_atr(df)
