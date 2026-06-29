"""Explicit split / merge / negate of HIP-4 outcome shares.

Unlike normal trading (where the matching engine *classifies* fills as
mint/burn/normal — see 11_mint_burn_demo.py), these are user-initiated
`userOutcome` actions that convert shares directly, with no counterparty:

  split   --outcome 7002 --amount 1     lock 1 USDH -> 1 YES + 1 NO
  merge   --outcome 7002 [--amount 1]   burn 1 YES + 1 NO -> 1 USDH (omit = max)
  negate  --question 182 --outcome 7003 --amount 1   burn NO of 7003 ->
          credit YES of every other leg (7004, 7005, fallback 7002)
  merge-question --question 182 [--amount 1]   burn 1 YES of EVERY leg ->
          1 USDH (a complete set). Omit --amount for max. This is how you exit
          a full YES set (e.g. after a negate) without waiting for settlement.

Fees on outcome markets are currently zero (initial testing).

Usage:
    uv run python examples/13_split_merge.py split  --outcome 7002 --amount 1
    uv run python examples/13_split_merge.py merge  --outcome 7002 --amount 1
    uv run python examples/13_split_merge.py merge  --outcome 7002
    uv run python examples/13_split_merge.py negate --question 182 --outcome 7003 --amount 1
    uv run python examples/13_split_merge.py merge-question --question 182
"""

import argparse

from rich.console import Console

from hl4 import load_config
from hl4.client import make_clients
from hl4.outcome_actions import (
    merge_outcome,
    merge_question,
    negate_outcome,
    split_outcome,
)


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("split")
    sp.add_argument("--outcome", type=int, required=True)
    sp.add_argument("--amount", required=True)

    mp = sub.add_parser("merge")
    mp.add_argument("--outcome", type=int, required=True)
    mp.add_argument("--amount", default=None, help="omit to merge the max available")

    np = sub.add_parser("negate")
    np.add_argument("--question", type=int, required=True)
    np.add_argument("--outcome", type=int, required=True)
    np.add_argument("--amount", required=True)

    qp = sub.add_parser("merge-question")
    qp.add_argument("--question", type=int, required=True)
    qp.add_argument("--amount", default=None, help="omit to merge the max complete set")

    args = p.parse_args()
    cfg = load_config()
    # No need to hydrate the coin map — userOutcome actions take raw ids, not coins.
    _info, exchange = make_clients(cfg, hydrate_outcomes=False)
    c = Console()

    if args.cmd == "split":
        c.print(f"split outcome {args.outcome} amount {args.amount}")
        c.print(split_outcome(exchange, args.outcome, args.amount))
    elif args.cmd == "merge":
        c.print(f"merge outcome {args.outcome} amount {args.amount or 'MAX'}")
        c.print(merge_outcome(exchange, args.outcome, args.amount))
    elif args.cmd == "negate":
        c.print(f"negate Q{args.question} outcome {args.outcome} amount {args.amount}")
        c.print(negate_outcome(exchange, args.question, args.outcome, args.amount))
    elif args.cmd == "merge-question":
        c.print(f"merge-question Q{args.question} amount {args.amount or 'MAX'}")
        c.print(merge_question(exchange, args.question, args.amount))


if __name__ == "__main__":
    main()
