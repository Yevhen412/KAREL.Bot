import requests
import time

class TokenMonitor:
    def __init__(self, callback, delay=2):
        self.seen_tokens = set()
        self.callback = callback
        self.delay = delay  # опрос каждые N секунд

    def fetch_new_tokens(self):
        url = "https://public-api.birdeye.so/public/tokenlist?sort_by=created_at&sort_type=desc"
        headers = {
            "X-API-KEY": "839342d297b044e9b3c20984d128a757"  # ← вставь свой ключ сюда
        }
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            tokens = data.get("data", {}).get("tokens", [])
            return tokens
        except Exception as e:
            print(f"[screen.py] ❌ Ошибка при получении токенов: {e}")
            return []

    def run(self):
        print("[screen.py] ▶️ Мониторинг новых токенов запущен.")
        while True:
            tokens = self.fetch_new_tokens()
            for token in tokens:
                address = token.get("address")
                if address and address not in self.seen_tokens:
                    self.seen_tokens.add(address)
                    token_data = {
                        "name": token.get("name"),
                        "symbol": token.get("symbol"),
                        "address": address,
                        "created_at": token.get("created_at"),
                        "creator": token.get("creator")
                    }
                    print(f"[screen.py] 🆕 Новый токен: {token_data['name']} ({token_data['symbol']})")
                    self.callback(token_data)
            time.sleep(self.delay)
