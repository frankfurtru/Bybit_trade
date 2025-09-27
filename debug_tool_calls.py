#!/usr/bin/env python3
"""
Debug tool calls parsing
"""

import asyncio
import sys
import os

# Add src to path (project root/src)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config import get_config
from llm import ZaiClient

async def debug_tool_calls():
    """Debug tool calls responses"""
    print("🔍 Debugging Tool Calls...")
    
    # Initialize LLM client
    config = get_config()
    llm_client = ZaiClient(
        api_key=config.zai_api_key,
        base_url=config.zai_base_url,
        default_model=config.llm_model,
        temperature=0.3,
        max_tokens=800
    )
    
    system_prompt = """You are a cryptocurrency trading assistant with access to real-time market data tools.

IMPORTANT: For ANY price or trading query, you MUST respond with JSON tool calls. DO NOT provide fake data.

Available tools:
- get_price: Get price from one exchange
- compare_top_exchanges: Compare prices across top exchanges  

Response format for trading queries:
```json
{
    "reasoning": "Why I need this tool",
    "tool_calls": [
        {
            "tool": "tool_name", 
            "parameters": {"symbol": "BTC", "exchange": "binance"}
        }
    ]
}
```

Examples:
- "What's Bitcoin price?" → use compare_top_exchanges

For general chat (non-trading), respond normally without tools.
"""
    
    query = "What's the price of Bitcoin?"
    
    print(f"💬 Query: {query}")
    print("-" * 50)
    
    try:
        response = await asyncio.to_thread(
            llm_client.chat,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.3,
            max_tokens=800
        )
        
        print(f"🤖 Raw Response:\n{repr(response)}")
        print(f"\n📝 Formatted Response:\n{response}")
        
        # Test JSON parsing
        import re
        import json
        
        print(f"\n🔍 JSON Parsing Tests:")
        
        # Method 1: Look for ```json blocks
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            print(f"✅ Found JSON block: {json_match.group(1)}")
            try:
                parsed = json.loads(json_match.group(1))
                print(f"✅ Successfully parsed: {parsed}")
            except Exception as e:
                print(f"❌ JSON parse error: {e}")
        else:
            print("❌ No ```json block found")
        
        # Method 2: Look for any JSON object
        json_match2 = re.search(r'{.*}', response, re.DOTALL)
        if json_match2:
            print(f"✅ Found JSON object: {json_match2.group(0)}")
            try:
                parsed = json.loads(json_match2.group(0))
                print(f"✅ Successfully parsed: {parsed}")
            except Exception as e:
                print(f"❌ JSON parse error: {e}")
        else:
            print("❌ No JSON object found")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(debug_tool_calls())
