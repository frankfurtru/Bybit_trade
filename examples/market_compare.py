#!/usr/bin/env python3
"""
Market compare (public endpoints, no API keys).
Compares best bid/ask & mid across multiple exchanges and prints a table.

Usage:
  python examples/market_compare.py
  python examples/market_compare.py --symbols BTCUSDT ETHUSDT SOLUSDT --ref bybit


Exchanges included (public REST):
- binance  (spot)
- bybit    (linear USDT perps; also works for some spot symbols)
- bingx    (spot)  *symbol mapping uses BTC-USDT/ETH-USDT, etc.

Notes:
- Endpoints occasionally change; this script is defensive and will skip an
  exchange on error rather than crash.
- You can add/remove exchanges in the EXCHANGES list below.
"""

from __future__ import annotations
import argparse
import time
from typing import Dict, Tuple, Optional, List
import requests

# --------- HTTP basics ---------
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "market-compare/0.1"})
TIMEOUT = 8

def _get(url: str, params: Dict[str, str] | None = None) -> Dict:
    r = SESSION.get(url, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

# --------- Symbol mappers ---------
def norm(symbol: str) -> str:
    """Normalize common variations: BTC/USDT → BTCUSDT."""
    s = symbol.upper().replace("/", "").replace("-", "")
    return s

def to_bingx(symbol: str) -> str:
    """BingX spot often uses hyphen: BTC-USDT."""
    s = norm(symbol)
    # Insert '-' before last 4 letters when ends with USDT/USDC/etc.
    # Simple heuristic:
    if s.endswith("USDT"):
        return s[:-4] + "-" + "USDT"
    if s.endswith("USDC"):
        return s[:-4] + "-" + "USDC"
    if s.endswith("BUSD"):
        return s[:-4] + "-" + "BUSD"
    # Fallback: BTCUSDT -> BTC-USDT style
    if len(s) >= 6:
        return s[:-4] + "-" + s[-4:]
    return s

def to_bybit_linear(symbol: str) -> str:
    """Bybit linear perps typically: BTCUSDT, ETHUSDT (same)."""
    return norm(symbol)

def to_binance(symbol: str) -> str:
    """Binance spot bookTicker uses: BTCUSDT, ETHUSDT, ..."""
    return norm(symbol)

# --------- Adapters (return bid, ask, ts_ms) ---------
def fetch_binance(symbol: str) -> Tuple[float, float, int]:
    sym = to_binance(symbol)
    data = _get("https://api.binance.com/api/v3/ticker/bookTicker", {"symbol": sym})
    bid = float(data["bidPrice"])
    ask = float(data["askPrice"])
    ts = int(time.time() * 1000)
    return bid, ask, ts

def fetch_bybit(symbol: str) -> Tuple[float, float, int]:
    sym = to_bybit_linear(symbol)
    # Linear (perp) category; also returns for some spot symbols.
    data = _get("https://api.bybit.com/v5/market/tickers",
                {"category": "linear", "symbol": sym})
    if not data.get("result") or not data["result"].get("list"):
        # Try spot as fallback
        data = _get("https://api.bybit.com/v5/market/tickers",
                    {"category": "spot", "symbol": sym})
    item = data["result"]["list"][0]
    bid = float(item.get("bid1Price") or item.get("bidPrice") or item["lastPrice"])
    ask = float(item.get("ask1Price") or item.get("askPrice") or item["lastPrice"])
    ts = int(item.get("ts") or time.time() * 1000)
    return bid, ask, ts

def fetch_bingx(symbol: str) -> Tuple[float, float, int]:
    # Spot ticker; BingX commonly expects BTC-USDT style
    sym = to_bingx(symbol)
    # Some deployments use /openApi/spot/market/ticker; others have a slightly different path.
    # We try one, then fall back to another if needed.
    try:
        data = _get("https://open-api.bingx.com/openApi/spot/market/ticker", {"symbol": sym})
    except Exception:
        data = _get("https://open-api.bingx.com/openApi/market/ticker", {"symbol": sym})
    # Many responses have shape {"code":0,"msg":"success","data":{"symbol":"BTC-USDT","askPrice":"...","bidPrice":"..."}}
    d = data.get("data") or {}
    # Some variants return a list; handle both
    if isinstance(d, list) and d:
        d = d[0]
    bid = float(d.get("bidPrice") or d.get("bid") or d.get("bestBid") or 0.0)
    ask = float(d.get("askPrice") or d.get("ask") or d.get("bestAsk") or 0.0)
    if not bid or not ask:
        # Try depth as last resort (top of book)
        depth = _get("https://open-api.bingx.com/openApi/spot/market/depth", {"symbol": sym, "limit": 5})
        bids = depth.get("data", {}).get("bids") or []
        asks = depth.get("data", {}).get("asks") or []
        if bids: bid = float(bids[0][0])
        if asks: ask = float(asks[0][0])
    ts = int(time.time() * 1000)
    if not bid or not ask:
        raise RuntimeError(f"BingX returned empty book for {sym}")
    return bid, ask, ts

# Register exchanges here
EXCHANGES = {
    "binance": fetch_binance,
    "bybit": fetch_bybit,
    "bingx": fetch_bingx,
}

# --------- Computation & formatting ---------
def bps(x: float) -> float:
    return x * 1e4

def fmt(x: Optional[float], width: int = 10) -> str:
    if x is None:
        return " " * (width - 1) + "-"
    return f"{x:>{width}.2f}"

def compare(symbols: List[str], ref: str) -> None:
    ref = ref.lower()
    if ref not in EXCHANGES:
        raise SystemExit(f"--ref must be one of: {', '.join(EXCHANGES)}")

    print(f"\nMarket Compare • symbols={symbols} • ref={ref}")
    print("=" * 86)
    header = f"{'SYMBOL':<10} {'EXCHANGE':<10} {'BID':>12} {'ASK':>12} {'MID':>12} {'SPR (bps)':>10} {'Δ vs REF (%)':>12}"
    print(header)
    print("-" * len(header))

    for sym in symbols:
        symN = norm(sym)
        # First collect all mids to compute deltas vs ref
        rows = []
        ref_mid: Optional[float] = None
        for name, fn in EXCHANGES.items():
            try:
                bid, ask, ts = fn(symN)
                mid = (bid + ask) / 2.0
                spread_bps = bps((ask - bid) / mid) if mid else None
                rows.append((name, bid, ask, mid, spread_bps))
                if name == ref:
                    ref_mid = mid
            except Exception as e:
                rows.append((name, None, None, None, None))

        # Print, calculating deltas once we know ref_mid
        for (name, bid, ask, mid, spread_bps) in rows:
            delta_pct = None
            if mid and ref_mid:
                delta_pct = (mid / ref_mid - 1.0) * 100.0
            print(
                f"{symN:<10} {name:<10} {fmt(bid,12)} {fmt(ask,12)} {fmt(mid,12)} "
                f"{fmt(spread_bps,10)} {fmt(delta_pct,12)}"
            )
        print("-" * len(header))

    print("Notes:")
    print(" • SPR (bps) = (ask - bid) / mid * 10,000")
    print(" • Δ vs REF compares each exchange's mid to the reference exchange mid")
    print(" • If a row shows '-' values, that exchange's public endpoint returned no data or changed")

# --------- CLI ---------
def main():
    p = argparse.ArgumentParser(description="Compare best bid/ask across exchanges (public endpoints).")
    p.add_argument("--symbols", nargs="+", default=["BTCUSDT", "ETHUSDT"], help="Symbols to compare (e.g., BTCUSDT ETHUSDT)")
    p.add_argument("--ref", default="binance", choices=list(EXCHANGES.keys()), help="Reference exchange for Δ calculation")
    args = p.parse_args()

    # Light rate-limit friendliness
    try:
        compare(args.symbols, ref=args.ref)
    finally:
        SESSION.close()

if __name__ == "__main__":
    main()

