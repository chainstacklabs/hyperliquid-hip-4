"""Buy USDH for USDC on the testnet spot pair @1338.

HIP-4 outcome contracts are denominated in USDH but the testnet faucet pays out
USDC. The USDH/USDC spot pair is liquid at ~1.0 with thin slippage. This script
takes a target USDH amount and crosses the ask up to a configurable max price
(default 1.001).

Usage:
    uv run python examples/00_get_usdh.py --amount 50
    uv run python examples/00_get_usdh.py --amount 50 --max-price 1.0
"""

import argparse

import httpx
from eth_account import Account
from hyperliquid.exchange import Exchange
from rich.console import Console

from hl4 import load_config

USDH_USDC_COIN = "@1338"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--amount", type=float, required=True, help="USDH to buy")
    p.add_argument("--max-price", type=float, default=1.001)
    args = p.parse_args()

    cfg = load_config()
    c = Console()

    book = httpx.post(
        f"{cfg.base_url}/info",
        json={"type": "l2Book", "coin": USDH_USDC_COIN},
        timeout=10.0,
    ).json()
    asks = book.get("levels", [[], []])[1]
    if not asks:
        c.print("[red]no asks on USDH/USDC[/red]")
        return
    best_ask = float(asks[0]["px"])
    c.print(f"best ask {best_ask}, requested max {args.max_price}")
    if best_ask > args.max_price:
        c.print("[red]best ask above max-price; aborting[/red]")
        return

    account = Account.from_key(cfg.private_key)
    exchange = Exchange(account, cfg.base_url, account_address=cfg.address)

    sz = round(args.amount, 2)
    c.print(f"placing IOC buy: {sz} USDH @ {args.max_price} on {USDH_USDC_COIN}")
    result = exchange.order(
        USDH_USDC_COIN,
        is_buy=True,
        sz=sz,
        limit_px=args.max_price,
        order_type={"limit": {"tif": "Ioc"}},
    )
    c.print(result)


if __name__ == "__main__":
    main()
