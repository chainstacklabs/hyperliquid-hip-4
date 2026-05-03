# Hyperliquid HIP-4 — Learning examples + market-maker bot

> **Built with [Chainstack](https://chainstack.com).** Managed RPC for Hyperliquid — HyperEVM `/evm` (default, hl-node-compliant) and `/nanoreth` (with system transactions) on a single endpoint, plus a subset of HyperCore `/info` queries. Get a private node from the [console](https://console.chainstack.com), browse the [Hyperliquid RPC reference](https://docs.chainstack.com/reference/blockchain-apis), or point your AI agent at the [Chainstack MCP server](https://mcp.chainstack.com) (`get mcp.chainstack.com`) to deploy and manage nodes from your IDE.

---

Standalone Python scripts for every primitive operation on Hyperliquid's
**HIP-4 outcome markets** (binary prediction / event contracts), plus a small
passive market-maker bot. Targets testnet by default.

> HIP-4 went live on mainnet 2026-05-02. Currently the only production market
> is a recurring BTC daily binary; testnet additionally has a HYPE 15-min
> binary and several validator-deployed test markets including a categorical
> "what will Hypurr eat" question.

## Quick start

```bash
uv sync
cp .env.example .env   # then fill in HYPERLIQUID_TESTNET_PRIVATE_KEY + TESTNET_WALLET_ADDRESS

# get USDH for the wallet (HIP-4 settles in USDH, the faucet pays USDC)
uv run python examples/00_get_usdh.py --amount 50

# explore
uv run python examples/01_list_outcomes.py
uv run python examples/02_list_questions.py
uv run python examples/03_account_state.py
uv run python examples/04_orderbook_snapshot.py --outcome 5915
```

## Examples

| # | Script | Purpose |
|---|---|---|
| 00 | `00_get_usdh.py` | Buy USDH for USDC on the `@1338` spot pair |
| 01 | `01_list_outcomes.py` | Enumerate all outcome markets via `outcomeMeta` |
| 02 | `02_list_questions.py` | List categorical questions and their named legs |
| 03 | `03_account_state.py` | Show USDC, USDH, and outcome side balances |
| 04 | `04_orderbook_snapshot.py` | REST top-of-book for both YES and NO sides |
| 05 | `05_ws_subscribe.py` | Live WebSocket l2Book + trades feed |
| 06 | `06_place_limit_order.py` | Resting GTC limit order |
| 07 | `07_cancel_order.py` | Cancel by oid or all opens for a coin |
| 08 | `08_modify_order.py` | Modify an open order's price/size |
| 09 | `09_close_position.py` | Cross the book IOC to flatten |
| 10 | `10_categorical_trade.py` | Trade a single leg of a question |
| 11 | `11_mint_burn_demo.py` | Explainer of mint/burn/normal-trade fee classes |
| 12 | `12_wait_for_settlement.py` | Hold to expiry, observe auto-settlement |

## Bot

```bash
# market-make BTC daily and HYPE 15-min binaries simultaneously
uv run python -m bot.market_maker --outcomes 5915,5969 \
    --quote-notional 12 --half-spread 0.04 --max-inventory 30 --tick 5
```

The bot:
- Quotes both YES and NO books on each configured outcome.
- Computes a fair from each book's mid; falls back to `1 - p` from the opposite
  side when one side has empty bids/asks (common on illiquid outcomes).
- Sizes orders to a target notional in USDH (defaults to ~$12, just above the
  $10 server min).
- Caps inventory per side; once at the cap it stops adding bids on that side.
- Cancels-and-replaces only when the desired price drifts more than
  `--repost-threshold`.
- On Ctrl+C, cancels every open order before exiting.

## Notes on the design (read this first)

### Asset ID encoding
For an `outcomeId` and `side` (YES=0, NO=1):

```
encoding     = 10 * outcomeId + side
asset_id     = 100_000_000 + encoding
trade_coin   = "#{encoding}"   # used for l2Book / order placement
balance_coin = "+{encoding}"   # used in spotClearinghouseState balances
```

**Two coin string forms exist for the same side asset.** The `#` form is what
the `/info` endpoint expects for `l2Book` and what `Exchange.order(...)` takes;
the `+` form is what shows up under your account in `spotClearinghouseState`.
Mixing them up will silently fail to find your position. `hl4.outcomes` exposes
`encode_coin` and `encode_balance_coin` for the two cases.

BTC daily YES (outcome 5915) → trade `#59150`, balance `+59150`, asset_id `100_059_150`.

### SDK doesn't know about HIP-4 yet
`hyperliquid-python-sdk` v0.23.0 has no HIP-4 support. The shared module
`hl4.client.make_clients()` patches the SDK's `Info` and `Exchange` instances
by injecting `coin_to_asset` and `name_to_coin` entries for every live outcome
fetched via `outcomeMeta`. Once injected, normal `Exchange.order(...)` calls
work unchanged.

### USDH not USDC
HIP-4 settles in **USDH** (token id 1452 on testnet). The faucet pays USDC, so
script `00_get_usdh.py` swaps USDC → USDH on spot pair `@1338` (~1:1).

### Min notional
Server enforces a **$10 USDH minimum** per order. Below that you'll get
`"Order must have minimum value of 10 USDH"`.

### Sizes are integer
Outcome side coins use **integer size precision** on testnet (book sizes show
as `27.0`, `1024.0` etc.). The bot rounds up to integers; if you place orders
manually with fractional sizes you'll get `"Order has invalid size"`.

### Price bounds
Outcome prices are constrained to `0.001 .. 0.999` (probabilities, not raw
prices). The price tick on the BTC binary is `0.0001` (e.g. `0.4235`); the bot
defaults to `0.001` for safety.

### No split / merge primitive
Unlike Polymarket (Gnosis CTF), there is no `splitPosition` or
`mergePositions` API. To get YES exposure you place a buy on the YES book; to
get short-YES exposure you buy NO. Mint and burn happen *implicitly* inside
the matching engine as a side-effect of fills:

| Engine classification | When it happens | Fee |
|---|---|---|
| MINT | both counterparties had no prior position | 0 |
| NORMAL | one side opens, the other closes | fee on the opener / taker |
| BURN | both counterparties hold the opposite side and unwind together | both sides (or taker only) |
| SETTLEMENT | at expiry, oracle credits 0 or 1 USDH | `settle_fraction × sz` |

See `examples/11_mint_burn_demo.py` for the full explainer.

### No claim/redeem call at expiry
Settlement is automatic — at expiry, USDH credits land in the account. No
script needed; `12_wait_for_settlement.py` just polls the balance to show this.

## Disclaimer

This code is provided **as is**, for educational purposes only, with no
warranties of any kind. Nothing here is financial advice. HIP-4 went live
on mainnet days before this was written — the API surface, fee model, and
market roster may shift without notice. You are solely responsible for any
funds, keys, or trades involved in running this code. The authors and
Chainstack accept no liability for losses, errors, or any other consequences
arising from its use.

