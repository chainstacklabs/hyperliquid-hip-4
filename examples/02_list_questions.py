"""List HIP-4 categorical questions (multi-outcome markets).

A `question` groups N binary `outcome` legs plus a fallback ("Other"). To take
a directional view that "X will win this category", you buy YES on the leg whose
outcome_id matches X (or sell that side's NO). The fallback leg captures the
"none of the named options" case."""

from rich.console import Console

from hl4 import fetch_outcome_meta, load_config


def main() -> None:
    cfg = load_config()
    outcomes, questions = fetch_outcome_meta(cfg.base_url)
    by_id = {o.outcome_id: o for o in outcomes}

    c = Console()
    if not questions:
        c.print("[yellow]no questions live on this network[/yellow]")
        return

    for q in questions:
        c.rule(f"Q{q.question_id}: {q.name}")
        c.print(f"[dim]{q.description}[/dim]")
        c.print(f"  [bold]Named outcomes:[/bold]")
        for oid in q.named_outcomes:
            o = by_id.get(oid)
            label = f"{o.name} ({o.side_names[0]} / {o.side_names[1]})" if o else "?"
            settled = "  [green]SETTLED[/green]" if oid in q.settled_named_outcomes else ""
            c.print(f"    - outcome={oid}  {label}{settled}")
        fb = by_id.get(q.fallback_outcome)
        c.print(f"  [bold]Fallback:[/bold] outcome={q.fallback_outcome}  {fb.name if fb else '?'}")


if __name__ == "__main__":
    main()
