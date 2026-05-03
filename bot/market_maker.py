"""Passive two-sided market maker for HIP-4 outcome contracts.

For each configured outcome, quotes both the YES and NO order books at
`fair_px ± half_spread`, sized to `quote_notional_usdh`. Replaces orders when
the touch drifts more than `repost_threshold`. Skews to one side only when
inventory in that side exceeds `max_inventory_per_side`.

Run:
    uv run python -m bot.market_maker --outcomes 5915,5969 \
        --quote-notional 12 --half-spread 0.04 --max-inventory 30

Stop with Ctrl+C — the bot cancels all open orders before exiting."""

import argparse
import asyncio
import signal
import time
from dataclasses import dataclass, field

import httpx
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from rich.console import Console

from hl4 import load_config
from hl4.client import make_clients
from hl4.outcomes import encode_balance_coin, encode_coin

console = Console()

PRICE_MIN = 0.001
PRICE_MAX = 0.999
PRICE_TICK = 0.001


def round_tick(px: float) -> float:
    return max(PRICE_MIN, min(PRICE_MAX, round(px, 3)))


@dataclass
class SideState:
    coin: str
    is_buy: bool
    open_oid: int | None = None
    open_px: float | None = None
    open_sz: float | None = None


@dataclass
class OutcomeMM:
    outcome_id: int
    sides: dict[tuple[int, bool], SideState] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for side in (0, 1):
            coin = encode_coin(self.outcome_id, side)
            self.sides[(side, True)] = SideState(coin=coin, is_buy=True)
            self.sides[(side, False)] = SideState(coin=coin, is_buy=False)


def fetch_book(base_url: str, coin: str) -> tuple[float | None, float | None]:
    r = httpx.post(f"{base_url}/info", json={"type": "l2Book", "coin": coin}, timeout=5.0)
    levels = r.json().get("levels", [[], []])
    bid = float(levels[0][0]["px"]) if levels[0] else None
    ask = float(levels[1][0]["px"]) if levels[1] else None
    return bid, ask


def fair_from_book(bid: float | None, ask: float | None) -> float | None:
    if bid is not None and ask is not None:
        return (bid + ask) / 2
    if bid is not None:
        return min(PRICE_MAX, bid + PRICE_TICK)
    if ask is not None:
        return max(PRICE_MIN, ask - PRICE_TICK)
    return 0.5


def position_for(base_url: str, address: str, balance_coin: str) -> float:
    """Look up an outcome side balance. Note: outcome balances appear under the
    `+<encoding>` coin form, not the `#<encoding>` form used for trading."""
    r = httpx.post(
        f"{base_url}/info",
        json={"type": "spotClearinghouseState", "user": address},
        timeout=5.0,
    )
    for b in r.json().get("balances", []):
        if b["coin"] == balance_coin:
            return float(b["total"])
    return 0.0


def safe_cancel(exchange: Exchange, coin: str, oid: int) -> None:
    try:
        exchange.cancel(coin, oid)
    except Exception as e:
        console.print(f"[red]cancel {oid} on {coin}: {e}[/red]")


def replace_quote(
    exchange: Exchange,
    side_state: SideState,
    target_px: float,
    target_sz: float,
    repost_threshold: float,
) -> None:
    needs_replace = (
        side_state.open_oid is None
        or side_state.open_px is None
        or abs(side_state.open_px - target_px) >= repost_threshold
        or side_state.open_sz != target_sz
    )
    if not needs_replace:
        return

    if side_state.open_oid is not None:
        safe_cancel(exchange, side_state.coin, side_state.open_oid)
        side_state.open_oid = None

    if target_sz <= 0:
        return

    try:
        res = exchange.order(
            side_state.coin,
            is_buy=side_state.is_buy,
            sz=target_sz,
            limit_px=target_px,
            order_type={"limit": {"tif": "Gtc"}},
        )
    except Exception as e:
        console.print(f"[red]order err on {side_state.coin}: {e}[/red]")
        return

    statuses = res.get("response", {}).get("data", {}).get("statuses", [])
    for s in statuses:
        if "resting" in s:
            side_state.open_oid = s["resting"]["oid"]
            side_state.open_px = target_px
            side_state.open_sz = target_sz
            console.print(
                f"  [green]{'BUY' if side_state.is_buy else 'SELL'}[/green] "
                f"{target_sz} @ {target_px} on {side_state.coin} "
                f"oid={side_state.open_oid}"
            )
        elif "filled" in s:
            console.print(
                f"  [yellow]immediate fill[/yellow] on {side_state.coin}: {s['filled']}"
            )
        elif "error" in s:
            console.print(f"  [red]{s['error']}[/red] on {side_state.coin}")


