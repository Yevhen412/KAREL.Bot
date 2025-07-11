import asyncio
from bybit_websocket import BybitWebSocket

async def main():
    ws = BybitWebSocket()
    async for event in ws.listen():
        print(event)

if __name__ == "__main__":
    asyncio.run(main())
