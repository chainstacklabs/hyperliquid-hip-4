"""Hold a position to expiry and watch it auto-settle.

Polls spotClearinghouseState every 10s. When the outcome's coin disappears
from the balances list (or its `total` snaps to a settled value) it prints
the realized PnL.

Usage:
    uv run python examples/12_wait_for_settlement.py --outcome 5969 --side 0
"""

import argparse
import time

import httpx
from rich.console import Console

from hl4 import load_config
from hl4.outcomes import encode_balance_coin


def fetch_balance(base_url: str, address: str, balance_coin: str) -> dict | None:
    r = httpx.post(
        f"{base_url}/info",
        json={"type": "spotClearinghouseState", "user": address},
        timeout=10.0,
    )
    for b in r.json().get("balances", []):
        if b["coin"] == balance_coin:
            return b
    return None


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--outcome", type=int, required=True)
    p.add_argument("--side", type=int, default=0, choices=[0, 1])
    p.add_argument("--poll", type=int, default=10)
    args = p.parse_args()

    cfg = load_config()
    bal_coin = encode_balance_coin(args.outcome, args.side)
    c = Console()

    initial = fetch_balance(cfg.base_url, cfg.address, bal_coin)
    if not initial or float(initial["total"]) == 0:
        c.print(f"[red]no position on {bal_coin}[/red]"); return
    c.print(f"watching {bal_coin}: size={initial['total']} entryNtl={initial['entryNtl']}")
    while True:
        b = fetch_balance(cfg.base_url, cfg.address, bal_coin)
        if b is None or float(b["total"]) == 0:
            c.print("[green]position settled (balance is zero)[/green]")
            break
        c.print(f"  still open: total={b['total']}")
        time.sleep(args.poll)


if __name__ == "__main__":
    main()
