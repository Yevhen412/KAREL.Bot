# main.py

from screen import DexScreenerScraper

def handle_token(token):
    print(f"[main.py] Обнаружен: {token['symbol']} | Цена: {token['priceUsd']} | LP: ${token['liquidity']}")

if __name__ == "__main__":
    scraper = DexScreenerScraper(callback=handle_token)
    scraper.run()
