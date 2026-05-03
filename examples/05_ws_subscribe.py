"""Subscribe to live l2Book + trades for one side of an outcome over WebSocket.

Usage:
    uv run python examples/05_ws_subscribe.py --outcome 5915 --side 0 --seconds 30
"""

import argparse
import asyncio
import json

import websockets
from rich.console import Console

from hl4 import encode_coin, load_config


async def run(ws_url: str, coin: str, seconds: int) -> None:
    c = Console()
    async with websockets.connect(ws_url) as ws:
        for sub in ({"type": "l2Book", "coin": coin}, {"type": "trades", "coin": coin}):
            await ws.send(json.dumps({"method": "subscribe", "subscription": sub}))
        c.print(f"subscribed l2Book + trades on coin={coin}, listening {seconds}s ...")
        try:
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=seconds)
                d = json.loads(msg)
                ch = d.get("channel")
                if ch == "l2Book":
                    lvls = d["data"]["levels"]
                    bid = lvls[0][0] if lvls[0] else {}
                    ask = lvls[1][0] if lvls[1] else {}
                    c.print(f"book bid={bid.get('px')} ({bid.get('sz')})  ask={ask.get('px')} ({ask.get('sz')})")
                elif ch == "trades":
                    for t in d["data"]:
                        c.print(f"[yellow]trade[/yellow] px={t['px']} sz={t['sz']} side={t['side']}")
                elif ch == "subscriptionResponse":
                    pass
                else:
                    c.print(f"[dim]{ch}: {str(d)[:120]}[/dim]")
        except asyncio.TimeoutError:
            c.print("done")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--outcome", type=int, required=True)
    p.add_argument("--side", type=int, default=0, choices=[0, 1])
    p.add_argument("--seconds", type=int, default=30)
    args = p.parse_args()
    cfg = load_config()
    asyncio.run(run(cfg.ws_url, encode_coin(args.outcome, args.side), args.seconds))


if __name__ == "__main__":
    main()
