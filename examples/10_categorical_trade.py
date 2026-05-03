"""Trade a single leg of a categorical question.

A `question` is N binary outcomes plus a fallback. To bet on "Otoro will win",
you place a buy on the YES side of the Otoro leg. To fade it, sell YES (which
is the same as buying NO at price 1 - YES_px before fees).

Usage:
    uv run python examples/10_categorical_trade.py --question 1 --backing-outcome 12 --buy --px 0.30 --sz 5
"""

import argparse

from rich.console import Console

from hl4 import fetch_outcome_meta, load_config
from hl4.client import make_clients
from hl4.outcomes import encode_coin


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--question", type=int, required=True)
    p.add_argument("--backing-outcome", type=int, required=True,
                   help="which leg of the question you're taking a view on")
    p.add_argument("--buy", action="store_true")
    p.add_argument("--sell", action="store_true")
    p.add_argument("--px", type=float, required=True)
    p.add_argument("--sz", type=float, required=True)
    args = p.parse_args()
    if args.buy == args.sell:
        raise SystemExit("pass exactly one of --buy / --sell")

    cfg = load_config()
    outcomes, questions = fetch_outcome_meta(cfg.base_url)
    q = next((q for q in questions if q.question_id == args.question), None)
    if not q:
        raise SystemExit(f"question {args.question} not found")
    if args.backing_outcome not in q.named_outcomes and args.backing_outcome != q.fallback_outcome:
        raise SystemExit(
            f"outcome {args.backing_outcome} is not part of question {args.question} "
            f"(named={q.named_outcomes}, fallback={q.fallback_outcome})"
        )

    _info, exchange = make_clients(cfg)
    coin = encode_coin(args.backing_outcome, 0)
    c = Console()
    c.print(f"trading YES leg of outcome {args.backing_outcome} under question Q{q.question_id}: {q.name}")
    c.print(exchange.order(
        coin,
        is_buy=args.buy,
        sz=args.sz,
        limit_px=args.px,
        order_type={"limit": {"tif": "Gtc"}},
    ))


if __name__ == "__main__":
    main()
