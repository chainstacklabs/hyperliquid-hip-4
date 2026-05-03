"""Modify an open order's price and/or size in-place.

Usage:
    uv run python examples/08_modify_order.py --outcome 5915 --side 0 --oid 123 --buy --px 0.12 --sz 5
"""

import argparse

from rich.console import Console

from hl4 import load_config
from hl4.client import make_clients
from hl4.outcomes import encode_coin


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--outcome", type=int, required=True)
    p.add_argument("--side", type=int, default=0, choices=[0, 1])
    p.add_argument("--oid", type=int, required=True)
    p.add_argument("--buy", action="store_true")
    p.add_argument("--sell", action="store_true")
    p.add_argument("--px", type=float, required=True)
    p.add_argument("--sz", type=float, required=True)
    args = p.parse_args()
    if args.buy == args.sell:
        raise SystemExit("pass exactly one of --buy / --sell")

    cfg = load_config()
    _info, exchange = make_clients(cfg)
    coin = encode_coin(args.outcome, args.side)
    c = Console()
    res = exchange.modify_order(
        args.oid,
        coin,
        is_buy=args.buy,
        sz=args.sz,
        limit_px=args.px,
        order_type={"limit": {"tif": "Gtc"}},
    )
    c.print(res)


if __name__ == "__main__":
    main()
