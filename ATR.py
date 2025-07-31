import pandas as pd
import time
import aiohttp

async def fetch_btc_candles(interval="5", limit=12):
    url = "https://api.bybit.com/v5/market/kline"
    category = "linear"
    symbol = "BTCUSDT"
    end = int(time.time() * 1000)
    start = end - (limit * int(interval) * 60 * 1000)

    params = {
        "category": category,
        "symbol": symbol,
        "interval": interval,
        "start": start,
        "end": end,
        "limit": limit
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            data = await resp.json()

    if "result" not in data or "list" not in data["result"]:
        raise ValueError(f"❌ Ошибка получения данных BTC: {data}")

    df = pd.DataFrame(data["result"]["list"])
    df.columns = ["timestamp", "open", "high", "low", "close", "volume", "turnover"]
    df = df[["timestamp", "open", "high", "low", "close"]]
    df = df.astype({"open": float, "high": float, "low": float, "close": float})
    df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="ms")
    df.sort_values("timestamp", inplace=True)

    return df

async def calculate_atr():
    df = await fetch_btc_candles()
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["close"] = df["close"].astype(float)

    df["previous_close"] = df["close"].shift(1)
    df["tr"] = df[["high", "low", "previous_close"]].apply(
        lambda row: max(row["high"] - row["low"], abs(row["high"] - row["previous_close"]), abs(row["low"] - row["previous_close"])),
        axis=1
    )
    atr = df["tr"].mean()
    return round(atr, 2)
