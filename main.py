from data_loader import load_data
from correlation_tracker import CorrelationTracker
from strategy import Strategy
from trade_log import TradeLogger

# Параметры
PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "XRPUSDT"]
INTERVAL = "1"  # 1 минута
WINDOW = 30  # окно корреляции (30 свечей)

# Загрузка данных
print("\n[1] Загрузка исторических данных...")
data = load_data(PAIRS, INTERVAL, limit=360)  # 6 часов

# Инициализация компонентов
print("[2] Инициализация корреляционного трекера...")
corr_tracker = CorrelationTracker(data, window=WINDOW)

print("[3] Вычисление корреляций...")
corr_matrix = corr_tracker.calculate()
print(corr_matrix)

print("[4] Поиск высоко коррелирующих пар...")
top_pairs = corr_tracker.get_top_pairs(threshold=0.85, top_n=3)
print(top_pairs)

print("[5] Запуск симуляции стратегии...")
strategy = Strategy(data, top_pairs)
results = strategy.run()

# Вывод результата
print("\n[6] Лог сделок и PnL:")
logger = TradeLogger(results)
logger.summary()
