import requests
import pandas as pd
import time

def get_recent_candles(symbol: str, interval: str = "5", limit: int = 100):
    url = "https://api.bybit.com/v5/market/kline"
    params = {
        "category": "linear",  # фьючерсы
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
    }
    response = requests.get(url, params=params)
    response.raise_for_status()

    raw = response.json()["result"]["list"]
    df = pd.DataFrame(raw, columns=[
        "timestamp", "open", "high", "low", "close",
        "volume", "turnover"
    ])

    # Приводим типы данных
    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["close"] = df["close"].astype(float)
    df["volume"] = df["volume"].astype(float)
    df["turnover"] = df["turnover"].astype(float)

    df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')
    return df[::-1].reset_index(drop=True)  # от старой к новой
