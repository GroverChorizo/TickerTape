import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
import asyncio
from backend.alerts import SocketNotifier, AlertManager


def test_alert_emission(tmp_path):
    async def _run():
        notifier = SocketNotifier(host="127.0.0.1", port=9876)
        await notifier.start()

        # start a client to receive messages
        reader, writer = await asyncio.open_connection("127.0.0.1", 9876)

        mgr = AlertManager(notifier)

        # emit an alert
        await mgr.emit("liquidation_spike", "high", "liquidations", {"count": 10})

        # read line
        data = await reader.readline()
        assert data
        msg = data.decode("utf-8").strip()
        assert "liquidation_spike" in msg

        writer.close()
        await writer.wait_closed()
        await notifier.stop()

    asyncio.run(_run())
