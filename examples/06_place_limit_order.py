"""Place a resting GTC limit order on an outcome side.

Default behavior keeps the price well away from the touch so the order rests
on the book and you can practice cancel/modify/close on it.

Usage:
    uv run python examples/06_place_limit_order.py --outcome 5915 --side 0 --buy --px 0.10 --sz 5
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
    p.add_argument("--buy", action="store_true")
    p.add_argument("--sell", action="store_true")
    p.add_argument("--px", type=float, required=True, help="0.001 .. 0.999")
    p.add_argument("--sz", type=float, required=True)
    args = p.parse_args()
    if args.buy == args.sell:
        raise SystemExit("pass exactly one of --buy / --sell")
    if not (0.001 <= args.px <= 0.999):
        raise SystemExit("px must be within 0.001 .. 0.999 for outcome markets")

    cfg = load_config()
    _info, exchange = make_clients(cfg)
    coin = encode_coin(args.outcome, args.side)
    c = Console()
    c.print(f"placing {'BUY' if args.buy else 'SELL'} {args.sz} @ {args.px} on {coin}")
    res = exchange.order(
        coin,
        is_buy=args.buy,
        sz=args.sz,
        limit_px=args.px,
        order_type={"limit": {"tif": "Gtc"}},
    )
    c.print(res)


if __name__ == "__main__":
    main()
