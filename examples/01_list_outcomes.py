"""List every HIP-4 outcome market on the configured network."""

from rich.console import Console
from rich.table import Table

from hl4 import fetch_outcome_meta, load_config, parse_recurring_description


def main() -> None:
    cfg = load_config()
    outcomes, _ = fetch_outcome_meta(cfg.base_url)

    table = Table(title=f"HIP-4 outcomes @ {cfg.base_url}")
    for col in ("id", "name", "side[0]", "side[1]", "asset_id(0)", "coin(0)", "spec"):
        table.add_column(col)

    for o in outcomes:
        rec = parse_recurring_description(o.description)
        spec = (
            f"{rec.underlying} target={rec.target_price} expiry={rec.expiry} period={rec.period}"
            if rec
            else o.description[:60]
        )
        table.add_row(
            str(o.outcome_id),
            o.name,
            o.side_names[0],
            o.side_names[1],
            str(o.asset_id(0)),
            o.coin(0),
            spec,
        )

    Console().print(table)


if __name__ == "__main__":
    main()
