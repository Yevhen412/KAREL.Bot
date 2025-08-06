from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

class DexScreenerSelenium:
    def __init__(self, callback, delay=5):
        self.callback = callback
        self.delay = delay
        self.seen = set()
        options = Options()
        options.headless = True
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        self.driver = webdriver.Chrome(options=options)

    def run(self):
        print("[Selenium] Запускаем мониторинг DexScreener через официальный сайт")
        while True:
            self.driver.get("https://dexscreener.com/new-pairs")
            rows = self.driver.find_elements(By.CSS_SELECTOR, "tr")
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) < 6:
                    continue
                chain = cols[1].text.lower()
                if "solana" not in chain:
                    continue
                symbol = cols[3].text
                link = row.find_element(By.TAG_NAME, "a").get_attribute("href")
                addr = link.split("/")[-1]
                if addr in self.seen:
                    continue
                self.seen.add(addr)
                print(f"[S] ✅ Новый токен: {symbol} | Адрес: {addr}")
                self.callback({"symbol": symbol, "address": addr})
            time.sleep(self.delay)
