import asyncio
from screen import PumpFunListener

async def handle_token(token):
    print("🆕 Новый токен:", token["tokenSymbol"], "| Адрес:", token["tokenAddress"])

if __name__ == "__main__":
    listener = PumpFunListener(callback=handle_token)
    asyncio.run(listener.connect())
