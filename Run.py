import asyncio
from screen import PumpScreen

async def on_new_token(token):
    # тут дальше будут фильтры/покупка
    print(f"🆕 MINT: {token['mint']} | TX: {token['tx']}")

if __name__ == "__main__":
    scr = PumpScreen(callback=on_new_token)
    asyncio.run(scr.run())
