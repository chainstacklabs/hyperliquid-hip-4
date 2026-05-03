"""Show USDC, USDH, and outcome positions for the configured wallet.

Outcome positions are tracked under HyperCore as signed balances per side coin.
The Hyperliquid SDK does not currently surface them in `clearinghouseState`, so
we fetch `spotClearinghouseState` (which includes outcome side balances) and
filter for entries whose coin starts with `#`."""

import httpx
from rich.console import Console
from rich.table import Table

from hl4 import load_config


def main() -> None:
    cfg = load_config()
    addr = cfg.address
    c = Console()

    perp = httpx.post(
        f"{cfg.base_url}/info",
        json={"type": "clearinghouseState", "user": addr},
        timeout=10.0,
    ).json()
    spot = httpx.post(
        f"{cfg.base_url}/info",
        json={"type": "spotClearinghouseState", "user": addr},
        timeout=10.0,
    ).json()

    c.rule("Perp / margin account")
    c.print(perp.get("marginSummary", {}))
    c.print(f"  withdrawable: {perp.get('withdrawable')} USDC")

    c.rule("Spot balances (USDC / USDH / outcome legs)")
    table = Table()
    for col in ("coin", "token", "kind", "total", "hold", "entryNtl"):
        table.add_column(col)
    for b in spot.get("balances", []):
        if float(b["total"]) == 0 and b["coin"] not in {"USDC", "USDH"}:
            continue
        kind = "outcome" if b["coin"].startswith("+") else "spot"
        table.add_row(
            b["coin"], str(b.get("token", "-")), kind,
            b["total"], b["hold"], b["entryNtl"],
        )
    c.print(table)


if __name__ == "__main__":
    main()
