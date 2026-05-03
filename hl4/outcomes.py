from dataclasses import dataclass
from typing import Any

import httpx

ASSET_ID_BASE = 100_000_000
SIDE_YES = 0
SIDE_NO = 1


def encode_asset_id(outcome_id: int, side: int) -> int:
    if side not in (0, 1):
        raise ValueError(f"side must be 0 or 1, got {side}")
    return ASSET_ID_BASE + 10 * outcome_id + side


def encode_coin(outcome_id: int, side: int) -> str:
    """Coin string used for l2Book and order placement: `#<encoding>`."""
    if side not in (0, 1):
        raise ValueError(f"side must be 0 or 1, got {side}")
    return f"#{10 * outcome_id + side}"


def encode_balance_coin(outcome_id: int, side: int) -> str:
    """Coin string used in spotClearinghouseState balances: `+<encoding>`.

    Distinct from the `#` form returned by encode_coin — the API uses two
    different prefixes for the same underlying side asset depending on context."""
    if side not in (0, 1):
        raise ValueError(f"side must be 0 or 1, got {side}")
    return f"+{10 * outcome_id + side}"


@dataclass
class OutcomeSpec:
    outcome_id: int
    name: str
    description: str
    side_names: tuple[str, str]

    @property
    def is_recurring_price_binary(self) -> bool:
        return self.description.startswith("class:priceBinary|")

    def coin(self, side: int) -> str:
        return encode_coin(self.outcome_id, side)

    def asset_id(self, side: int) -> int:
        return encode_asset_id(self.outcome_id, side)


@dataclass
class QuestionSpec:
    question_id: int
    name: str
    description: str
    fallback_outcome: int
    named_outcomes: list[int]
    settled_named_outcomes: list[int]


@dataclass
class RecurringSpec:
    cls: str
    underlying: str
    expiry: str
    target_price: float
    period: str


def parse_recurring_description(desc: str) -> RecurringSpec | None:
    if not desc.startswith("class:"):
        return None
    parts = dict(p.split(":", 1) for p in desc.split("|") if ":" in p)
    try:
        return RecurringSpec(
            cls=parts["class"],
            underlying=parts["underlying"],
            expiry=parts["expiry"],
            target_price=float(parts["targetPrice"]),
            period=parts["period"],
        )
    except KeyError:
        return None


def fetch_outcome_meta(base_url: str) -> tuple[list[OutcomeSpec], list[QuestionSpec]]:
    r = httpx.post(f"{base_url}/info", json={"type": "outcomeMeta"}, timeout=10.0)
    r.raise_for_status()
    data: dict[str, Any] = r.json()
    outcomes = [
        OutcomeSpec(
            outcome_id=o["outcome"],
            name=o["name"],
            description=o.get("description", ""),
            side_names=(o["sideSpecs"][0]["name"], o["sideSpecs"][1]["name"]),
        )
        for o in data.get("outcomes", [])
    ]
    questions = [
        QuestionSpec(
            question_id=q["question"],
            name=q["name"],
            description=q.get("description", ""),
            fallback_outcome=q["fallbackOutcome"],
            named_outcomes=q["namedOutcomes"],
            settled_named_outcomes=q.get("settledNamedOutcomes", []),
        )
        for q in data.get("questions", [])
    ]
    return outcomes, questions
