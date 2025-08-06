from screen import TokenMonitor

def fetch_new_token(token):
    print(f"[main.py] Обнаружен мемкоин: {token['name']} | Адрес: {token['address']}")

if __name__ == "__main__":
    monitor = TokenMonitor(callback=handle_new_token)
    monitor.run()
