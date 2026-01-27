"""Example client that connects to SocketNotifier and prints incoming alerts."""

import asyncio


async def main():
    reader, writer = await asyncio.open_connection("127.0.0.1", 8765)
    try:
        while True:
            line = await reader.readline()
            if not line:
                break
            print(line.decode("utf-8").strip())
    finally:
        writer.close()
        await writer.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
