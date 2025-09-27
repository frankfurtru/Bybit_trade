#!/usr/bin/env python3
"""
Debug specific query yang bermasalah
"""

import asyncio
import sys
import os

# Add src to path (project root/src)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config import get_config
from llm import ZaiClient
from exchange_client import ExchangeClient
from bybit_client import BybitClient, BybitConfig
from natural_trading_assistant import TradingToolsRegistry
from natural_language_processor import NaturalTradingProcessor

async def debug_specific_query():
    """Debug specific problematic query"""
    print("🔍 Debugging Specific Query...")
    
    # Initialize components
    config = get_config()
    
    llm_client = ZaiClient(
        api_key=config.zai_api_key,
        base_url=config.zai_base_url,
        default_model=config.llm_model,
        temperature=0.3,
        max_tokens=800
    )
    
    query = "Give me market overview for BTC, ETH, ADA"
    
    print(f"💬 Query: {query}")
    print("-" * 50)
    
    try:
        response = await asyncio.to_thread(
            llm_client.chat,
            [
                {"role": "system", "content": """You are a cryptocurrency trading assistant. For trading queries, respond with JSON tool calls.

Available tools:
- get_market_overview: Get market overview with multiple cryptocurrencies

Response format:
```json
{
    "reasoning": "I need market overview for multiple cryptocurrencies",
    "tool_calls": [
        {
            "tool": "get_market_overview",
            "parameters": {"symbols": ["BTC", "ETH", "ADA"], "exchanges": ["binance", "kucoin", "bybit"]}
        }
    ]
}
```"""},
                {"role": "user", "content": query}
            ],
            temperature=0.3,
            max_tokens=800
        )
        
        print(f"🤖 Raw Response:\n{repr(response)}")
        print(f"\n📝 Formatted Response:\n{response}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(debug_specific_query())
