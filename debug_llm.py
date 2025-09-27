#!/usr/bin/env python3
"""
Debug script untuk melihat raw LLM responses
"""

import asyncio
import sys
import os

# Add src to path (project root/src)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config import get_config
from llm import ZaiClient

async def debug_llm_responses():
    """Debug raw LLM responses untuk trading queries"""
    print("🔍 Debugging LLM Responses...")
    
    # Initialize LLM client
    config = get_config()
    llm_client = ZaiClient(
        api_key=config.zai_api_key,
        base_url=config.zai_base_url,
        default_model=config.llm_model,
        temperature=config.llm_temperature,
        max_tokens=config.llm_max_tokens,
    )
    
    system_prompt = """You are an advanced cryptocurrency trading assistant with access to real-time market data from multiple exchanges.

IMPORTANT: You MUST use the available tools to get real-time data. Do NOT provide fake or outdated prices.

Available tools:

**get_price**: Get current price of a cryptocurrency from a specific exchange
Parameters: {"symbol": "string", "exchange": "string"}

**compare_top_exchanges**: Compare prices across top exchanges for a cryptocurrency
Parameters: {"symbol": "string", "count": "integer"}

**CRITICAL INSTRUCTIONS:**
1. **ALWAYS use tools** for price queries, market data, or trading information
2. **NEVER make up prices** or provide fake data

**Response Format for Tool Usage:**
```json
{
    "reasoning": "I need to get real-time data for [specific reason]",
    "tool_calls": [
        {
            "tool": "tool_name",
            "parameters": {"param": "value"}
        }
    ]
}
```

**Examples with Required Tool Usage:**
- "What's the price of Bitcoin?" → MUST use get_price or compare_top_exchanges

REMEMBER: Always use tools for real data. Never provide fake prices or outdated information.
"""
    
    test_queries = [
        "What's the price of Bitcoin?",
        "Show me BTC prices on top 5 exchanges"
    ]
    
    for query in test_queries:
        print(f"\n💬 Query: {query}")
        print("-" * 50)
        
        try:
            response = await asyncio.to_thread(
                llm_client.chat,
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.3,
                max_tokens=1024
            )
            
            print(f"🤖 Raw Response:\n{repr(response)}")
            print(f"\n📝 Formatted Response:\n{response}")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        print("\n" + "="*60)

if __name__ == "__main__":
    asyncio.run(debug_llm_responses())
