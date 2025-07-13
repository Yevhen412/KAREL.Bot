import asyncio
from bybit_websocket import BybitWebSocket
from trade_simulator import TradeSimulator
from telegram_bot import notify_telegram
from test import test_send
import asyncio

asyncio.run(test_send())

async def send_hourly_report(simulator):
    while True:
        await asyncio.sleep(3600)
        report = simulator.generate_hourly_report()
        if report:
            await notify_telegram(report)

async def main():
    ws = BybitWebSocket()
    simulator = TradeSimulator()

    asyncio.create_task(send_hourly_report(simulator))

    async for event in ws.listen():
        signal = simulator.process(event)
        if signal:
            result_msg = simulator.simulate_trade(signal)
            if result_msg:
                await notify_telegram(result_msg)

if __name__ == "__main__":
    asyncio.run(main())
