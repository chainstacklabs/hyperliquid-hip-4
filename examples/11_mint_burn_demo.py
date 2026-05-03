"""Explainer: mint vs burn vs normal-trade on HIP-4.

HIP-4 has no separate `splitPosition` / `mergePositions` API like Polymarket
(Gnosis CTF). Instead, every fill in the orderbook is *classified* by the
matching engine into one of these cases (per the official fee docs):

  1. MINT          — both sides have no prior position. Locks USDH on each side
                     and creates a new YES holder + a new NO holder. FEE: 0.
  2. NORMAL TRADE  — one side closes an existing position, the other opens.
                     Fee paid by whichever side is opening / taking liquidity.
  3. BURN          — both sides hold opposite legs and trade against each other
                     to flatten. The two positions cancel and USDH collateral
                     is released. Fees apply (both sides, or taker-only).
  4. SETTLEMENT    — at expiry, oracle posts result; YES credits 1 USDH, NO
                     credits 0 (or vice versa). No claim call needed.

Implication for your bot: you don't choose mint/burn — the engine does, based
on the inventory of the matching counterparties. Two equivalent ways to get
short YES exposure are:
  (a) place a sell on the YES side at price p (synthetic short)
  (b) place a buy on the NO side at price 1-p

Both create the same economic exposure but route through the YES or NO book.
A market maker should quote both books to maximize fill probability."""

from rich.console import Console
from rich.markdown import Markdown


def main() -> None:
    Console().print(Markdown(__doc__ or ""))


if __name__ == "__main__":
    main()
