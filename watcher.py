"""
import requests
import pandas as pd
import time
import datetime
import os

# === Константы ===
SYMBOL = "BTCUSDT"
OTHER_SYMBOLS = ["ETHUSDT", "SOLUSDT", "AVAXUSDT", "XRPUSDT"]
INTERVAL = 5  # в минутах
ATR_PERIOD = 14
ATR_MULTIPLIER = 0.5
CORR_LOOKBACK = 20  # количество свечей для расчета корреляции

# === Переменные окружения ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# === Telegram ===
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Ошибка при отправке в Telegram: {e}")

# === Загрузка свечей с Bybit (фьючерсы) ===
def fetch_ohlcv(symbol):
    url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol={symbol}&interval={INTERVAL}&limit={ATR_PERIOD + CORR_LOOKBACK}"
    try:
        response = requests.get(url)
        data = response.json()
        if "result" not in data or "list" not in data["result"]:
            raise ValueError("Некорректный ответ от API")
        raw = data["result"]["list"]
        df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume", "_", "_", "_", "_"])
        df = df[["timestamp", "open", "high", "low", "close"]].astype(float)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')
        return df
    except Exception as e:
        print(f"Ошибка загрузки свечей {symbol}: {e}")
        return pd.DataFrame()

# === Расчёт ATR ===
def calculate_atr(df):
    df["H-L"] = df["high"] - df["low"]
    df["H-PC"] = abs(df["high"] - df["close"].shift(1))
    df["L-PC"] = abs(df["low"] - df["close"].shift(1))
    tr = df[["H-L", "H-PC", "L-PC"]].max(axis=1)
    atr = tr.rolling(ATR_PERIOD).mean().iloc[-1]
    return atr

# === Основная функция ===
def run_tracker():
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=1)  # UTC+1
    if now.hour < 7 or now.hour >= 24:
        send_telegram_message(f"⏸ Сканирование остановлено с 00:00 до 07:00 (Нидерланды)\nТекущее время: {now.strftime('%H:%M')}")
        return

    btc_df = fetch_ohlcv(SYMBOL)
    if btc_df.empty:
        return

    atr = calculate_atr(btc_df)
    last_candle = btc_df.iloc[-1]
    recent_change = last_candle["high"] - last_candle["low"]
    base_price = min(last_candle["open"], last_candle["close"])
    pct_change = (recent_change / base_price) * 100

    if recent_change >= atr * ATR_MULTIPLIER:
        message = f"<b>🚨 BTC Движение за {INTERVAL}m:</b>\n"
        message += f"Δ = {recent_change:.2f} USDT ({pct_change:.2f}%)\n"
        message += f"ATR = {atr:.2f}\n"

        # === Корреляции ===
        try:
            btc_returns = btc_df["close"].pct_change().dropna().iloc[-CORR_LOOKBACK:]
            for sym in OTHER_SYMBOLS:
                sym_df = fetch_ohlcv(sym)
                if sym_df.empty:
                    continue
                sym_returns = sym_df["close"].pct_change().dropna().iloc[-CORR_LOOKBACK:]
                if len(sym_returns) == len(btc_returns):
                    corr = btc_returns.corr(sym_returns)
                    message += f"🔗 {sym}: корреляция = {corr:.2f}\n"
        except Exception as e:
            message += f"\n⚠️ Ошибка расчёта корреляции: {e}\n"

        send_telegram_message(message)
        print(message)
    else:
        print(f"– Нет импульса: Δ = {recent_change:.4f} < {ATR_MULTIPLIER} × ATR = {atr:.4f}")

# === Цикл работы ===
while True:
    run_tracker()
    time.sleep(INTERVAL * 60)
