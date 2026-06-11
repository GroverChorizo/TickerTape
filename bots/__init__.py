"""Strategy bots — standalone processes per the Bot-TickerTape Interface Contract.

Bots NEVER import TickerTape and TickerTape never imports bots. The only
shared surfaces are local files: data/*.csv (read via data_loader), an
append-only signals/signals.jsonl, atomic state/<bot>.json heartbeats, and
the state/KILL kill-switch.
"""
