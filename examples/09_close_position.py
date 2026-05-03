"""Close (or partially close) an outcome position by crossing the book IOC.

Reads spotClearinghouseState (where outcome legs appear under the `+<encoding>`
coin string), then sends an IOC sell at a far-bid limit price on the `#<encoding>`
trading coin.

Usage:
    uv run python examples/09_close_position.py --outcome 5915 --side 0
    uv run python examples/09_close_position.py --outcome 5915 --side 0 --sz 5
"""

import argparse

import httpx
from rich.console import Console

from hl4 import load_config
from hl4.client import make_clients
from hl4.outcomes import encode_balance_coin, encode_coin


def position_size(base_url: str, address: str, balance_coin: str) -> float:
    r = httpx.post(
        f"{base_url}/info",
        json={"type": "spotClearinghouseState", "user": address},
        timeout=10.0,
    )
    r.raise_for_status()
    for b in r.json().get("balances", []):
        if b["coin"] == balance_coin:
            return float(b["total"])
    return 0.0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--outcome", type=int, required=True)
    p.add_argument("--side", type=int, default=0, choices=[0, 1])
    p.add_argument("--sz", type=float, default=None, help="default: full position")
    args = p.parse_args()

    cfg = load_config()
    _info, exchange = make_clients(cfg)
    trade_coin = encode_coin(args.outcome, args.side)
    bal_coin = encode_balance_coin(args.outcome, args.side)

    book = httpx.post(
        f"{cfg.base_url}/info", json={"type": "l2Book", "coin": trade_coin}, timeout=10.0
    ).json()["levels"]
    bids, asks = book[0], book[1]

    sz = args.sz if args.sz is not None else position_size(cfg.base_url, cfg.address, bal_coin)
    if sz <= 0:
        raise SystemExit(f"no position on {bal_coin} to close")
    sz = float(int(sz))  # outcome sizes are integer

    c = Console()
    if bids:
        px = max(0.001, round(float(bids[0]["px"]) * 0.5, 4))
        tif = "Ioc"
        c.print(f"IOC SELL {sz} {trade_coin} @ {px} (cross to bid {bids[0]['px']}, balance coin {bal_coin})")
    else:
        # No bids on this side. Rest a GTC sell just inside the existing ask to attract liquidity.
        if asks:
            px = max(0.001, round(float(asks[0]["px"]) - 0.001, 4))
        else:
            px = 0.5
        tif = "Gtc"
        c.print(f"[yellow]no bids; resting GTC SELL[/yellow] {sz} {trade_coin} @ {px} (balance coin {bal_coin})")

    c.print(exchange.order(
        trade_coin, is_buy=False, sz=sz, limit_px=px,
        order_type={"limit": {"tif": tif}},
    ))


if __name__ == "__main__":
    main()
