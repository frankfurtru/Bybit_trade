# Bybit V5 Trading Bot + Multi-Exchange MCP Server

🚀 **Unified Trading Bot** dengan dual interface: **Telegram Bot** + **MCP Server** untuk integration dengan AI tools seperti Claude.

## 🎯 Overview

Sistem ini menggabungkan:
- **MCP Server** (Model Context Protocol) dengan FastAPI framework  
- **Telegram Bot** untuk mobile trading interface
- **Multi-Exchange Support** untuk 6 major exchanges
- **Natural Language Processing** untuk trading commands
- **Machine Learning** integration untuk market analysis

## ✨ Key Features

### 🤖 Dual Interface
- **Telegram Bot**: Mobile-first interface dengan natural language support
- **MCP Server**: HTTP API untuk integration dengan Claude/AI tools
- **Unified Backend**: Same trading engine untuk kedua interface

### 🌐 Multi-Exchange Support
- **Bybit** (Primary): Full V5 API - public + private endpoints
- **Binance**: Public market data API
- **KuCoin**: Public market data API  
- **OKX**: Public market data API
- **Huobi**: Public market data API
- **MEXC**: Public market data API

### 🧠 Intelligent Features
- **Natural Language**: "What's Bitcoin price?" → API calls
- **Price Comparison**: Real-time comparison across exchanges
- **API Documentation**: Contextual help dalam setiap response
- **Error Handling**: User-friendly error messages

## 🚀 Quick Start

### 1. Requirements
- Python 3.11+
- Create `.env` file (see configuration below)

### 2. Installation
```bash
git clone https://github.com/yourusername/bybit-trading-bot.git
cd bybit-trading-bot
pip install -r requirements.txt
```

### 3. Configuration

Create `.env` file:
```bash
# Required
TELEGRAM_BOT_TOKEN=your_telegram_token

# Optional for private endpoints
BYBIT_API_KEY=your_bybit_key
BYBIT_API_SECRET=your_bybit_secret
BYBIT_PUBLIC_ONLY=true  # Set false for trading

# LLM Integration
ZAI_API_KEY=your_llm_api_key
ZAI_BASE_URL=https://api.novita.ai/openai  # Default Novita GPT-OSS

# Optional
BOT_AUTH_REQUIRED=false
LLM_ROUTER_MODEL=your_router_model
```

### 4. Run the System

**Option 1: Telegram Bot Only**
```bash
python -m src.main
```

**Option 2: MCP Server Only**  
```bash
python tools/mcp_server.py
# Server: http://localhost:8001
```

**Option 3: Both (Recommended)**
```bash
# Terminal 1: Start MCP Server
python tools/mcp_server.py

# Terminal 2: Start Telegram Bot
python -m src.main
```

## 📱 Telegram Bot Usage

### Commands:
```bash
/start              # Initialize bot
/help               # Full command guide
/status             # System status

# Market Data
/price BTCUSDT bybit       # Get BTC price from Bybit
/price ETHUSDT binance     # Get ETH price from Binance  
/compare BTCUSDT           # Compare BTC across exchanges
/exchanges                 # List available exchanges

# Account (requires API key)
/balance                   # Wallet balance
/positions                 # Open positions
```

### Natural Language:
```bash
"Harga Bitcoin sekarang?"     # → Bybit BTC price
"Compare ETH prices"          # → Multi-exchange comparison  
"Show me SOL on KuCoin"       # → KuCoin SOL price
"What's my balance?"          # → Wallet balance
```

## 🔌 MCP Server Integration

### For Claude Desktop:

Add to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "bybit-trading": {
      "command": "python",
      "args": ["/path/to/bybit-trading-bot/tools/mcp_server.py"],
      "env": {
        "BYBIT_PUBLIC_ONLY": "true"
      }
    }
  }
}
```

### Direct HTTP Usage:
```bash
# Get Bybit ticker
curl "http://localhost:8001/bybit/tickers?category=spot&symbol=BTCUSDT"

# Compare prices across exchanges  
curl "http://localhost:8001/exchanges/compare-prices?symbol=BTCUSDT&exchanges=bybit,binance,kucoin"

# Get API documentation
curl "http://localhost:8001/api-docs?section=market"
```

## 🏗️ Project Structure

```
src/
├── main.py                    # Unified Telegram bot dengan MCP integration
├── bybit_client.py           # Bybit V5 API implementation
├── mcp_telegram_client.py    # MCP client untuk Telegram integration
├── llm.py                    # Natural language processing
├── telegram_bot.py           # Telegram bot core
├── exchange_client.py        # Multi-exchange API client
├── strategy.py              # Trading strategies  
├── model.py                 # Machine learning models
└── config.py                # Configuration management

