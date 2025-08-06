import requests
import time

class DexScreenerScraper:
    def __init__(self, callback, delay=5):
        self.callback = callback
        self.delay = delay
        self.seen_addresses = set()

    def fetch_new_pairs(self):
        url = "https://api.dexscreener.com/latest/dex/pairs"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[screen_scraper.py] ❌ Ошибка при получении JSON: {e}")
            return None

    def parse_pairs(self, data):
        if not data or "pairs" not in data:
            return []

        new_tokens = []
        for pair in data["pairs"]:
            try:
                chain = pair.get("chainId", "").lower()
                if chain != "solana":
                    continue

                address = pair["pairAddress"]
                name = pair["baseToken"]["name"]
                symbol = pair["baseToken"]["symbol"]
                if address not in self.seen_addresses:
                    self.seen_addresses.add(address)
                    new_tokens.append({
                        "name": name,
                        "symbol": symbol,
                        "address": address
                    })
            except Exception as e:
                print(f"[screen_scraper.py] ⚠️ Ошибка парсинга пары: {e}")
                continue

        return new_tokens

    def run(self):
        print("[screen_scraper.py] ▶️ Мониторинг новых токенов Solana через DexScreener API запущен.")
        while True:
            data = self.fetch_new_pairs()
            tokens = self.parse_pairs(data)
            for token in tokens:
                self.callback(token)
            time.sleep(self.delay)
