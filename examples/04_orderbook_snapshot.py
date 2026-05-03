"""Print a top-of-book snapshot for both YES and NO sides of an outcome.

Usage:
    uv run python examples/04_orderbook_snapshot.py --outcome 5915
"""

import argparse

import httpx
from rich.console import Console
from rich.table import Table

from hl4 import encode_coin, load_config


def fetch_book(base_url: str, coin: str) -> tuple[list, list]:
    r = httpx.post(
        f"{base_url}/info", json={"type": "l2Book", "coin": coin}, timeout=10.0
    )
    r.raise_for_status()
    levels = r.json().get("levels", [[], []])
    return levels[0], levels[1]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--outcome", type=int, required=True)
    p.add_argument("--depth", type=int, default=5)
    args = p.parse_args()

    cfg = load_config()
    c = Console()

    for side, label in ((0, "YES"), (1, "NO")):
        coin = encode_coin(args.outcome, side)
        bids, asks = fetch_book(cfg.base_url, coin)
        t = Table(title=f"outcome={args.outcome} side={side} ({label})  coin={coin}")
        t.add_column("bid_px"); t.add_column("bid_sz")
        t.add_column("ask_px"); t.add_column("ask_sz")
        for i in range(args.depth):
            b = bids[i] if i < len(bids) else {}
            a = asks[i] if i < len(asks) else {}
            t.add_row(b.get("px", ""), b.get("sz", ""), a.get("px", ""), a.get("sz", ""))
        c.print(t)


if __name__ == "__main__":
    main()
