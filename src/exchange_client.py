#!/usr/bin/env python3
"""
Multi-Exchange Client for Cryptocurrency Bot
Supports multiple exchanges including Bybit, Binance, KuCoin, MEXC, Indodax, etc.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

import httpx

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ExchangeClient:
    """Client for accessing multiple cryptocurrency exchanges"""
    
    def __init__(self):
        """Initialize the exchange client with HTTP client"""
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True
        )
        self.exchange_base_urls = {
            'bybit': 'https://api.bybit.com',
            'binance': 'https://api.binance.com',
            'kucoin': 'https://api.kucoin.com',
            'indodax': 'https://indodax.com/api',
            'mexc': 'https://api.mexc.com',
            'okx': 'https://www.okx.com/api/v5',
            'bitfinex': 'https://api-pub.bitfinex.com',
            'gateio': 'https://api.gateio.ws/api/v4',
            'kraken': 'https://api.kraken.com/0/public',
            'huobi': 'https://api.huobi.pro'
        }
        
    async def close(self):
        """Close the HTTP client session"""
        await self.client.aclose()
        
    def get_supported_exchanges(self) -> List[str]:
        """Get a list of supported exchanges"""
        return list(self.exchange_base_urls.keys())
        
    def normalize_symbol(self, symbol: str, exchange: str = 'bybit') -> str:
        """
        Normalize symbol for the specified exchange
        
        Args:
            symbol: The symbol to normalize (e.g., "BTC", "ETH")
            exchange: The exchange to normalize for
            
        Returns:
            Normalized symbol for the exchange
        """
        # Convert to uppercase and remove non-alphanumeric characters
        symbol = symbol.upper().replace('/', '').replace('-', '')
        
        # Handle exchange-specific formatting
        if exchange == 'indodax':
            # Indodax uses lowercase and IDR pairs
            return f"{symbol.lower()}_idr"
        elif exchange == 'kucoin':
            # KuCoin uses dashes
            if 'USDT' not in symbol and len(symbol) <= 5:
                return f"{symbol}-USDT"
            else:
                # Already has trading pair
                parts = symbol.split('USD')
                if len(parts) > 1:
                    return f"{parts[0]}-USD{parts[1]}"
                return symbol.replace('USDT', '-USDT')
        elif exchange == 'bybit' or exchange == 'binance' or exchange == 'mexc':
            # BYBIT/Binance/MEXC already use BTCUSDT format
            if 'USDT' not in symbol and len(symbol) <= 5:
                return f"{symbol}USDT"
            return symbol
        elif exchange == 'okx':
            # OKX uses dashes
            if 'USDT' not in symbol and len(symbol) <= 5:
                return f"{symbol}-USDT"
            else:
                return symbol.replace('USDT', '-USDT')
        elif exchange == 'bitfinex':
            # Bitfinex prefixes with 't'
            if 'USD' not in symbol and len(symbol) <= 5:
                return f"t{symbol}USD"
            return f"t{symbol}"
        elif exchange == 'kraken':
            # Kraken uses XBT instead of BTC
            symbol = symbol.replace('BTC', 'XBT')
            if 'USD' not in symbol and len(symbol) <= 5:
                return f"{symbol}USD"
            return symbol
        
        # Default case - return as BTCUSDT format
        if 'USDT' not in symbol and len(symbol) <= 5:
            return f"{symbol}USDT"
        return symbol
    
    async def get_ticker(self, symbol: str, exchange: str = 'bybit') -> Dict[str, Any]:
        """
        Get ticker data from the specified exchange
        
        Args:
            symbol: The trading pair symbol (e.g., "BTC", "ETH", "BTCUSDT")
            exchange: The exchange to query
            
        Returns:
            Ticker data response as a dictionary
        """
        exchange = exchange.lower()
        
        if exchange not in self.exchange_base_urls:
            return {
                "error": f"Exchange '{exchange}' not supported",
                "supported_exchanges": self.get_supported_exchanges()
            }
            
        # Normalize the symbol for the exchange
        formatted_symbol = self.normalize_symbol(symbol, exchange)
        
        try:
            if exchange == 'bybit':
                # Bybit API for ticker
                endpoint = f"{self.exchange_base_urls[exchange]}/v5/market/tickers"
                params = {"category": "spot", "symbol": formatted_symbol}
                response = await self.client.get(endpoint, params=params)
                
                # Handle response
                if response.status_code == 200:
                    return {
                        "exchange": "Bybit",
                        "symbol": formatted_symbol,
                        "data": response.json(),
                        "timestamp": datetime.now().isoformat()
                    }
                
            elif exchange == 'binance':
                # Binance API for ticker
                endpoint = f"{self.exchange_base_urls[exchange]}/api/v3/ticker/price"
                params = {"symbol": formatted_symbol}
                response = await self.client.get(endpoint, params=params)
                
                # Add 24h data
                if response.status_code == 200:
                    # Get 24h stats as well
                    endpoint_24h = f"{self.exchange_base_urls[exchange]}/api/v3/ticker/24hr"
                    response_24h = await self.client.get(endpoint_24h, params=params)
                    data_24h = {}
                    
                    if response_24h.status_code == 200:
                        data_24h = response_24h.json()
                    
                    return {
                        "exchange": "Binance",
                        "symbol": formatted_symbol,
                        "data": response.json(),
                        "data_24h": data_24h,
                        "timestamp": datetime.now().isoformat()
                    }
                
            elif exchange == 'kucoin':
                # KuCoin API for ticker
                endpoint = f"{self.exchange_base_urls[exchange]}/api/v1/market/stats"
                params = {"symbol": formatted_symbol}
                response = await self.client.get(endpoint, params=params)
                
                if response.status_code == 200:
                    return {
                        "exchange": "KuCoin",
                        "symbol": formatted_symbol,
                        "data": response.json(),
                        "timestamp": datetime.now().isoformat()
                    }
                
            elif exchange == 'indodax':
                # Indodax API for ticker
                endpoint = f"{self.exchange_base_urls[exchange]}/{formatted_symbol}/ticker"
                response = await self.client.get(endpoint)
                
                if response.status_code == 200:
                    return {
                        "exchange": "Indodax",
                        "symbol": formatted_symbol,
                        "data": response.json(),
                        "timestamp": datetime.now().isoformat()
                    }
                
            elif exchange == 'mexc':
                # MEXC API for ticker
                endpoint = f"{self.exchange_base_urls[exchange]}/api/v3/ticker/price"
                params = {"symbol": formatted_symbol}
                response = await self.client.get(endpoint, params=params)
                
                if response.status_code == 200:
                    return {
                        "exchange": "MEXC",
                        "symbol": formatted_symbol,
                        "data": response.json(),
                        "timestamp": datetime.now().isoformat()
                    }
                    
            elif exchange == 'okx':
                # OKX API for ticker
                endpoint = f"{self.exchange_base_urls[exchange]}/market/ticker"
                params = {"instId": formatted_symbol}
                response = await self.client.get(endpoint, params=params)
                
                if response.status_code == 200:
                    return {
                        "exchange": "OKX",
                        "symbol": formatted_symbol,
                        "data": response.json(),
                        "timestamp": datetime.now().isoformat()
                    }
                
            elif exchange == 'bitfinex':
                # Bitfinex API for ticker
                endpoint = f"{self.exchange_base_urls[exchange]}/v2/ticker/{formatted_symbol}"
                response = await self.client.get(endpoint)
                
                if response.status_code == 200:
                    return {
                        "exchange": "Bitfinex",
                        "symbol": formatted_symbol,
                        "data": response.json(),
                        "timestamp": datetime.now().isoformat()
                    }
                
            elif exchange == 'gateio':
                # Gate.io API for ticker
                # For Gate.io, use BTC_USDT format
                gateio_symbol = formatted_symbol.replace('-', '_')
                endpoint = f"{self.exchange_base_urls[exchange]}/spot/tickers"
                params = {"currency_pair": gateio_symbol}
                response = await self.client.get(endpoint, params=params)
                
                if response.status_code == 200:
                    return {
                        "exchange": "Gate.io",
                        "symbol": gateio_symbol,
                        "data": response.json(),
                        "timestamp": datetime.now().isoformat()
                    }
                
            elif exchange == 'kraken':
                # Kraken API for ticker
                endpoint = f"{self.exchange_base_urls[exchange]}/Ticker"
                params = {"pair": formatted_symbol}
                response = await self.client.get(endpoint, params=params)
                
                if response.status_code == 200:
                    return {
                        "exchange": "Kraken",
                        "symbol": formatted_symbol,
                        "data": response.json(),
                        "timestamp": datetime.now().isoformat()
                    }
                
            elif exchange == 'huobi':
                # Huobi API for ticker
                huobi_symbol = formatted_symbol.replace('-', '').lower()
                endpoint = f"{self.exchange_base_urls[exchange]}/market/detail/merged"
                params = {"symbol": huobi_symbol}
                response = await self.client.get(endpoint, params=params)
                
                if response.status_code == 200:
                    return {
                        "exchange": "Huobi",
                        "symbol": huobi_symbol,
                        "data": response.json(),
                        "timestamp": datetime.now().isoformat()
                    }
            
            # If we get here, either the response wasn't 200 or the exchange wasn't handled
            return {
                "error": f"Failed to fetch data from {exchange}",
                "status_code": response.status_code if 'response' in locals() else None,
                "response": response.text if 'response' in locals() else None
            }
            
        except httpx.RequestError as e:
            return {
                "error": f"Request error for {exchange}: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "error": f"Unexpected error for {exchange}: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            
    async def get_server_time(self, exchange: str = 'bybit') -> Dict[str, Any]:
        """
        Get server time from the specified exchange
        
        Args:
            exchange: The exchange to query
            
        Returns:
            Server time response as a dictionary
        """
        exchange = exchange.lower()
        
        if exchange not in self.exchange_base_urls:
            return {
                "error": f"Exchange '{exchange}' not supported",
                "supported_exchanges": self.get_supported_exchanges()
            }
            
        try:
            if exchange == 'bybit':
                # Bybit API for server time
                endpoint = f"{self.exchange_base_urls[exchange]}/v5/market/time"
                response = await self.client.get(endpoint)
                
                if response.status_code == 200:
                    return {
                        "exchange": "Bybit",
                        "data": response.json(),
                        "timestamp": datetime.now().isoformat()
                    }
                
            elif exchange == 'binance':
                # Binance API for server time
                endpoint = f"{self.exchange_base_urls[exchange]}/api/v3/time"
                response = await self.client.get(endpoint)
                
                if response.status_code == 200:
                    return {
                        "exchange": "Binance",
                        "data": response.json(),
                        "timestamp": datetime.now().isoformat()
                    }
                
            elif exchange == 'kucoin':
                # KuCoin API for server time
                endpoint = f"{self.exchange_base_urls[exchange]}/api/v1/timestamp"
                response = await self.client.get(endpoint)
                
                if response.status_code == 200:
                    return {
                        "exchange": "KuCoin",
                        "data": response.json(),
                        "timestamp": datetime.now().isoformat()
                    }
                
            # Default: return local time if exchange doesn't support time endpoint
            current_time = int(time.time())
            return {
                "exchange": exchange.capitalize(),
                "data": {
                    "time": current_time,
                    "local": True
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except httpx.RequestError as e:
            return {
                "error": f"Request error for {exchange}: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "error": f"Unexpected error for {exchange}: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def format_ticker_response(self, ticker_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format ticker response into a consistent structure
        
        Args:
            ticker_data: The raw ticker data from an exchange
            
        Returns:
            Formatted ticker data with consistent fields
        """
        try:
            exchange = ticker_data.get("exchange", "Unknown").lower()
            symbol = ticker_data.get("symbol", "Unknown")
            data = ticker_data.get("data", {})
            
            if "error" in ticker_data:
                return ticker_data
                
            if exchange == "bybit":
                # Bybit format
                result = data.get("result", {})
                list_items = result.get("list", [])
                
                if not list_items:
                    return {"error": f"No ticker data for {symbol} on {exchange.capitalize()}"}
                    
                ticker = list_items[0]
                return {
                    "exchange": exchange.capitalize(),
                    "symbol": symbol,
                    "price": ticker.get("lastPrice"),
                    "change_24h": ticker.get("price24hPcnt"),
                    "volume_24h": ticker.get("volume24h"),
                    "high_24h": ticker.get("highPrice24h"),
                    "low_24h": ticker.get("lowPrice24h"),
                }
                
            elif exchange == "binance":
                # Binance format
                price = data.get("price", "N/A")
                data_24h = ticker_data.get("data_24h", {})
                return {
                    "exchange": exchange.capitalize(),
                    "symbol": symbol,
                    "price": price,
                    "change_24h": data_24h.get("priceChangePercent", "N/A"),
                    "volume_24h": data_24h.get("volume", "N/A"),
                    "high_24h": data_24h.get("highPrice", "N/A"),
                    "low_24h": data_24h.get("lowPrice", "N/A"),
                }
                
            elif exchange == "kucoin":
                # KuCoin format
                kucoin_data = data.get("data", {})
                return {
                    "exchange": exchange.capitalize(),
                    "symbol": symbol,
                    "price": kucoin_data.get("last", "N/A"),
                    "change_24h": kucoin_data.get("changeRate", "N/A"),
                    "volume_24h": kucoin_data.get("vol", "N/A"),
                    "high_24h": kucoin_data.get("high", "N/A"),
                    "low_24h": kucoin_data.get("low", "N/A"),
                }
                
            elif exchange == "indodax":
                # Indodax format (IDR prices need conversion to USD)
                ticker = data.get("ticker", {})
                idr_price = ticker.get("last", "0")
                
                # Convert IDR to USD (approximate rate: 1 USD = 15000 IDR)
                try:
                    usd_price = float(idr_price) / 15000 if idr_price != "N/A" else "N/A"
                    formatted_price = f"{usd_price:.2f}" if usd_price != "N/A" else "N/A"
                except (ValueError, TypeError):
                    formatted_price = "N/A"
                
                return {
                    "exchange": exchange.capitalize(),
                    "symbol": symbol,
                    "price": formatted_price,
                    "price_idr": idr_price,  # Keep original IDR price
                    "change_24h": "N/A",  # Indodax doesn't provide percent change
                    "volume_24h": ticker.get("vol_idr", "N/A"),
                    "high_24h": ticker.get("high", "N/A"),
                    "low_24h": ticker.get("low", "N/A"),
                }
                
            elif exchange == "mexc":
                # MEXC format
                price = data.get("price", "N/A")
                return {
                    "exchange": exchange.upper(),
                    "symbol": symbol,
                    "price": price,
                    "change_24h": "N/A",
                    "volume_24h": "N/A",
                    "high_24h": "N/A",
                    "low_24h": "N/A",
                }
                
            elif exchange == "okx":
                # OKX format
                okx_data = data.get("data", [])
                if okx_data:
                    ticker = okx_data[0]
                    return {
                        "exchange": exchange.upper(),
                        "symbol": symbol,
                        "price": ticker.get("last", "N/A"),
                        "change_24h": ticker.get("changePercent", "N/A"),
                        "volume_24h": ticker.get("vol24h", "N/A"),
                        "high_24h": ticker.get("high24h", "N/A"),
                        "low_24h": ticker.get("low24h", "N/A"),
                    }
                    
            elif exchange == "kraken":
                # Kraken format
                result = data.get("result", {})
                if result:
                    # Kraken returns data with pair names as keys
                    pair_data = list(result.values())[0] if result else {}
                    last_price = pair_data.get("c", ["N/A"])[0] if isinstance(pair_data.get("c"), list) else "N/A"
                    return {
                        "exchange": exchange.capitalize(),
                        "symbol": symbol,
                        "price": last_price,
                        "change_24h": "N/A",
                        "volume_24h": pair_data.get("v", ["N/A"])[1] if isinstance(pair_data.get("v"), list) else "N/A",
                        "high_24h": pair_data.get("h", ["N/A"])[1] if isinstance(pair_data.get("h"), list) else "N/A",
                        "low_24h": pair_data.get("l", ["N/A"])[1] if isinstance(pair_data.get("l"), list) else "N/A",
                    }
                    
            elif exchange == "huobi":
                # Huobi format
                tick = data.get("tick", {})
                return {
                    "exchange": exchange.capitalize(),
                    "symbol": symbol,
                    "price": str(tick.get("close", "N/A")),
                    "change_24h": "N/A",
                    "volume_24h": str(tick.get("vol", "N/A")),
                    "high_24h": str(tick.get("high", "N/A")),
                    "low_24h": str(tick.get("low", "N/A")),
                }
            
            # Default case - try to extract common fields
            price = data.get("price") or data.get("last") or data.get("lastPrice") or "N/A"
            return {
                "exchange": exchange.capitalize(),
                "symbol": symbol,
                "price": str(price),
                "change_24h": "N/A",
                "volume_24h": "N/A",
                "high_24h": "N/A",
                "low_24h": "N/A",
                "raw": data  # Keep raw data for debugging
            }
            
        except Exception as e:
            return {
                "error": f"Error formatting ticker response: {str(e)}",
                "raw": ticker_data
            }