#!/usr/bin/env python3
"""
Enhanced Natural Language Trading Assistant
Menggunakan proper MCP tools integration dengan LLM yang benar-benar memahami context
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime

from llm import ZaiClient, LLMError
from exchange_client import ExchangeClient
from bybit_client import BybitClient, BybitConfig
from config import get_config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradingToolsRegistry:
    """Registry untuk semua trading tools yang tersedia"""
    
    def __init__(self, exchange_client: ExchangeClient, bybit_client: BybitClient):
        self.exchange_client = exchange_client
        self.bybit_client = bybit_client
        self.tools = {}
        self._register_tools()
    
    def _register_tools(self):
        """Register semua tools yang tersedia"""
        
        # Tool untuk get single price
        self.tools["get_price"] = {
            "name": "get_price",
            "description": "Get current price of a cryptocurrency from a specific exchange",
            "parameters": {
                "symbol": {"type": "string", "description": "Cryptocurrency symbol (e.g., BTC, ETH)"},
                "exchange": {"type": "string", "description": "Exchange name (bybit, binance, kucoin, etc.)"}
            },
            "function": self._get_price
        }
        
        # Tool untuk get multiple prices
        self.tools["get_multiple_prices"] = {
            "name": "get_multiple_prices", 
            "description": "Get prices of a cryptocurrency from multiple exchanges",
            "parameters": {
                "symbol": {"type": "string", "description": "Cryptocurrency symbol (e.g., BTC, ETH)"},
                "exchanges": {"type": "array", "items": {"type": "string"}, "description": "List of exchange names"}
            },
            "function": self._get_multiple_prices
        }
        
        # Tool untuk get top exchanges comparison
        self.tools["compare_top_exchanges"] = {
            "name": "compare_top_exchanges",
            "description": "Compare prices across top exchanges for a cryptocurrency",
            "parameters": {
                "symbol": {"type": "string", "description": "Cryptocurrency symbol (e.g., BTC, ETH)"},
                "count": {"type": "integer", "description": "Number of top exchanges to compare (default: 5)"}
            },
            "function": self._compare_top_exchanges
        }
        
        # Tool untuk get market overview
        self.tools["get_market_overview"] = {
            "name": "get_market_overview",
            "description": "Get market overview with multiple cryptocurrencies and exchanges",
            "parameters": {
                "symbols": {"type": "array", "items": {"type": "string"}, "description": "List of cryptocurrency symbols"},
                "exchanges": {"type": "array", "items": {"type": "string"}, "description": "List of exchange names"}
            },
            "function": self._get_market_overview
        }
        
        # Tool untuk server time
        self.tools["get_server_time"] = {
            "name": "get_server_time",
            "description": "Get server time from specific exchange",
            "parameters": {
                "exchange": {"type": "string", "description": "Exchange name"}
            },
            "function": self._get_server_time
        }
        
        # Tool untuk analysis dan insights
        self.tools["analyze_arbitrage"] = {
            "name": "analyze_arbitrage",
            "description": "Analyze arbitrage opportunities between exchanges",
            "parameters": {
                "symbol": {"type": "string", "description": "Cryptocurrency symbol"},
                "exchanges": {"type": "array", "items": {"type": "string"}, "description": "Exchanges to analyze"}
            },
            "function": self._analyze_arbitrage
        }
    
    async def _get_price(self, symbol: str, exchange: str) -> Dict[str, Any]:
        """Get price dari single exchange"""
        try:
            result = await self.exchange_client.get_ticker(symbol, exchange)
            formatted = self.exchange_client.format_ticker_response(result)
            return {
                "success": True,
                "data": formatted,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _get_multiple_prices(self, symbol: str, exchanges: List[str]) -> Dict[str, Any]:
        """Get price dari multiple exchanges"""
        try:
            tasks = []
            for exchange in exchanges:
                tasks.append(self.exchange_client.get_ticker(symbol, exchange))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            formatted_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    formatted_results.append({
                        "exchange": exchanges[i],
                        "error": str(result)
                    })
                else:
                    formatted = self.exchange_client.format_ticker_response(result)
                    formatted_results.append(formatted)
            
            return {
                "success": True,
                "symbol": symbol,
                "data": formatted_results,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _compare_top_exchanges(self, symbol: str, count: int = 5) -> Dict[str, Any]:
        """Compare price across top exchanges"""
        try:
            # Get top exchanges
            top_exchanges = self.exchange_client.get_supported_exchanges()[:count]
            
            # Get prices from all exchanges
            result = await self._get_multiple_prices(symbol, top_exchanges)
            
            if not result["success"]:
                return result
            
            # Sort by price untuk find best prices
            valid_prices = []
            for item in result["data"]:
                if "error" not in item and "price" in item:
                    try:
                        price_float = float(str(item["price"]).replace(",", ""))
                        valid_prices.append({
                            **item,
                            "price_float": price_float
                        })
                    except:
                        continue
            
            # Sort by price
            valid_prices.sort(key=lambda x: x["price_float"])
            
            return {
                "success": True,
                "symbol": symbol,
                "comparison": valid_prices,
                "lowest_price": valid_prices[0] if valid_prices else None,
                "highest_price": valid_prices[-1] if valid_prices else None,
                "price_spread": {
                    "amount": valid_prices[-1]["price_float"] - valid_prices[0]["price_float"] if len(valid_prices) > 1 else 0,
                    "percentage": ((valid_prices[-1]["price_float"] - valid_prices[0]["price_float"]) / valid_prices[0]["price_float"] * 100) if len(valid_prices) > 1 else 0
                },
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _get_market_overview(self, symbols: List[str], exchanges: List[str]) -> Dict[str, Any]:
        """Get comprehensive market overview"""
        try:
            overview = {}
            
            for symbol in symbols:
                symbol_data = await self._get_multiple_prices(symbol, exchanges)
                overview[symbol] = symbol_data
            
            return {
                "success": True,
                "overview": overview,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _get_server_time(self, exchange: str) -> Dict[str, Any]:
        """Get server time dari exchange"""
        try:
            result = await self.exchange_client.get_server_time(exchange)
            return {
                "success": True,
                "data": result,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _analyze_arbitrage(self, symbol: str, exchanges: List[str]) -> Dict[str, Any]:
        """Analyze arbitrage opportunities"""
        try:
            comparison = await self._compare_top_exchanges(symbol, len(exchanges))
            
            if not comparison["success"]:
                return comparison
            
            # Calculate arbitrage opportunities
            opportunities = []
            prices = comparison["comparison"]
            
            for i, low_exchange in enumerate(prices):
                for j, high_exchange in enumerate(prices):
                    if i != j and low_exchange["price_float"] < high_exchange["price_float"]:
                        profit_percent = ((high_exchange["price_float"] - low_exchange["price_float"]) / low_exchange["price_float"]) * 100
                        if profit_percent > 0.1:  # Only show opportunities > 0.1%
                            opportunities.append({
                                "buy_exchange": low_exchange["exchange"],
                                "sell_exchange": high_exchange["exchange"],
                                "buy_price": low_exchange["price"],
                                "sell_price": high_exchange["price"],
                                "profit_percent": round(profit_percent, 4),
                                "profit_amount": round(high_exchange["price_float"] - low_exchange["price_float"], 8)
                            })
            
            # Sort by profit percentage
            opportunities.sort(key=lambda x: x["profit_percent"], reverse=True)
            
            return {
                "success": True,
                "symbol": symbol,
                "opportunities": opportunities[:5],  # Top 5 opportunities
                "market_spread": comparison["price_spread"],
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_tools_description(self) -> str:
        """Get description of all available tools untuk LLM"""
        tools_desc = "Available tools:\n\n"
        
        for tool_name, tool_info in self.tools.items():
            tools_desc += f"**{tool_name}**: {tool_info['description']}\n"
            tools_desc += f"Parameters: {json.dumps(tool_info['parameters'], indent=2)}\n\n"
        
        return tools_desc
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific tool dengan improved error handling"""
        if tool_name not in self.tools:
            available_tools = ", ".join(self.tools.keys())
            return {
                "success": False, 
                "error": f"Tool '{tool_name}' not found. Available tools: {available_tools}"
            }
        
        try:
            tool_function = self.tools[tool_name]["function"]
            
            # Validate parameters
            tool_params = self.tools[tool_name]["parameters"]
            validated_params = self._validate_parameters(parameters, tool_params)
            
            result = await tool_function(**validated_params)
            return result
        except TypeError as e:
            logger.error(f"Parameter error for tool {tool_name}: {e}")
            return {"success": False, "error": f"Invalid parameters for {tool_name}: {str(e)}"}
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {"success": False, "error": f"Tool execution failed: {str(e)}"}
    
    def _validate_parameters(self, parameters: Dict[str, Any], tool_params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean parameters"""
        validated = {}
        
        for param_name, param_info in tool_params.items():
            if param_name in parameters:
                validated[param_name] = parameters[param_name]
            elif param_info.get("required", False):
                raise ValueError(f"Required parameter '{param_name}' missing")
        
        return validated