def quote_outcome(
    cfg,
    info: Info,
    exchange: Exchange,
    state: OutcomeMM,
    half_spread: float,
    quote_notional: float,
    max_inventory: float,
    repost_threshold: float,
) -> None:
    yes_coin = encode_coin(state.outcome_id, 0)
    no_coin = encode_coin(state.outcome_id, 1)
    yes_bid, yes_ask = fetch_book(cfg.base_url, yes_coin)
    no_bid, no_ask = fetch_book(cfg.base_url, no_coin)

    fair_yes = fair_from_book(yes_bid, yes_ask)
    fair_no_implied = (1.0 - fair_yes) if fair_yes is not None else None
    fair_no_book = fair_from_book(no_bid, no_ask)
    fair_no = fair_no_book if fair_no_book is not None else fair_no_implied

    yes_pos = position_for(cfg.base_url, cfg.address, encode_balance_coin(state.outcome_id, 0))
    no_pos = position_for(cfg.base_url, cfg.address, encode_balance_coin(state.outcome_id, 1))

    console.print(
        f"[bold]outcome {state.outcome_id}[/bold] "
        f"YES book {yes_bid}/{yes_ask} fair {fair_yes}  "
        f"NO book {no_bid}/{no_ask} fair {fair_no}  "
        f"pos YES={yes_pos:.2f} NO={no_pos:.2f}"
    )

    for side, fair, my_pos in ((0, fair_yes, yes_pos), (1, fair_no, no_pos)):
        if fair is None:
            continue
        bid_px = round_tick(fair - half_spread)
        ask_px = round_tick(fair + half_spread)
        # min notional ~$10 USDH; outcome size precision is integer on testnet
        sz_buy = float(int(max(quote_notional, 11) / max(bid_px, 0.01)) + 1)
        sz_sell = float(int(max(quote_notional, 11) / max(ask_px, 0.01)) + 1)

        bid_state = state.sides[(side, True)]
        ask_state = state.sides[(side, False)]

        # inventory cap: stop adding to a side when over the cap
        if my_pos >= max_inventory:
            sz_buy = 0
        if my_pos <= 0:
            sz_sell = 0
        elif my_pos < sz_sell:
            sz_sell = float(int(my_pos))

        replace_quote(exchange, bid_state, bid_px, sz_buy, repost_threshold)
        replace_quote(exchange, ask_state, ask_px, sz_sell, repost_threshold)


def cancel_all(exchange: Exchange, states: list[OutcomeMM]) -> None:
    console.print("[bold]cancelling all open orders[/bold]")
    for s in states:
        for ss in s.sides.values():
            if ss.open_oid is not None:
                safe_cancel(exchange, ss.coin, ss.open_oid)
                ss.open_oid = None


async def main_loop(args) -> None:
    cfg = load_config()
    info, exchange = make_clients(cfg)
    states = [OutcomeMM(o) for o in args.outcome_ids]

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    console.print(f"[bold green]market maker up[/bold green] outcomes={args.outcome_ids}")
    try:
        while not stop.is_set():
            t0 = time.time()
            for s in states:
                quote_outcome(
                    cfg, info, exchange, s,
                    half_spread=args.half_spread,
                    quote_notional=args.quote_notional,
                    max_inventory=args.max_inventory,
                    repost_threshold=args.repost_threshold,
                )
            elapsed = time.time() - t0
            await asyncio.wait_for(stop.wait(), timeout=max(0.1, args.tick - elapsed))
    except asyncio.TimeoutError:
        pass
    except Exception as e:
        console.print(f"[red]loop error: {e}[/red]")
    finally:
        cancel_all(exchange, states)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--outcomes", required=True, help="comma-separated outcome ids")
    p.add_argument("--half-spread", type=float, default=0.04)
    p.add_argument("--quote-notional", type=float, default=12.0, help="USDH per quote")
    p.add_argument("--max-inventory", type=float, default=30.0, help="max units per side")
    p.add_argument("--repost-threshold", type=float, default=0.005)
    p.add_argument("--tick", type=float, default=5.0, help="seconds per loop")
    args = p.parse_args()
    args.outcome_ids = [int(x) for x in args.outcomes.split(",")]
    asyncio.run(main_loop(args))


if __name__ == "__main__":
    main()
