from screen import DexScreenerMonitor

def handle_new_token(token):
    print(f"[main.py] Обнаружен токен: {token['symbol']} | Цена: {token['priceUsd']} | LP: ${token['liquidity']}")

if __name__ == "__main__":
    monitor = DexScreenerMonitor(callback=handle_new_token)
    monitor.run()
