"""Cancel an open order by oid.

Usage:
    uv run python examples/07_cancel_order.py --outcome 5915 --side 0 --oid 12345
    uv run python examples/07_cancel_order.py --outcome 5915 --side 0 --all
"""

import argparse

import httpx
from rich.console import Console

from hl4 import load_config
from hl4.client import make_clients
from hl4.outcomes import encode_coin


def open_orders_for_coin(base_url: str, address: str, coin: str) -> list[int]:
    r = httpx.post(
        f"{base_url}/info",
        json={"type": "openOrders", "user": address},
        timeout=10.0,
    )
    r.raise_for_status()
    return [o["oid"] for o in r.json() if o.get("coin") == coin]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--outcome", type=int, required=True)
    p.add_argument("--side", type=int, default=0, choices=[0, 1])
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--oid", type=int)
    g.add_argument("--all", action="store_true")
    args = p.parse_args()

    cfg = load_config()
    _info, exchange = make_clients(cfg)
    coin = encode_coin(args.outcome, args.side)
    c = Console()

    oids = [args.oid] if args.oid else open_orders_for_coin(cfg.base_url, cfg.address, coin)
    if not oids:
        c.print("nothing to cancel"); return
    for oid in oids:
        c.print(exchange.cancel(coin, oid))


if __name__ == "__main__":
    main()
