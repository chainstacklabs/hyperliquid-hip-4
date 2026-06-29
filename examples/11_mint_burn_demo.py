"""Explainer: mint vs burn vs normal-trade on HIP-4.

There are TWO ways YES/NO shares get created or destroyed on HIP-4:

A) Explicit `userOutcome` actions — split / merge / negate. You call them
   directly, no counterparty needed (see 13_split_merge.py). split locks USDH
   and mints a YES+NO pair; merge burns a pair back into USDH.

B) Orderbook fills, which the matching engine *classifies* into one of the
   cases below based on the inventory of the two matching counterparties. THIS
   is what the explainer here is about — you don't pick the case, the engine
   does:

  1. MINT          — both sides have no prior position. Locks USDH on each side
                     and creates a new YES holder + a new NO holder.
  2. NORMAL TRADE  — one side closes an existing position, the other opens.
  3. BURN          — both sides hold opposite legs and trade against each other
                     to flatten. The two positions cancel and USDH collateral
                     is released.
  4. SETTLEMENT    — at expiry, oracle posts result; YES credits 1 USDH, NO
                     credits 0 (or vice versa). No claim call needed.

Fees: currently ZERO on outcome markets (initial testing). When fees turn on,
they follow the spot model (taker / builder-code), classified per case above.

Implication for your bot: for orderbook fills you don't choose mint/burn — the
engine does, based on the inventory of the matching counterparties. Two
equivalent ways to get short YES exposure are:
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
