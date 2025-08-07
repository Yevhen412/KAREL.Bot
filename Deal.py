import time
from decimal import Decimal
from Telegram import send_telegram_message

TRADE_AMOUNT = Decimal("200")
LEVERAGE = 3
TARGET_NET_PROFIT = Decimal("0.01")
TAKER_FEE = Decimal("0.001")  # 0.1%
PAIR = "BTCUSDT"

last_trade_time = 0
in_trade = False

def get_current_price():
    # Пример API запроса к Bybit — можно заменить на WebSocket или реальный SDK
    import requests
    url = f"https://api.bybit.com/v5/market/tickers?category=linear&symbol={PAIR}"
    r = requests.get(url)
    data = r.json()
    price = Decimal(data["result"]["list"][0]["lastPrice"])
    return price

def simulate_trade(entry_price):
    global last_trade_time

    position_value = TRADE_AMOUNT * LEVERAGE
    target_profit = TARGET_NET_PROFIT
    total_fees = (entry_price * position_value) * TAKER_FEE * 2  # вход и выход

    required_exit_price = entry_price + ((target_profit + total_fees) / position_value)
    time.sleep(0.4)  # Имитируем время ожидания выхода

    # Получим текущую цену
    current_price = get_current_price()
    if current_price >= required_exit_price:
        net = (current_price - entry_price) * position_value - total_fees
        msg = (
            f"✅ Сделка завершена:\n"
            f"Пара: {PAIR}\n"
            f"Buy: {entry_price:.2f}\n"
            f"Sell: {current_price:.2f}\n"
            f"Net: {net:.5f} USDT"
        )
        print(msg)
        send_telegram_message(msg)
        last_trade_time = time.time()

def run_micro_scalper():
    global in_trade, last_trade_time

    while True:
        now = time.time()
        if in_trade or now - last_trade_time < 1:
            time.sleep(0.1)
            continue

        # Получение цены входа
        entry_price = get_current_price()
        in_trade = True
        simulate_trade(entry_price)
        in_trade = False
