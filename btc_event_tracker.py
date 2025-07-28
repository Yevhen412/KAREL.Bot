import time
import requests
import pandas as pd
import numpy as np
import os
from datetime import datetime

# --- Настройки ---
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT"]
INTERVAL = "5m"
LOOKBACK = 50
ATR_PERIOD = 14
CORR_THRESHOLD = 0.85
ATR_MULTIPLIER = 0.5
BYBIT_BASE_URL = "https://api.bybit.com"

# --- Переменные окружения (из Railway или .env) ---
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- Telegram Notifier ---
def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if not response.ok:
            print(f"[Telegram] Ошибка: {response.text}")
    except Exception as e:
        print(f"[Telegram] Исключение: {e}")

# --- Получение свечей ---
def get_klines(symbol: str, interval: str, limit: int = LOOKBACK):
    url = f"{BYBIT_BASE_URL}/v5/market/kline"
    params = {
        "category": "spot",
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
    }
    response = requests.get(url, params=params)
    data = response.json()

    if data["retCode"] != 0 or "result" not in data:
        print(f"[!] Ошибка получения свечей для {symbol}")
        return None

    df = pd.DataFrame(data["result"]["list"], columns=["timestamp", "open", "high", "low", "close", "volume", "_"])
    df = df[["timestamp", "open", "high", "low", "close", "volume"]]
    df = df.astype(float)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')
    df.set_index("timestamp", inplace=True)
    return df

# --- Расчёт ATR ---
def calculate_atr(df: pd.DataFrame, period: int = ATR_PERIOD):
    df["H-L"] = df["high"] - df["low"]
    df["H-PC"] = abs(df["high"] - df["close"].shift(1))
    df["L-PC"] = abs(df["low"] - df["close"].shift(1))
    df["TR"] = df[["H-L", "H-PC", "L-PC"]].max(axis=1)
    df["ATR"] = df["TR"].rolling(window=period).mean()
    return df["ATR"].iloc[-1]

# --- Расчёт корреляции ---
def compute_correlation(base_df, target_df):
    merged = pd.concat([base_df["close"], target_df["close"]], axis=1, keys=["base", "target"]).dropna()
    if len(merged) < 2:
        return 0
    corr = np.corrcoef(merged["base"], merged["target"])[0, 1]
    return corr

# --- Основной процесс ---
def run_tracker():
    while True:
        print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] Проверка движения BTC...")

        btc_df = get_klines("BTCUSDT", INTERVAL)
        if btc_df is None:
            time.sleep(30)
            continue

        atr = calculate_atr(btc_df)
        recent_change = abs(btc_df["close"].iloc[-1] - btc_df["close"].iloc[-2])

        if recent_change >= atr * ATR_MULTIPLIER:
            pct_change = (recent_change / btc_df["close"].iloc[-2]) * 100
            message = f"<b>🚨 BTC Движение за 5m:</b>\n"
            message += f"Δ = {recent_change:.2f} USDT ({pct_change:.2f}%)\n"
            message += f"ATR = {atr:.2f}\n"

            for symbol in SYMBOLS:
                if symbol == "BTCUSDT":
                    continue

                df = get_klines(symbol, INTERVAL)
                if df is None:
                    continue

                corr = compute_correlation(btc_df, df)
                if corr >= CORR_THRESHOLD:
                    message += f"🔗 <b>{symbol}</b>: корреляция = {corr:.2f}\n"

            send_message(message)
            print("✅ Сообщение отправлено в Telegram")
        else:
            print(f"— Нет импульса: Δ = {recent_change:.4f} < 0.5 × ATR = {atr:.4f}")

        time.sleep(300)  # каждые 5 минут

# --- Запуск ---
if __name__ == "__main__":
    run_tracker()
