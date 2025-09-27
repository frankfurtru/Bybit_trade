from __future__ import annotations

import hashlib
import hmac
import json
import time
import random
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx


@dataclass
class BybitConfig:
    api_key: str | None
    api_secret: str | None
    testnet: bool = False
    demo: bool = False
    simulation_mode: bool = False
    simulation_balance: dict = None
    public_only: bool = False  # Add public_only mode


class BybitClient:
    """Bybit V5 REST client with minimal endpoints.

    Auth/sign spec: https://bybit-exchange.github.io/docs/v5/intro
    Sign string: timestamp + apiKey + recvWindow + (queryString or requestBody)
    HMAC-SHA256(secret, sign_string).hexdigest()
    """

    def __init__(self, cfg: BybitConfig):
        self.cfg = cfg
        self.simulation_mode = cfg.simulation_mode
        self.simulation_balance = cfg.simulation_balance or {}
        self.public_only = cfg.public_only
        
        if self.simulation_mode:
            self.enabled = True  # Simulation is always enabled
            self.base_url = "simulation://localhost"
            self._client = None
        else:
            # In public_only mode, we don't require API keys but still create a client
            self.enabled = self.public_only or bool(cfg.api_key and cfg.api_secret)
            # Select correct environment
            if cfg.testnet:
                self.base_url = "https://api-testnet.bybit.com"
            elif hasattr(cfg, 'demo') and cfg.demo:
                self.base_url = "https://api-demo.bybit.com"
            else:
                self.base_url = "https://api.bybit.com"
            
            if self.enabled:
                self._client = httpx.AsyncClient(base_url=self.base_url, timeout=20.0)
            else:
                self._client = None
            
        self._recv_window = "5000"

    def is_ready(self) -> bool:
        return self.enabled or self.simulation_mode or self.public_only
        
    def can_access_private_endpoints(self) -> bool:
        """Check if client has permissions for private endpoints"""
        return (self.enabled and not self.public_only and bool(self.cfg.api_key and self.cfg.api_secret)) or self.simulation_mode

    # --------------- Simulation Methods ---------------
    def _simulate_market_data(self, symbol: str = "BTCUSDT") -> Dict[str, Any]:
        """Generate realistic market data for simulation"""
        current_price = 45000.0 if symbol == "BTCUSDT" else 3000.0
        price_variation = random.uniform(-0.05, 0.05)  # ±5%
        price = current_price * (1 + price_variation)
        
        return {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "list": [{
                    "symbol": symbol,
                    "lastPrice": str(round(price, 2)),
                    "prevPrice24h": str(round(price * 0.98, 2)),
                    "price24hPcnt": str(round(price_variation * 100, 2)),
                    "highPrice24h": str(round(price * 1.03, 2)),
                    "lowPrice24h": str(round(price * 0.97, 2)),
                    "volume24h": str(random.randint(1000, 10000)),
                    "turnover24h": str(random.randint(10000000, 100000000)),
                }]
            }
        }
    
    def _simulate_kline_data(self, symbol: str, interval: str, limit: int = 200) -> Dict[str, Any]:
        """Generate realistic OHLCV data for simulation"""
        base_price = 45000.0 if symbol == "BTCUSDT" else 3000.0
        klines = []
        
        for i in range(limit):
            timestamp = int(time.time() * 1000) - (limit - i) * 60000  # 1min intervals
            price_change = random.uniform(-0.02, 0.02)  # ±2% per candle
            
            open_price = base_price * (1 + price_change)
            close_price = open_price * (1 + random.uniform(-0.01, 0.01))
            high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.005))
            low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.005))
            volume = random.uniform(10, 100)
            
            klines.append([
                str(timestamp),
                str(round(open_price, 2)),
                str(round(high_price, 2)),
                str(round(low_price, 2)),
                str(round(close_price, 2)),
                str(round(volume, 6)),
                str(round(volume * close_price, 2))
            ])
        
        return {
            "retCode": 0,
            "retMsg": "OK", 
            "result": {
                "symbol": symbol,
                "category": "spot",
                "list": klines
            }
        }
    
    def _simulate_wallet_balance(self) -> Dict[str, Any]:
        """Generate realistic wallet balance for simulation"""
        coins = []
        for coin, balance in self.simulation_balance.items():
            coins.append({
                "coin": coin,
                "walletBalance": str(balance),
                "availableBalance": str(balance * 0.9),  # 90% available
                "usdValue": str(balance * (45000 if coin == "BTC" else 3000 if coin == "ETH" else 1)),
            })
        
        return {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "list": [{
                    "accountType": "UNIFIED",
                    "coin": coins
                }]
            }
        }

    # --------------- Helpers ---------------
    def _timestamp_ms(self) -> str:
        return str(int(time.time() * 1000))

    def _sign(self, ts: str, payload: str) -> str:
        secret = (self.cfg.api_secret or "").encode()
        msg = (ts + (self.cfg.api_key or "") + self._recv_window + payload).encode()
        return hmac.new(secret, msg, hashlib.sha256).hexdigest()

    def _auth_headers(self, sign: str, ts: str) -> Dict[str, str]:
        return {
            "X-BAPI-API-KEY": self.cfg.api_key or "",
            "X-BAPI-SIGN": sign,
            "X-BAPI-TIMESTAMP": ts,
            "X-BAPI-RECV-WINDOW": self._recv_window,
            "X-BAPI-SIGN-TYPE": "2",  # HMAC SHA256
            "Content-Type": "application/json",
        }

    # --------------- Public Endpoints ---------------
    async def get_server_time(self) -> Dict[str, Any]:
        # Handle simulation mode or client not initialized (public only with no client)
        if self.simulation_mode or self._client is None:
            current_time = int(time.time())
            return {
                "retCode": 0,
                "retMsg": "OK" if self.simulation_mode else "OK (local time)",
                "result": {
                    "timeSecond": str(current_time),
                    "timeNano": str(current_time * 1000000000)
                }
            }
        
        try:
            r = await self._client.get("/v5/market/time")
            r.raise_for_status()
            return r.json()
        except Exception as e:
            # Fallback mechanism if API call fails
            current_time = int(time.time())
            return {
                "retCode": 0,
                "retMsg": f"OK (local fallback: {str(e)})",
                "result": {
                    "timeSecond": str(current_time),
                    "timeNano": str(current_time * 1000000000)
                }
            }

    async def get_tickers(self, category: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        if self.simulation_mode:
            return self._simulate_market_data(symbol or "BTCUSDT")
            
        # Validate category
        valid_categories = ["spot", "linear", "inverse", "option"]
        if category.lower() not in valid_categories:
            return {
                "retCode": 10001,
                "retMsg": f"Invalid category: {category}. Must be one of {', '.join(valid_categories)}",
                "result": {}
            }
            
        # Handle case where client is not initialized (public_only with no key)
        if self._client is None:
            return {
                "retCode": 10002,
                "retMsg": "Client not initialized. API access unavailable.",
                "result": {}
            }
            
        try:
            params = {"category": category}
            if symbol:
                params["symbol"] = symbol
            r = await self._client.get("/v5/market/tickers", params=params)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                # Try to extract error from Bybit response
                try:
                    error_data = e.response.json()
                    return error_data
                except:
                    pass
            return {
                "retCode": e.response.status_code,
                "retMsg": f"HTTP Error: {str(e)}",
                "result": {}
            }
        except Exception as e:
            return {
                "retCode": 10000,
                "retMsg": f"Error: {str(e)}",
                "result": {}
            }

    async def get_kline(self, category: str, symbol: str, interval: str, limit: int = 200, start: Optional[int] = None, end: Optional[int] = None) -> Dict[str, Any]:
        if self.simulation_mode:
            return self._simulate_kline_data(symbol, interval, limit)
            
        # Handle case where client is not initialized (public_only with no key)
        if self._client is None:
            return {
                "retCode": 10002,
                "retMsg": "Client not initialized. API access unavailable.",
                "result": {}
            }
            
        try:
            params: Dict[str, Any] = {
                "category": category,
                "symbol": symbol,
                "interval": interval,
                "limit": limit,
            }
            if start is not None:
                params["start"] = start
            if end is not None:
                params["end"] = end
            r = await self._client.get("/v5/market/kline", params=params)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {
                "retCode": 10000,
                "retMsg": f"Error: {str(e)}",
                "result": {}
            }

    async def get_orderbook(self, category: str, symbol: str, limit: int = 50) -> Dict[str, Any]:
        # Handle case where client is not initialized (public_only with no key)
        if self._client is None:
            return {
                "retCode": 10002,
                "retMsg": "Client not initialized. API access unavailable.",
                "result": {}
            }
            
        try:
            params = {"category": category, "symbol": symbol, "limit": limit}
            r = await self._client.get("/v5/market/orderbook", params=params)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {
                "retCode": 10000,
                "retMsg": f"Error: {str(e)}",
                "result": {}
            }

    async def get_recent_trades(self, category: str, symbol: str, limit: int = 50) -> Dict[str, Any]:
        # Handle case where client is not initialized (public_only with no key)
        if self._client is None:
            return {
                "retCode": 10002,
                "retMsg": "Client not initialized. API access unavailable.",
                "result": {}
            }
            
        try:
            params = {"category": category, "symbol": symbol, "limit": limit}
            r = await self._client.get("/v5/market/recent-trade", params=params)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {
                "retCode": 10000,
                "retMsg": f"Error: {str(e)}",
                "result": {}
            }

    async def get_instruments_info(self, category: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        # Handle case where client is not initialized (public_only with no key)
        if self._client is None:
            return {
                "retCode": 10002,
                "retMsg": "Client not initialized. API access unavailable.",
                "result": {}
            }
            
        try:
            params: Dict[str, Any] = {"category": category}
            if symbol:
                params["symbol"] = symbol
            r = await self._client.get("/v5/market/instruments-info", params=params)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {
                "retCode": 10000,
                "retMsg": f"Error: {str(e)}",
                "result": {}
            }

    async def get_funding_history(self, category: str, symbol: str, limit: int = 50) -> Dict[str, Any]:
        # Handle case where client is not initialized (public_only with no key)
        if self._client is None:
            return {
                "retCode": 10002,
                "retMsg": "Client not initialized. API access unavailable.",
                "result": {}
            }
            
        try:
            params = {"category": category, "symbol": symbol, "limit": limit}
            r = await self._client.get("/v5/market/funding-history", params=params)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {
                "retCode": 10000,
                "retMsg": f"Error: {str(e)}",
                "result": {}
            }

    # --------------- Private Endpoints ---------------
    async def set_leverage(self, *, category: str, symbol: str, buyLeverage: str, sellLeverage: str) -> Dict[str, Any]:
        """Set leverage for a symbol. Bybit V5: POST /v5/position/set-leverage"""
        if self.simulation_mode:
            return {"retCode": 0, "retMsg": "OK", "result": {"symbol": symbol, "buyLeverage": buyLeverage, "sellLeverage": sellLeverage}}
        if not self.can_access_private_endpoints():
            raise RuntimeError("Private endpoint requires API key/secret or simulation mode.")
        path = "/v5/position/set-leverage"
        ts = self._timestamp_ms()
        body: Dict[str, Any] = {
            "category": category,
            "symbol": symbol,
            "buyLeverage": str(buyLeverage),
            "sellLeverage": str(sellLeverage),
        }
        body_str = json.dumps(body, separators=(",", ":"))
        sign = self._sign(ts, body_str)
        headers = self._auth_headers(sign, ts)
        r = await self._client.post(path, headers=headers, content=body_str)
        r.raise_for_status()
        return r.json()

    async def switch_isolated(self, *, category: str, symbol: str, tradeMode: int, buyLeverage: Optional[str] = None, sellLeverage: Optional[str] = None) -> Dict[str, Any]:
        """Switch Cross/Isolated Margin. Bybit V5: POST /v5/position/switch-isolated
        tradeMode: 0=cross, 1=isolated
        """
        if self.simulation_mode:
            return {"retCode": 0, "retMsg": "OK", "result": {"symbol": symbol, "tradeMode": tradeMode}}
        if not self.can_access_private_endpoints():
            raise RuntimeError("Private endpoint requires API key/secret or simulation mode.")
        path = "/v5/position/switch-isolated"
        ts = self._timestamp_ms()
        body: Dict[str, Any] = {
            "category": category,
            "symbol": symbol,
            "tradeMode": tradeMode,
        }
        if buyLeverage is not None:
            body["buyLeverage"] = str(buyLeverage)
        if sellLeverage is not None:
            body["sellLeverage"] = str(sellLeverage)
        body_str = json.dumps(body, separators=(",", ":"))
        sign = self._sign(ts, body_str)
        headers = self._auth_headers(sign, ts)
        r = await self._client.post(path, headers=headers, content=body_str)
        r.raise_for_status()
        return r.json()
    async def get_wallet_balance(self, account_type: str = "UNIFIED", coin: Optional[str] = None) -> Dict[str, Any]:
        if self.simulation_mode:
            return self._simulate_wallet_balance()
            
        if not self.can_access_private_endpoints():
            raise RuntimeError("Private endpoint requires API key/secret or simulation mode.")

        path = "/v5/account/wallet-balance"
        ts = self._timestamp_ms()
        query = {
            "accountType": account_type,
        }
        if coin:
            query["coin"] = coin

        # Build query string in key=val& form sorted by key
        query_items = sorted((k, v) for k, v in query.items() if v is not None)
        query_str = "&".join(f"{k}={v}" for k, v in query_items)

        sign = self._sign(ts, query_str)
        headers = self._auth_headers(sign, ts)
        r = await self._client.get(path, params=query, headers=headers)
        r.raise_for_status()
        return r.json()

    # Example create order (minimal fields)
    async def create_order(
        self,
        *,
        category: str,
        symbol: str,
        side: str,
        orderType: str,
        qty: str,
        price: Optional[str] = None,
        timeInForce: str = "GTC",
        reduceOnly: Optional[bool] = None,
        positionIdx: Optional[int] = None,
        leverage: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self.can_access_private_endpoints():
            raise RuntimeError("Private endpoint requires API key/secret or simulation mode.")

        path = "/v5/order/create"
        ts = self._timestamp_ms()
        body: Dict[str, Any] = {
            "category": category,
            "symbol": symbol,
            "side": side,
            "orderType": orderType,
            "qty": qty,
            "timeInForce": timeInForce,
        }
        if price is not None:
            body["price"] = price
        if reduceOnly is not None:
            body["reduceOnly"] = reduceOnly
        if positionIdx is not None:
            body["positionIdx"] = positionIdx
        if leverage is not None:
            body["leverage"] = leverage

        body_str = json.dumps(body, separators=(",", ":"))
        sign = self._sign(ts, body_str)
        headers = self._auth_headers(sign, ts)
        r = await self._client.post(path, headers=headers, content=body_str)
        r.raise_for_status()
        return r.json()

    async def cancel_order(
        self,
        *,
        category: str,
        symbol: str,
        orderId: Optional[str] = None,
        orderLinkId: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self.can_access_private_endpoints():
            raise RuntimeError("Private endpoint requires API key/secret or simulation mode.")
        path = "/v5/order/cancel"
        ts = self._timestamp_ms()
        body: Dict[str, Any] = {"category": category, "symbol": symbol}
        if orderId:
            body["orderId"] = orderId
        if orderLinkId:
            body["orderLinkId"] = orderLinkId
        body_str = json.dumps(body, separators=(",", ":"))
        sign = self._sign(ts, body_str)
        headers = self._auth_headers(sign, ts)
        r = await self._client.post(path, headers=headers, content=body_str)
        r.raise_for_status()
        return r.json()

    async def get_position_list(self, category: str, symbol: Optional[str] = None, settle_coin: Optional[str] = None) -> Dict[str, Any]:
        if not self.can_access_private_endpoints():
            raise RuntimeError("Private endpoint requires API key/secret or simulation mode.")
        path = "/v5/position/list"
        ts = self._timestamp_ms()
        query: Dict[str, Any] = {"category": category}
        if symbol:
            query["symbol"] = symbol
        if settle_coin:
            query["settleCoin"] = settle_coin
        query_items = sorted((k, v) for k, v in query.items() if v is not None)
        query_str = "&".join(f"{k}={v}" for k, v in query_items)
        sign = self._sign(ts, query_str)
        headers = self._auth_headers(sign, ts)
        r = await self._client.get(path, params=query, headers=headers)
        r.raise_for_status()
        return r.json()

    async def get_order_realtime(self, category: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        if not self.can_access_private_endpoints():
            raise RuntimeError("Private endpoint requires API key/secret or simulation mode.")
        path = "/v5/order/realtime"
        ts = self._timestamp_ms()
        query: Dict[str, Any] = {"category": category}
        if symbol:
            query["symbol"] = symbol
        query_items = sorted((k, v) for k, v in query.items() if v is not None)
        query_str = "&".join(f"{k}={v}" for k, v in query_items)
        sign = self._sign(ts, query_str)
        headers = self._auth_headers(sign, ts)
        r = await self._client.get(path, params=query, headers=headers)
        r.raise_for_status()
        return r.json()

    # --------------- Formatting helpers ---------------
    @staticmethod
    def format_wallet_balance(resp: Dict[str, Any]) -> str:
        try:
            result = resp.get("result") or {}
            list_items = result.get("list") or []
            if not list_items:
                return "Tidak ada data saldo."
            first = list_items[0]
            total_equity = first.get("totalEquity")
            acct_type = first.get("accountType")
            coins = first.get("coin") or []
            lines = [f"AccountType: {acct_type}", f"TotalEquity: {total_equity}"]
            for c in coins[:10]:
                lines.append(
                    f"{c.get('coin')}: equity={c.get('equity')} avail={c.get('availableToWithdraw')} usdValue={c.get('usdValue')}"
                )
            if len(coins) > 10:
                lines.append(f"… {len(coins) - 10} coin lainnya dipotong")
            return "\n".join(lines)
        except Exception:
            return json.dumps(resp)

    @staticmethod
    def format_tickers(resp: Dict[str, Any]) -> str:
        try:
            result = resp.get("result") or {}
            list_items = result.get("list") or []
            if not list_items:
                return "Ticker tidak ditemukan."
            rows = []
            for it in list_items[:5]:
                symbol = it.get("symbol")
                lp = it.get("lastPrice") or it.get("lastPrice")
                bid1 = it.get("bid1Price")
                ask1 = it.get("ask1Price")
                rows.append(f"{symbol}: last={lp} bid={bid1} ask={ask1}")
            if len(list_items) > 5:
                rows.append(f"… {len(list_items) - 5} simbol lainnya dipotong")
            return "\n".join(rows)
        except Exception:
            return json.dumps(resp)

    @staticmethod
    def format_orderbook(resp: Dict[str, Any], depth: int = 5) -> str:
        try:
            result = resp.get("result") or {}
            a = result.get("a") or []
            b = result.get("b") or []
            lines = ["Asks:"]
            for px, sz in a[:depth]:
                lines.append(f"  {px} x {sz}")
            lines.append("Bids:")
            for px, sz in b[:depth]:
                lines.append(f"  {px} x {sz}")
            return "\n".join(lines)
        except Exception:
            return json.dumps(resp)

    @staticmethod
    def format_recent_trades(resp: Dict[str, Any], limit: int = 5) -> str:
        try:
            result = resp.get("result") or {}
            list_items = result.get("list") or []
            rows = []
            for it in list_items[:limit]:
                side = it.get("side")
                price = it.get("price")
                qty = it.get("qty")
                time = it.get("time")
                rows.append(f"{time} {side} {qty}@{price}")
            return "\n".join(rows) if rows else "Tidak ada trade."
        except Exception:
            return json.dumps(resp)

    async def close(self) -> None:
        """Close underlying HTTP client if initialized."""
        client = getattr(self, "_client", None)
        if client is not None:
            try:
                await client.aclose()
            finally:
                self._client = None
