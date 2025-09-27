#!/usr/bin/env python3
"""
Enhanced Bybit Telegram Bot
Bot yang memahami konteks API docs dan memberikan data real-time Bybit
Dengan respons yang jelas saat fitur private diminta pada mode publik.
"""

import asyncio
import json
import logging
import os
import sys
import re
import fcntl
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ChatAction

# Import modules
from config import get_config
from llm import ZaiClient, LLMError
from bybit_client import BybitClient, BybitConfig
from auth import AuthStore, AuthConfig
from natural_trading_assistant import TradingToolsRegistry
from exchange_client import ExchangeClient

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# API Documentation context for LLM
API_DOCS_CONTEXT = """
# Bybit V5 API Documentation Summary

## Available Endpoints:
1. **Market Data** (Public):
   - /v5/market/time - Server time
   - /v5/market/tickers - Get ticker data for symbols
   - /v5/market/kline - Get kline/candlestick data
   - /v5/market/orderbook - Get order book
   - /v5/market/recent-trade - Get recent trades

2. **Account Data** (Private - requires authentication):
   - /v5/account/wallet-balance - Get wallet balance
   - /v5/position/list - Get positions
   - /v5/order/realtime - Get active orders

3. **Trading** (Private):
   - /v5/order/create - Place orders
   - /v5/order/cancel - Cancel orders
   - /v5/position/set-leverage - Set leverage

## Response Format:
All endpoints return JSON with:
- retCode: 0 for success
- retMsg: Success message or error description
- result: Actual data
"""

class EnhancedTelegramBot:
    """Enhanced Telegram bot dengan natural language understanding"""

    def __init__(self):
        self.config = get_config()
        self.auth_store = AuthStore(AuthConfig(
            username=self.config.bot_auth_username,
            password=self.config.bot_auth_password,
            store_path=self.config.bot_auth_store
        ))

        # Initialize LLM client
        if self.config.zai_api_key:
            self.llm_client = ZaiClient(
                api_key=self.config.zai_api_key,
                base_url=self.config.zai_base_url,
                default_model=self.config.llm_model,
                temperature=self.config.llm_temperature,
                max_tokens=self.config.llm_max_tokens,
            )
        else:
            self.llm_client = None
            logger.warning("No ZAI API key provided. LLM features will be disabled.")

        # Initialize Bybit client
        self.bybit_client = BybitClient(BybitConfig(
            api_key=self.config.bybit_api_key,
            api_secret=self.config.bybit_api_secret,
            testnet=self.config.bybit_testnet,
            public_only=self.config.public_only
        ))

        # Initialize multi-exchange support
        self.exchange_client = ExchangeClient()
        self.tools_registry = TradingToolsRegistry(self.exchange_client, self.bybit_client)

        logger.info(f"🤖 Enhanced Telegram Bot initialized")
        logger.info(f"📊 Public Mode: {self.config.public_only}")
        logger.info(f"🔄 Multi-Exchange: {self.config.multi_exchange_enabled}")
        logger.info(f"🧠 LLM Enabled: {self.llm_client is not None}")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id

        welcome_msg = f"""
🚀 **Enhanced Bybit Trading Bot**

👋 Halo! Saya adalah bot trading yang canggih dengan dukungan multi-exchange dan natural language understanding.

🌟 **Fitur Utama:**
• 📊 Data real-time dari multiple exchanges
• 🧠 Natural language queries (AI-powered)
• 💹 Analisis harga dan arbitrage
• 🔄 Multi-exchange comparison

💬 **Cara Penggunaan:**
Kirim pesan apapun dalam bahasa natural, contoh:
• "Harga Bitcoin sekarang?"
• "Compare BTC prices across exchanges"
• "Show me top 5 CEX prices for BTC"
• "Arbitrage opportunities for ETH"

🔐 **Mode:** {'🔓 Public Only' if self.config.public_only else '🔒 Full Access'}
🌐 **Exchanges:** {', '.join(self.config.available_exchanges[:5])}{'...' if len(self.config.available_exchanges) > 5 else ''}

✨ Mulai bertanya apapun tentang crypto trading!
        """

        await update.message.reply_text(welcome_msg, parse_mode='Markdown')

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_msg = """
🆘 **Bantuan & Panduan**

🗣️ **Natural Language Queries:**
• "Harga Bitcoin hari ini"
• "Compare ETH between Binance and Bybit"
• "Show me top 5 exchange prices for BTC"
• "What are arbitrage opportunities?"
• "Market overview for BTC and ETH"

📊 **Commands Available:**
• `/start` - Memulai bot
• `/help` - Panduan ini
• `/status` - Status bot dan koneksi
• `/exchanges` - List exchange yang didukung

🌐 **Multi-Exchange Support:**
Bot mendukung multiple exchanges dan bisa membandingkan harga secara real-time.

💡 **Tips:**
• Gunakan bahasa natural (Indonesia/English)
• Bot memahami konteks trading
• Tanya apapun tentang crypto prices, exchanges, arbitrage

❓ Masih bingung? Langsung tanya aja!
        """

        await update.message.reply_text(help_msg, parse_mode='Markdown')

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        try:
            # Test connections
            server_time = await self.bybit_client.get_server_time()

            status_msg = f"""
📊 **Bot Status**

🔗 **Koneksi:**
• Bybit API: ✅ Connected
• Server Time: `{server_time.get('time', 'N/A')}`

🤖 **Bot Config:**
• Mode: {'🔓 Public' if self.config.public_only else '🔒 Private'}
• LLM: {'✅ Active' if self.llm_client else '❌ Disabled'}
• Multi-Exchange: {'✅ Enabled' if self.config.multi_exchange_enabled else '❌ Disabled'}

🌐 **Exchanges Aktif:**
{chr(10).join([f'• {ex.title()}' for ex in self.config.available_exchanges[:8]])}

✅ Semua sistem normal!
            """

        except Exception as e:
            status_msg = f"""
📊 **Bot Status**

❌ **Error:**
```
{str(e)}
```

🔧 **Troubleshooting:**
• Cek koneksi internet
• Verifikasi API credentials
• Restart bot jika perlu
            """

        await update.message.reply_text(status_msg, parse_mode='Markdown')

    async def exchanges_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /exchanges command"""
        exchanges_msg = f"""
