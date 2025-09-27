#!/usr/bin/env python3
"""
MCP Client untuk Telegram Bot
Menghubungkan Telegram bot dengan MCP server untuk akses multi-exchange
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
import httpx
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPClient:
    """Client untuk berinteraksi dengan MCP Server"""
    
    def __init__(self, mcp_base_url: str = "http://localhost:8001"):
        self.base_url = mcp_base_url
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()
    
    async def _make_request(self, endpoint: str, method: str = "GET", **kwargs) -> Dict[str, Any]:
        """Make HTTP request to MCP server"""
        try:
            url = f"{self.base_url}{endpoint}"
            
            if method.upper() == "GET":
                response = await self.http_client.get(url, params=kwargs)
            elif method.upper() == "POST":
                response = await self.http_client.post(url, json=kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except httpx.RequestError as e:
            logger.error(f"Request error to {url}: {e}")
            return {"success": False, "error": f"Request failed: {str(e)}"}
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} from {url}")
            return {"success": False, "error": f"HTTP {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"success": False, "error": str(e)}
    
    # === SERVER INFO ===
    
    async def get_server_info(self) -> Dict[str, Any]:
        """Get server information and available endpoints"""
        return await self._make_request("/")
    
    # === BYBIT PUBLIC ENDPOINTS ===
    
    async def get_bybit_tickers(self, category: str = "spot", symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get Bybit ticker information"""
        params = {"category": category}
        if symbol:
            params["symbol"] = symbol
        return await self._make_request("/bybit/tickers", **params)
    
    async def get_bybit_kline(self, category: str, symbol: str, interval: str = "1", limit: int = 5) -> Dict[str, Any]:
        """Get Bybit kline/candlestick data"""
        return await self._make_request("/bybit/kline", 
                                      category=category, symbol=symbol, 
                                      interval=interval, limit=limit)
    
    async def get_bybit_orderbook(self, category: str, symbol: str, limit: int = 10) -> Dict[str, Any]:
        """Get Bybit order book data"""
        return await self._make_request("/bybit/orderbook", 
                                      category=category, symbol=symbol, limit=limit)
    
    async def get_bybit_recent_trades(self, category: str, symbol: str, limit: int = 5) -> Dict[str, Any]:
        """Get Bybit recent trade data"""
        return await self._make_request("/bybit/recent-trades", 
                                      category=category, symbol=symbol, limit=limit)
    
    async def get_bybit_instruments(self, category: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get Bybit instrument information"""
        params = {"category": category}
        if symbol:
            params["symbol"] = symbol
        return await self._make_request("/bybit/instruments-info", **params)
    
    async def get_bybit_server_time(self) -> Dict[str, Any]:
        """Get Bybit server time"""
        return await self._make_request("/bybit/server-time")
    
    # === BYBIT PRIVATE ENDPOINTS ===
    
    async def get_bybit_wallet_balance(self, account_type: str = "UNIFIED") -> Dict[str, Any]:
        """Get Bybit wallet balance (requires API key)"""
        return await self._make_request("/bybit/wallet-balance", account_type=account_type)
    
    async def get_bybit_positions(self, category: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get Bybit position list (requires API key)"""
        params = {"category": category}
        if symbol:
            params["symbol"] = symbol
        return await self._make_request("/bybit/positions", **params)
    
    async def create_bybit_order(self, category: str, symbol: str, side: str, 
                               order_type: str, qty: str, price: Optional[str] = None) -> Dict[str, Any]:
        """Create Bybit order (requires API key)"""
        order_data = {
            "category": category,
            "symbol": symbol, 
            "side": side,
            "order_type": order_type,
            "qty": qty
        }
        if price:
            order_data["price"] = price
        return await self._make_request("/bybit/order", "POST", **order_data)
    
    # === MULTI-EXCHANGE ENDPOINTS ===
    
    async def get_binance_ticker(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get Binance ticker information"""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return await self._make_request("/exchanges/binance/ticker", **params)
    
    async def get_kucoin_ticker(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get KuCoin ticker information"""  
        params = {}
        if symbol:
            params["symbol"] = symbol
        return await self._make_request("/exchanges/kucoin/ticker", **params)
    
    async def get_okx_ticker(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get OKX ticker information"""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return await self._make_request("/exchanges/okx/ticker", **params)
    
    async def get_huobi_ticker(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get Huobi ticker information"""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return await self._make_request("/exchanges/huobi/ticker", **params)
    
    async def get_mexc_ticker(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get MEXC ticker information"""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return await self._make_request("/exchanges/mexc/ticker", **params)
    
    async def compare_exchange_prices(self, symbol: str, exchanges: str = "bybit,binance,kucoin") -> Dict[str, Any]:
        """Compare prices across multiple exchanges"""
        return await self._make_request("/exchanges/compare-prices", 
                                      symbol=symbol, exchanges=exchanges)
    
    # === DOCUMENTATION ===
    
    async def get_api_docs(self, section: Optional[str] = None) -> Dict[str, Any]:
        """Get API documentation context"""
        params = {}
        if section:
            params["section"] = section
        return await self._make_request("/api-docs", **params)

class TelegramMCPIntegration:
    """Integration layer antara Telegram bot dan MCP client"""
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
    
    async def format_price_response(self, data: Dict[str, Any], exchange: str = "bybit") -> str:
        """Format price data untuk response Telegram"""
        try:
            if not data.get("success", False):
                return f"❌ Error dari {exchange}: {data.get('error', 'Unknown error')}"
            
            if exchange == "bybit":
                # Format Bybit response
                result = data.get("data", {}).get("result", {})
                if "list" in result and result["list"]:
                    ticker = result["list"][0]
                    symbol = ticker.get("symbol", "Unknown")
                    price = float(ticker.get("lastPrice", 0))
                    change_24h = float(ticker.get("price24hPcnt", 0)) * 100
                    volume_24h = float(ticker.get("volume24h", 0))
                    
                    change_emoji = "🟢" if change_24h >= 0 else "🔴"
                    
                    return f"""
📊 **{symbol}** - Bybit
💰 Price: ${price:,.6f}
{change_emoji} 24h Change: {change_24h:+.2f}%
📈 24h Volume: {volume_24h:,.2f}
                    """.strip()
            
            elif exchange in ["binance", "mexc"]:
                # Format Binance/MEXC response
                ticker_data = data.get("data", {})
                if isinstance(ticker_data, list) and ticker_data:
                    ticker_data = ticker_data[0]
                
                symbol = ticker_data.get("symbol", "Unknown")
                price = float(ticker_data.get("lastPrice", 0))
                change_24h = float(ticker_data.get("priceChangePercent", 0))
                volume_24h = float(ticker_data.get("volume", 0))
                
                change_emoji = "🟢" if change_24h >= 0 else "🔴"
                
                return f"""
📊 **{symbol}** - {exchange.title()}
💰 Price: ${price:,.6f}
{change_emoji} 24h Change: {change_24h:+.2f}%
📈 24h Volume: {volume_24h:,.2f}
                """.strip()
            
            elif exchange == "kucoin":
                # Format KuCoin response
                ticker_data = data.get("data", {})
                if "data" in ticker_data:
                    ticker_data = ticker_data["data"]
                
                symbol = ticker_data.get("symbol", "Unknown")
                price = float(ticker_data.get("last", 0))
                change_24h = float(ticker_data.get("changeRate", 0)) * 100
                volume_24h = float(ticker_data.get("vol", 0))
                
                change_emoji = "🟢" if change_24h >= 0 else "🔴"
                
                return f"""
📊 **{symbol}** - KuCoin
💰 Price: ${price:,.6f}
{change_emoji} 24h Change: {change_24h:+.2f}%
📈 24h Volume: {volume_24h:,.2f}
                """.strip()
            
            else:
                return f"✅ Data received from {exchange}:\n```json\n{json.dumps(data, indent=2)}\n```"
                
        except Exception as e:
            return f"❌ Error formatting {exchange} data: {str(e)}"
    
    async def format_comparison_response(self, data: Dict[str, Any]) -> str:
        """Format price comparison untuk response Telegram"""
        try:
            if not data.get("success", False):
                return f"❌ Error: {data.get('error', 'Unknown error')}"
            
            symbol = data.get("symbol", "Unknown")
            exchanges = data.get("exchanges", {})
            analysis = data.get("analysis", {})
            
            response = f"💹 **Price Comparison for {symbol}**\n\n"
            
            # Exchange prices
            for exchange, price_data in exchanges.items():
                if isinstance(price_data, dict) and "price" in price_data:
                    price = price_data["price"]
                    change = price_data.get("change24h", 0)
                    change_emoji = "🟢" if change >= 0 else "🔴"
                    
                    response += f"**{exchange.title()}**: ${price:,.6f} {change_emoji}{change:+.2f}%\n"
                else:
                    response += f"**{exchange.title()}**: ❌ Error\n"
            
            # Analysis
            if analysis:
                min_price = analysis.get("min_price", 0)
                max_price = analysis.get("max_price", 0)
                spread_percent = analysis.get("spread_percent", 0)
                avg_price = analysis.get("avg_price", 0)
                
                response += f"\n📊 **Analysis:**\n"
                response += f"🔻 Lowest: ${min_price:,.6f}\n"
                response += f"🔺 Highest: ${max_price:,.6f}\n"
                response += f"📏 Spread: {spread_percent:.4f}%\n"
                response += f"📊 Average: ${avg_price:,.6f}\n"
            
            return response
            
        except Exception as e:
            return f"❌ Error formatting comparison: {str(e)}"
    
    async def handle_price_query(self, query: str) -> str:
        """Handle price queries dari Telegram"""
        try:
            # Parse query untuk extract symbol dan exchange
            parts = query.lower().split()
            symbol = "BTCUSDT"  # default
            exchange = "bybit"  # default
            
            # Extract symbol
            for part in parts:
                if any(coin in part.upper() for coin in ["BTC", "ETH", "SOL", "ADA"]):
                    if "USDT" not in part.upper():
                        symbol = f"{part.upper()}USDT"
                    else:
                        symbol = part.upper()
                    break
            
            # Extract exchange
            for part in parts:
                if part in ["bybit", "binance", "kucoin", "okx", "huobi", "mexc"]:
                    exchange = part
                    break
            
            # Special handling for comparison
            if "compare" in query.lower() or "vs" in query.lower():
                exchanges = "bybit,binance,kucoin"
                if "binance" in query.lower():
                    exchanges = "bybit,binance"
                
                data = await self.mcp_client.compare_exchange_prices(symbol, exchanges)
                return await self.format_comparison_response(data)
            
            # Single exchange query
            if exchange == "bybit":
                data = await self.mcp_client.get_bybit_tickers("spot", symbol)
            elif exchange == "binance":
                data = await self.mcp_client.get_binance_ticker(symbol)
            elif exchange == "kucoin":
                # Convert BTCUSDT to BTC-USDT for KuCoin
                kucoin_symbol = symbol.replace("USDT", "-USDT")
                data = await self.mcp_client.get_kucoin_ticker(kucoin_symbol)
            elif exchange == "okx":
                # Convert BTCUSDT to BTC-USDT for OKX
                okx_symbol = symbol.replace("USDT", "-USDT")
                data = await self.mcp_client.get_okx_ticker(okx_symbol)
            elif exchange == "mexc":
                data = await self.mcp_client.get_mexc_ticker(symbol)
            else:
                data = await self.mcp_client.get_bybit_tickers("spot", symbol)
            
            return await self.format_price_response(data, exchange)
            
        except Exception as e:
            return f"❌ Error processing query: {str(e)}"
    
    async def handle_balance_query(self) -> str:
        """Handle balance queries dari Telegram"""
        try:
            data = await self.mcp_client.get_bybit_wallet_balance()
            
            if not data.get("success", False):
                return f"❌ Error getting balance: {data.get('error', 'Unknown error')}"
            
            # Format balance response
            result = data.get("data", {}).get("result", {})
            if "list" in result and result["list"]:
                account = result["list"][0]
                total_equity = float(account.get("totalEquity", 0))
                total_wallet_balance = float(account.get("totalWalletBalance", 0))
                
                response = f"💰 **Wallet Balance**\n"
                response += f"Total Equity: ${total_equity:,.2f}\n"
                response += f"Total Balance: ${total_wallet_balance:,.2f}\n\n"
                
                # Coin details
                coins = account.get("coin", [])
                for coin in coins[:5]:  # Limit to 5 coins
                    coin_name = coin.get("coin", "")
                    wallet_balance = float(coin.get("walletBalance", 0))
                    if wallet_balance > 0:
                        response += f"**{coin_name}**: {wallet_balance:,.6f}\n"
                
                return response
            
            return "ℹ️ No balance data found"
            
        except Exception as e:
            return f"❌ Error getting balance: {str(e)}"

# Example usage untuk testing
async def test_mcp_integration():
    """Test MCP integration"""
    mcp_client = MCPClient()
    integration = TelegramMCPIntegration(mcp_client)
    
    try:
        # Test server info
        print("=== Server Info ===")
        server_info = await mcp_client.get_server_info()
        print(json.dumps(server_info, indent=2))
        
        # Test price query
        print("\n=== Price Query ===")
        response = await integration.handle_price_query("btc price bybit")
        print(response)
        
        # Test comparison
        print("\n=== Price Comparison ===")
        response = await integration.handle_price_query("compare btc prices")
        print(response)
        
    finally:
        await mcp_client.close()

if __name__ == "__main__":
    asyncio.run(test_mcp_integration())