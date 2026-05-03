from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info

from hl4.config import Config
from hl4.outcomes import encode_asset_id, encode_coin, fetch_outcome_meta


def make_clients(cfg: Config, *, hydrate_outcomes: bool = True) -> tuple[Info, Exchange]:
    """Build an Info + Exchange pair pointed at the configured base_url, with the
    outcome-market coin/asset mapping injected so SDK helpers can resolve them
    by coin string. The SDK does not yet know about HIP-4, so we patch it."""
    account = Account.from_key(cfg.private_key)
    info = Info(cfg.base_url, skip_ws=True)
    exchange = Exchange(account, cfg.base_url, account_address=cfg.address)
    if hydrate_outcomes:
        outcomes, _ = fetch_outcome_meta(cfg.base_url)
        for o in outcomes:
            for side in (0, 1):
                coin = encode_coin(o.outcome_id, side)
                asset_id = encode_asset_id(o.outcome_id, side)
                info.coin_to_asset[coin] = asset_id
                info.name_to_coin[coin] = coin
                exchange.info.coin_to_asset[coin] = asset_id
                exchange.info.name_to_coin[coin] = coin
    return info, exchange
