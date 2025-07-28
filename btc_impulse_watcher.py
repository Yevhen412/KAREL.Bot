import requests
import pandas as pd
import time
from datetime import datetime, timedelta
import pytz
import telegram

# === НАСТРОЙКИ ===
SYMBOL = "BTCUSDT"
ALTCOINS = ["ETHUSDT", "SOLUSDT", "AVAXUSDT", "XRPUSDT"]
INTERVAL = "5"
LIMIT = 100
ATR_PERIOD = 14
ATR_MULTIPLIER = 0.5
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


# === ФУНКЦИИ ===

def fetch_ohlcv(symbol):
    url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol={symbol}&interval={INTERVAL}&limit={LIMIT}"
    r = requests.get(url)
    data = r.json()["result"]["list"]
    df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
    df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].astype(float)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df

def calculate_atr(df):
    df["H-L"] = df["high"] - df["low"]
    df["H-PC"] = abs(df["high"] - df["close"].shift(1))
    df["L-PC"] = abs(df["low"] - df["close"].shift(1))
    df["TR"] = df[["H-L", "H-PC", "L-PC"]].max(axis=1)
    atr = df["TR"].rolling(ATR_PERIOD).mean().iloc[-1]
    return atr

def get_utc_plus1_now():
    return datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(pytz.timezone("Europe/Amsterdam"))

def send_telegram_message(text):
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode="HTML")

def run_tracker():
    now = get_utc_plus1_now()
    if now.hour < 7 or now.hour >= 24:
        send_telegram_message(f"⏸ Скрипт приостановлен до 07:00 по NL (сейчас {now.strftime('%H:%M')})")
        return

    btc_df = fetch_ohlcv(SYMBOL)
    atr = calculate_atr(btc_df)
    last_candle = btc_df.iloc[-1]
    recent_change = last_candle["high"] - last_candle["low"]

    if recent_change >= atr * ATR_MULTIPLIER:
        pct_change = (recent_change / last_candle["close"]) * 100
        message = f"<b>🚨 BTC Движение за {INTERVAL}m:</b>\n"
        message += f"Δ = {recent_change:.2f} USDT ({pct_change:.2f}%)\n"
        message += f"ATR = {atr:.2f}\n"

        # Корреляции
        for alt in ALTCOINS:
            alt_df = fetch_ohlcv(alt)
            corr = btc_df["close"].corr(alt_df["close"])
            message += f"🔗 {alt}: корреляция = {corr:.2f}\n"

        send_telegram_message(message)

# === ЦИКЛ ===

if __name__ == "__main__":
    while True:
        try:
            run_tracker()
        except Exception as e:
            send_telegram_message(f"⚠️ Ошибка: {e}")
        time.sleep(300)
