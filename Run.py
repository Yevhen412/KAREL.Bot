from screen_dex import DexScreenerMonitor

def handle_new_token(token):
    print(f"[main.py] Обнаружен: {token['symbol']} | Цена: {token['priceUsd']} | LP: ${token['liquidity']}")

if __name__ == "__main__":
    monitor = DexScreenerMonitor(callback=handle_new_token)
    monitor.run()
