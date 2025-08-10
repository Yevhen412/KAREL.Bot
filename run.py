from websocket_client import BybitWebSocket
import time

if __name__ == "__main__":
    ws_client = BybitWebSocket()
    ws_client.start()

    while True:
        time.sleep(1)
