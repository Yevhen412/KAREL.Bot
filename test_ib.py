from ib_insync import *

# Параметры подключения
IB_HOST = "127.0.0.1"  # Если TWS или IB Gateway запущены на другой машине, укажи IP
IB_PORT = 7497         # TWS Paper: 7497, TWS Live: 7496, IB Gateway Live: 4002, Paper: 4001
IB_CLIENT_ID = 1       # Любое число, уникальное для сессии

ib = IB()

try:
    ib.connect(IB_HOST, IB_PORT, IB_CLIENT_ID)
    print("✅ Подключение успешно!")
    print("Сервер время:", ib.reqCurrentTime())
except Exception as e:
    print("❌ Ошибка подключения:", e)
finally:
    ib.disconnect()
