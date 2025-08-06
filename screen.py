# screen_dex.py

import requests
import time

class DexScreenerMonitor:
    def __init__(self, callback, delay=3):
        self.callback = callback
        self.delay = delay  # пауза между запросами
        self.seen_pairs = set()

    def fetch_new_pairs(self):
        url = "https://api.dexscreener.io/latest/dex/pairs"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            pairs = data.get("pairs", [])
            return pairs
        except Exception as e:
            print(f"[screen_dex.py] ❌ Ошибка при получении пар: {e}")
            return []

    def run(self):
        print("[screen_dex.py] ▶️ Мониторинг новых пар Solana через DexScreener запущен.")
        while True:
            pairs = self.fetch_new_pairs()
            for pair in pairs:
                address = pair.get("pairAddress")
                if address and address not in self.seen_pairs:
                    self.seen_pairs.add(address)
                    token_data = {
                        "name": pair.get("baseToken", {}).get("name"),
                        "symbol": pair.get("baseToken", {}).get("symbol"),
                        "address": address,
                        "priceUsd": pair.get("priceUsd"),
                        "liquidity": pair.get("liquidity", {}).get("usd"),
                        "fdv": pair.get("fdv"),
                        "createdAt": pair.get("pairCreatedAt")
                    }
                    print(f"[screen_dex.py] 🆕 Новый токен: {token_data['symbol']} | Цена: ${token_data['priceUsd']}")
                    self.callback(token_data)
            time.sleep(self.delay)
