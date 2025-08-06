import requests
from bs4 import BeautifulSoup
import time

class DexScreenerScraper:
    def __init__(self, callback, delay=5):
        self.callback = callback
        self.delay = delay
        self.seen_addresses = set()

    def fetch_new_pairs(self):
        url = "https://dexscreener.com/new-pairs"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"[screen_scraper.py] ❌ Ошибка при получении HTML: {e}")
            return None

    def parse_pairs(self, html):
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select("tr")  # каждая строка — это пара

        new_tokens = []

        for row in rows:
            columns = row.find_all("td")
            if len(columns) < 6:
                continue

            # Извлечение информации
            network = columns[1].text.strip().lower()
            if "solana" not in network:
                continue

            name = columns[2].text.strip()
            symbol = columns[3].text.strip()
            price = columns[4].text.strip().replace("$", "").replace(",", "")
            liquidity = columns[5].text.strip().replace("$", "").replace(",", "")
            pair_link = row.select_one("a")
            if not pair_link:
                continue

            href = pair_link.get("href")
            pair_address = href.split("/")[-1]

            if pair_address in self.seen_addresses:
                continue

            self.seen_addresses.add(pair_address)

            token_data = {
                "name": name,
                "symbol": symbol,
                "priceUsd": price,
                "liquidity": liquidity,
                "pairAddress": pair_address,
                "network": "solana"
            }

            new_tokens.append(token_data)

        return new_tokens

    def run(self):
        print("[screen_scraper.py] ▶️ Мониторинг новых токенов Solana через DexScreener (HTML) запущен.")
        while True:
            html = self.fetch_new_pairs()
            tokens = self.parse_pairs(html)
            for token in tokens:
                print(f"[screen_scraper.py] 🆕 {token['symbol']} | ${token['priceUsd']} | LP: ${token['liquidity']}")
                self.callback(token)
            time.sleep(self.delay)
