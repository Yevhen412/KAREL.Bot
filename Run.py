from screen import DexScreenerSelenium

def handle_token(t):
    print("🔔 Новый токен:", t)

monitor = DexScreenerSelenium(callback=handle_token, delay=5)
monitor.run()
