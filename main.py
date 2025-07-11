import asyncio
from bybit_websocket import BybitWebSocket

async def main():
    ws = BybitWebSocket()
    async for msg in ws.listen():
        print(msg)

if __name__ == "__main__":
    asyncio.run(main())
