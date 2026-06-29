"""Explicit HIP-4 `userOutcome` actions: split / merge / negate.

These are manual conversions between outcome shares, sent as raw L1 actions to
the `/exchange` endpoint. The hyperliquid-python-sdk (<=0.24.0) has no helper
for them, so we sign and post by hand using the same `sign_l1_action` path the
SDK uses for `order`.

Action shapes (from the HIP-4 docs):

    {"type": "userOutcome", "splitOutcome":   {"outcome": int, "amount": str}}
    {"type": "userOutcome", "mergeOutcome":   {"outcome": int, "amount": str | None}}
    {"type": "userOutcome", "negateOutcome":  {"question": int, "outcome": int, "amount": str}}
    {"type": "userOutcome", "mergeQuestion":  {"question": int, "amount": str | None}}

- split:  lock `amount` USDH on `outcome`, mint `amount` YES + `amount` NO.
- merge:  burn matching YES+NO pairs of one `outcome` back into USDH
          (amount=None merges max).
- negate: burn `amount` NO of `outcome` (a named leg of `question`) and credit
          `amount` YES of EVERY OTHER leg (the other named outcomes + the
          fallback). i.e. NO-of-one-leg == YES-of-the-complementary-set.
          Unidirectional — there is no reverse-negate.
- merge-question: burn `amount` YES of EVERY outcome of `question` (a complete
          set) back into `amount` USDH. The way to exit a full YES set without
          waiting for settlement (and the unwind for negate, which scatters
          your position into YES legs across the question).

`amount` is a string (same convention as order sizes), to avoid float drift.
"""

from typing import Any, Optional

from hyperliquid.exchange import Exchange
from hyperliquid.utils.constants import MAINNET_API_URL
from hyperliquid.utils.signing import get_timestamp_ms, sign_l1_action


def _post_user_outcome(exchange: Exchange, action: dict[str, Any]) -> Any:
    timestamp = get_timestamp_ms()
    signature = sign_l1_action(
        exchange.wallet,
        action,
        exchange.vault_address,
        timestamp,
        exchange.expires_after,
        exchange.base_url == MAINNET_API_URL,
    )
    return exchange._post_action(action, signature, timestamp)


def split_outcome(exchange: Exchange, outcome: int, amount: str) -> Any:
    """Mint `amount` YES + `amount` NO of `outcome`, locking `amount` USDH."""
    return _post_user_outcome(
        exchange,
        {"type": "userOutcome", "splitOutcome": {"outcome": outcome, "amount": amount}},
    )


def merge_outcome(exchange: Exchange, outcome: int, amount: Optional[str] = None) -> Any:
    """Burn matching YES+NO pairs back into USDH. `amount=None` merges the max."""
    return _post_user_outcome(
        exchange,
        {"type": "userOutcome", "mergeOutcome": {"outcome": outcome, "amount": amount}},
    )


def negate_outcome(exchange: Exchange, question: int, outcome: int, amount: str) -> Any:
    """Burn `amount` NO of `outcome` -> credit `amount` YES of every other leg
    of `question` (other named outcomes + fallback). Needs the NO leg in hand."""
    return _post_user_outcome(
        exchange,
        {
            "type": "userOutcome",
            "negateOutcome": {"question": question, "outcome": outcome, "amount": amount},
        },
    )


def merge_question(exchange: Exchange, question: int, amount: Optional[str] = None) -> Any:
    """Burn `amount` YES of EVERY outcome of `question` (a complete set) back
    into `amount` USDH. `amount=None` redeems the max complete set held."""
    return _post_user_outcome(
        exchange,
        {"type": "userOutcome", "mergeQuestion": {"question": question, "amount": amount}},
    )
