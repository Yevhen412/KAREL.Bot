from screen import DexScreenerScraper

def handle_new_token(token):
    print(f"🟢 Новый токен: {token['symbol']} — {token['name']} ({token['address']})")

scraper = DexScreenerScraper(callback=handle_new_token, delay=5)
scraper.run()