🌐 **Supported Exchanges**

📈 **Available Exchanges:** {len(self.config.available_exchanges)}

{chr(10).join([f'• **{ex.title()}** - Real-time data' for ex in self.config.available_exchanges])}

💡 **Usage Examples:**
• "Compare BTC on Binance vs Bybit"
• "Show me ETH prices across all exchanges"
• "Which exchange has cheapest BTC?"

🔄 **Multi-Exchange Features:**
• Price comparison
• Arbitrage analysis
• Top exchange rankings
• Real-time market data

Tanya apapun tentang exchanges!
        """

        await update.message.reply_text(exchanges_msg, parse_mode='Markdown')

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle natural language messages"""
        user_id = update.effective_user.id
        message_text = update.message.text

        # Show typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

        logger.info(f"User {user_id}: {message_text}")

        try:
            # Check if LLM is available
            if not self.llm_client:
                await update.message.reply_text(
                    "❌ LLM service tidak tersedia. Silakan hubungi admin.",
                    parse_mode='Markdown'
                )
                return

            # Process with natural language understanding
            response = await self._process_natural_language_query(message_text)

            # Send response
            if len(response) > 4000:
                # Split long messages
                chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
                for chunk in chunks:
                    await update.message.reply_text(chunk, parse_mode='Markdown')
            else:
                await update.message.reply_text(response, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            await update.message.reply_text(
                f"❌ Terjadi error saat memproses pesan:\n```\n{str(e)}\n```",
                parse_mode='Markdown'
            )

    async def _process_natural_language_query(self, query: str) -> str:
        """Process natural language query using LLM and trading tools"""

        try:
            # Build comprehensive system prompt
            system_prompt = f"""You are an expert cryptocurrency trading assistant with access to real-time data from multiple exchanges.

AVAILABLE EXCHANGES: {', '.join(self.config.available_exchanges)}

AVAILABLE TOOLS:
1. get_price(symbol, exchange) - Get price from specific exchange
2. compare_top_exchanges(symbol, count) - Compare prices across top N exchanges
3. get_multiple_prices(symbol, exchanges) - Get prices from specific exchanges list
4. analyze_arbitrage(symbol, exchanges) - Find arbitrage opportunities
5. get_market_overview(symbols, exchanges) - Multi-symbol overview

UNDERSTANDING RULES:
- If user asks for "top N" or "best N" exchanges: use compare_top_exchanges
- If user compares specific exchanges: use get_multiple_prices
- If user asks about arbitrage/opportunities: use analyze_arbitrage
- If user asks about multiple cryptocurrencies: use get_market_overview
- If user asks about single exchange: use get_price

CRITICAL: Understand natural language context:
- "show me BTC prices on top 5 CEX" = compare_top_exchanges(BTC, 5)
- "compare ETH Binance vs KuCoin" = get_multiple_prices(ETH, [binance, kucoin])
- "arbitrage for Bitcoin" = analyze_arbitrage(BTC, all_exchanges)
- "harga Bitcoin terbaik" = compare_top_exchanges(BTC, 5)

MODE: {'Public Only - Real-time market data available' if self.config.public_only else 'Full Access - All features available'}

Respond in a helpful, professional manner with rich formatting using emojis and markdown.
"""

            # Get LLM understanding of the query
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ]

            # First, get LLM understanding of what to do
            understanding_prompt = f"""Analyze this trading query and determine the best action:

Query: "{query}"

Respond with JSON:
{{
    "understanding": "what user wants",
    "action": "tool_name_to_use",
    "parameters": {{"param1": "value1"}},
    "reasoning": "why this tool and parameters"
}}"""

            understanding_response = await asyncio.to_thread(
                self.llm_client.chat,
                [{"role": "user", "content": understanding_prompt}],
                temperature=0.1,
                max_tokens=1000
            )

            # Parse understanding
            understanding = self._parse_json_response(understanding_response)

            # Execute based on understanding
            action = understanding.get("action", "compare_top_exchanges")
            parameters = understanding.get("parameters", {})

            logger.info(f"LLM Understanding: {understanding.get('understanding')}")
            logger.info(f"Action: {action}, Parameters: {parameters}")

            # Execute the tool
            if action == "compare_top_exchanges":
                symbol = parameters.get("symbol", "BTC")
                count = parameters.get("count", 5)
                result = await self.tools_registry.execute_tool("compare_top_exchanges", {
                    "symbol": symbol,
                    "count": count
                })
            elif action == "get_multiple_prices":
                symbol = parameters.get("symbol", "BTC")
                exchanges = parameters.get("exchanges", ["binance", "bybit"])
                result = await self.tools_registry.execute_tool("get_multiple_prices", {
                    "symbol": symbol,
                    "exchanges": exchanges
                })
            elif action == "analyze_arbitrage":
                symbol = parameters.get("symbol", "BTC")
                exchanges = parameters.get("exchanges", self.config.available_exchanges[:5])
                result = await self.tools_registry.execute_tool("analyze_arbitrage", {
                    "symbol": symbol,
                    "exchanges": exchanges
                })
            elif action == "get_price":
                symbol = parameters.get("symbol", "BTC")
                exchange = parameters.get("exchange", "binance")
                result = await self.tools_registry.execute_tool("get_price", {
                    "symbol": symbol,
                    "exchange": exchange
                })
            elif action == "get_market_overview":
                symbols = parameters.get("symbols", ["BTC"])
                exchanges = parameters.get("exchanges", self.config.available_exchanges[:3])
                result = await self.tools_registry.execute_tool("get_market_overview", {
                    "symbols": symbols,
                    "exchanges": exchanges
                })
            else:
                result = {"success": False, "error": f"Unknown action: {action}"}

            # Format response with LLM
            if result.get("success"):
                format_prompt = f"""Format this trading data into a natural, informative response.

User Query: "{query}"
User Intent: {understanding.get('understanding', '')}
Tool Result: {json.dumps(result, indent=2)}

Create a well-formatted response with:
- Use emojis appropriately (🏆 for rankings, 💰 for prices, 📊 for data)
- Show clear rankings for top exchanges if relevant
- Include price spread analysis if relevant
- Add insights about arbitrage opportunities
- Use professional but engaging tone
- Include timestamp

Respond in {'Indonesian' if any(word in query.lower() for word in ['harga', 'berapa', 'mana', 'dimana']) else 'English'}.
"""

                formatted_response = await asyncio.to_thread(
                    self.llm_client.chat,
                    [{"role": "user", "content": format_prompt}],
                    temperature=0.2,
                    max_tokens=2000
                )

                return formatted_response
            else:
                return f"❌ Error: {result.get('error', 'Unknown error occurred')}"

        except Exception as e:
            logger.error(f"Error in natural language processing: {e}", exc_info=True)
            return f"❌ Error processing query: {str(e)}"

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON response from LLM safely"""
        try:
            # Clean response
            response = response.strip()

            # Extract JSON block if present
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                if end != -1:
                    response = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                if end != -1:
                    response = response[start:end].strip()

            return json.loads(response)

        except Exception as e:
            logger.error(f"Error parsing JSON: {e}")
            # Return fallback
            return {
                "understanding": "Parse error - fallback mode",
                "action": "compare_top_exchanges",
                "parameters": {"symbol": "BTC", "count": 5},
                "reasoning": "JSON parse failed"
            }

    def run(self):
        """Run the Telegram bot"""
        application = Application.builder().token(self.config.telegram_bot_token).build()

        # Add handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(CommandHandler("exchanges", self.exchanges_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        logger.info("🚀 Starting Telegram bot...")
        application.run_polling()

def main():
    """Main function"""
    try:
        bot = EnhancedTelegramBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error starting bot: {e}", exc_info=True)

if __name__ == "__main__":
    main()