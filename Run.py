import asyncio
from ATR import get_current_atr

atr = asyncio.run(get_current_atr())
print("Current ATR:", atr)
