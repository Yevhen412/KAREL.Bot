import time
from decimal import Decimal
import requests
from Telegram import send_telegram_message

TRADE_AMOUNT = Decimal("200")
LEVERAGE = 3
TARGET_NET_PROFIT = Decimal("0.01")
TAKER_FEE = Decimal("0.001")  # 0.1%
PAIR = "BTCUSDT"

last_trade_time = 0
in_trade = False

def get_current_price():
    url = f"https://api.bybit.com/v5/market/tickers?category=linear&symbol={PAIR}"
    try:
        response = requests.get(url, timeout=2)
        data = response.json()
        price = Decimal(data["result"]["list"][0]["lastPrice"])
        return price
    except Exception as e:
        print("Ошибка при получении цены:", e)
        return None

def simulate_trade(entry_price):
    global last_trade_time

    position_value = TRADE_AMOUNT * LEVERAGE
    total_fees = (entry_price * position_value) * TAKER_FEE * 2  # вход + выход
    required_exit_price = entry_price + ((TARGET_NET_PROFIT + total_fees) / position_value)

    # Ждём 0.4 секунды и снова смотрим цену
    time.sleep(0.4)
    exit_price = get_current_price()
    if exit_price is None:
        return

    if exit_price >= required_exit_price:
        net = (exit_price - entry_price) * position_value - total_fees
        msg = (
            f"✅ Виртуальная сделка завершена:\n"
            f"Пара: {PAIR}\n"
            f"Buy: {entry_price:.2f}\n"
            f"Sell: {exit_price:.2f}\n"
            f"Net: {net:.5f} USDT"
        )
        print(msg)
        send_telegram_message(msg)
        last_trade_time = time.time()

def run_micro_scalper():
    global in_trade, last_trade_time

    print("📈 Скальпер запущен.")
    send_telegram_message("📈 Скальпер запущен и ждёт условия...")

    while True:
        now = time.time()
        if in_trade or now - last_trade_time < 1:
            time.sleep(0.1)
            continue

        price = get_current_price()
        if price is None:
            time.sleep(1)
            continue

        print(f"🔄 Цикл работает. Цена BTC: {price}")
        # send_telegram_message(f"🔄 Проверка. Цена BTC: {price}")  # Можно включить для отладки

        in_trade = True
        simulate_trade(price)
        in_trade = False
