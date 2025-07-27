# config.py

import os

# Порог импульса BTC в % за 10 секунд
IMPULSE_THRESHOLD_PERCENT = 0.3

# Интервал окна анализа (в секундах)
IMPULSE_WINDOW_SECONDS = 10

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Сообщение каждые 10 минут, если нет импульсов
ALIVE_NOTIFICATION_INTERVAL_MINUTES = 10

# Символ для отслеживания
SYMBOL = "BTCUSDT"

# Интервал WebSocket-данных
WS_INTERVAL = "100ms"
