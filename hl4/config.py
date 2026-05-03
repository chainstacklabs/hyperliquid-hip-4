import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    private_key: str
    address: str
    base_url: str
    ws_url: str
    evm_url: str


def load_config() -> Config:
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    pk = os.environ["HYPERLIQUID_TESTNET_PRIVATE_KEY"]
    addr = os.environ["TESTNET_WALLET_ADDRESS"]
    return Config(
        private_key=pk,
        address=addr,
        base_url=os.environ.get("HL_BASE_URL", "https://api.hyperliquid-testnet.xyz"),
        ws_url=os.environ.get("HL_WS_URL", "wss://api.hyperliquid-testnet.xyz/ws"),
        evm_url=os.environ.get("HL_EVM_URL", "https://rpc.hyperliquid-testnet.xyz/evm"),
    )
