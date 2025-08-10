# config.py
# Конфигурация бота (параметры и настройки)

# ===== ПАРАМЕТРЫ ТОРГОВЛИ =====
SYMBOL = "BTCUSDT"         # Торговая пара
MARKET = "linear"          # linear = USDT perpetual
TRADE_SIZE = 600           # Объём сделки в USDT
TP_USD = 10                # Тейк-профит в $ по цене BTC
SL_USD = 10                # Стоп-лосс в $ по цене BTC
MAKER_FEE = 0.00036        # 0.036%
TAKER_FEE = 0.0010         # 0.10%
TICK_SIZE = 0.1            # Минимальный шаг цены для BTCUSDT
ORDER_LIFETIME = 10        # Время жизни лимитки (сек), потом переставляем

# ===== РЕЖИМ РАБОТЫ =====
SIMULATION = True          # True = режим симулятора, False = реальная торговля

# ===== BYBIT API (нужны только для реальной торговли) =====
API_KEY = "your_api_key"
API_SECRET = "your_api_secret"

#===== TELEGRAM
ENABLE_TELEGRAM = True            # включить/выключить отправку в TG
TELEGRAM_TOKEN = "xxx:yyyy"       # токен бота
TELEGRAM_CHAT_ID = "123456789"    # твой chat_id
TG_RATE_LIMIT_SEC = 1.5           # защита от спама (секунд между сообщениями)

# ===== LOGGING =====
LOG_LEVEL = "INFO"         # INFO / DEBUG
