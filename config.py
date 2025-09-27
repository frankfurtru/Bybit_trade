import os
from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv()


@dataclass
class Config:
    # Telegram Bot
    telegram_bot_token: str = ""
    
    # Bybit API
    bybit_api_key: str = ""
    bybit_api_secret: str = ""
    bybit_testnet: bool = False
    bybit_environment: str = "demo"  # mainnet, testnet, demo, simulation
    public_only: bool = True  # Toggle for public-only mode
    
    # Multi-Exchange Support
    multi_exchange_enabled: bool = True  # Enable multi-exchange support
    default_exchange: str = "bybit"  # Default exchange to use
    available_exchanges: list = None  # List of available exchanges
    
    # ZAI (LLM) API
    zai_api_key: str = ""
    zai_base_url: str = "https://api.novita.ai/openai"
    llm_model: str = "openai/gpt-oss-120b"
    llm_router_model: str = ""  # optional lighter model for intent routing
    llm_temperature: float = 0.7
    llm_max_tokens: int = 131072
    
    # Bot Auth
    bot_auth_username: str = "admin"
    bot_auth_password: str = "admin123"
    bot_auth_store: str = "data/auth.json"
    bot_auth_required: bool = False  # Toggle for auth requirement
    
    # Enhanced configurations
    mcp_enabled: bool = True
    api_docs_path: str = "api-docs.txt"
    default_category: str = "spot"
    max_api_retries: int = 3
    
    # Simulation Mode Settings
    simulation_mode: bool = False
    simulation_balance: dict = None


def get_config() -> Config:
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    zai_api_key = os.getenv("ZAI_API_KEY", "").strip()
    zai_base_url = os.getenv("ZAI_BASE_URL", "https://api.novita.ai/openai").strip()
    llm_model = os.getenv("LLM_MODEL", "openai/gpt-oss-120b").strip()
    
    # Multi-exchange configuration
    multi_exchange_enabled = os.getenv("MULTI_EXCHANGE_ENABLED", "true").lower() == "true"
    default_exchange = os.getenv("DEFAULT_EXCHANGE", "bybit").lower()
    available_exchanges_str = os.getenv("AVAILABLE_EXCHANGES", "bybit,binance,kucoin,indodax,mexc,okx,bitfinex,gateio,kraken,huobi")
    available_exchanges = [x.strip() for x in available_exchanges_str.split(",")]
    llm_router_model = os.getenv("LLM_ROUTER_MODEL", "").strip()
    try:
        llm_temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    except ValueError:
        llm_temperature = 0.7
    try:
        llm_max_tokens = int(os.getenv("LLM_MAX_TOKENS", "4096"))
    except ValueError:
        llm_max_tokens = 4096
    bybit_api_key = os.getenv("BYBIT_API_KEY")
    bybit_api_secret = os.getenv("BYBIT_API_SECRET")
    bybit_testnet = os.getenv("BYBIT_TESTNET", "false").lower() == "true"
    auth_username = os.getenv("BOT_AUTH_USERNAME", "").strip()
    auth_password = os.getenv("BOT_AUTH_PASSWORD", "").strip()
    auth_store_path = os.getenv("BOT_AUTH_STORE", "data/auth.json").strip()
    
    # Enhanced configurations
    mcp_enabled = os.getenv("MCP_ENABLED", "true").lower() == "true"
    api_docs_path = os.getenv("API_DOCS_PATH", "api-docs.txt").strip()
    default_category = os.getenv("DEFAULT_CATEGORY", "spot").strip()
    try:
        max_api_retries = int(os.getenv("MAX_API_RETRIES", "3"))
    except ValueError:
        max_api_retries = 3

    # Configuration for public-only mode
    public_only = os.getenv("BYBIT_PUBLIC_ONLY", "true").lower() == "true"
    
    # Configuration for auth requirement
    bot_auth_required = os.getenv("BOT_AUTH_REQUIRED", "false").lower() == "true"
    
    # Auto-detect simulation mode based on API key validity
    bybit_environment = os.getenv("BYBIT_ENVIRONMENT", "demo").lower()
    simulation_mode = not bybit_api_key or bybit_api_key == 'egA0nUxhmZ6QMbPVV'
    simulation_balance = {
        "USDT": 10000.0,
        "BTC": 1.0,
        "ETH": 10.0
    } if simulation_mode else None
    
    if not telegram_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is required. Set it in .env")
    if not zai_api_key:
        # Allow running /start but LLM replies will be disabled until provided
        pass

    return Config(
        telegram_bot_token=telegram_token,
        zai_api_key=zai_api_key,
        zai_base_url=zai_base_url,
        llm_model=llm_model,
        llm_router_model=llm_router_model,
        llm_temperature=llm_temperature,
        llm_max_tokens=llm_max_tokens,
        bybit_api_key=bybit_api_key,
        bybit_api_secret=bybit_api_secret,
        bybit_testnet=bybit_testnet,
        public_only=public_only,
        multi_exchange_enabled=multi_exchange_enabled,
        default_exchange=default_exchange,
        available_exchanges=available_exchanges,
        bot_auth_username=auth_username,
        bot_auth_password=auth_password,
        bot_auth_store=auth_store_path,
        bot_auth_required=bot_auth_required,
        mcp_enabled=mcp_enabled,
        api_docs_path=api_docs_path,
        default_category=default_category,
        max_api_retries=max_api_retries,
        simulation_mode=simulation_mode,
        simulation_balance=simulation_balance
    )