tools/
└── mcp_server.py            # FastAPI-MCP server

scripts/
├── debug_llm.py             # LLM debugging
├── debug_tool_calls.py      # Tool call debugging
├── debug_specific_query.py  # Query testing
└── simple_llm_test.py       # LLM sanity test

docs/
├── MCP_TELEGRAM_INTEGRATION.md  # Detailed system documentation
├── natural_language_implementation.md
└── multi_exchange.md

data/
└── auth.json                # Local runtime data
```

## 🧪 Testing & Debugging

### Test Individual Components:
```bash
# Test LLM integration
python scripts/debug_llm.py
python scripts/simple_llm_test.py

# Test tool calls
python scripts/debug_tool_calls.py

# Test specific queries
python scripts/debug_specific_query.py

# Test natural language
python test_true_natural.py
```

### Test MCP Server:
```bash
# Start server
python tools/mcp_server.py

# Test endpoints
curl http://localhost:8001/
curl "http://localhost:8001/bybit/tickers?category=spot"
curl "http://localhost:8001/exchanges/compare-prices?symbol=BTCUSDT"
```

## 🎯 What's New in This Version

✅ **Complete MCP Rewrite**: Migrated dari custom implementation ke FastAPI-MCP framework  
✅ **Multi-Exchange Integration**: 6 major exchanges dengan unified interface  
✅ **Dual Interface**: Telegram Bot + MCP Server dalam satu system  
✅ **API Documentation Context**: Contextual help dalam setiap response  
✅ **Enhanced Error Handling**: User-friendly error messages  
✅ **Natural Language**: Advanced LLM integration untuk command parsing  

## 🔒 Security & Best Practices

### API Key Management:
- Use environment variables untuk API keys
- Never commit keys to repository  
- Use testnet untuk development
- `BYBIT_PUBLIC_ONLY=true` untuk safe testing

### Rate Limiting:
- Built-in rate limiting untuk semua exchanges
- Auto-retry dengan exponential backoff
- Request queueing untuk high-volume usage

## 📄 Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌────────────────┐
│   Telegram Bot  │◄──►│   MCP Client     │◄──►│   MCP Server   │
│                 │    │                  │    │                │
│ • Commands      │    │ • HTTP Client    │    │ • FastAPI      │
│ • Natural Lang  │    │ • Response Format│    │ • Multi-CEX    │
│ • LLM Chat      │    │ • Error Handling │    │ • API Docs     │
└─────────────────┘    └──────────────────┘    └────────────────┘
                                                        │
                                                        ▼
                              ┌────────────────────────────────────┐
                              │         Exchange APIs              │
                              │ • Bybit (V5)  • Binance          │
                              │ • KuCoin      • OKX               │
                              │ • Huobi       • MEXC              │
                              └────────────────────────────────────┘
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch  
3. Implement changes dengan proper tests
4. Update documentation
5. Submit pull request

## 📄 License

MIT License - see LICENSE file for details.

## ⚠️ Disclaimer

This software is for educational purposes. Trading cryptocurrencies involves substantial risk. Always do your own research and never invest more than you can afford to lose.

---

**🚀 Happy Trading with Multi-Exchange MCP Integration!**
- To enable trading and other private endpoints, set `BYBIT_PUBLIC_ONLY=false` and provide valid API keys.
- For faster small-talk replies, consider a lighter `LLM_ROUTER_MODEL` and smaller `LLM_MAX_TOKENS` (e.g., 512–2048).

Run MCP Server (optional)

- Install deps: `pip install -r requirements.txt`
- Start server: `python -m tools.mcp_server`
- The server exposes two example tools: `health_check` and `echo`. Extend to call `ZaiClient` or Bybit.

Telegram Commands

- `/start` and `/help`: Info bantuan.
- `/time`: Server time Bybit (public, production).
- `/ticker <category> [symbol]`: Ticker market V5, kategori `spot|linear|inverse|option`.
- `/balance [COIN]`: Wallet balance V5 (private, default `accountType=UNIFIED`).
- `/signal <category> <symbol> <interval> <mode>`: Prediksi XGBoost (scalping/swing) dari kline terkini.
- `/ask <pertanyaan>`: Natural language router → LLM memilih aksi (tickers, kline, orderbook, trades, balance, positions, orders, create/cancel order) dan bot mengeksekusi.
