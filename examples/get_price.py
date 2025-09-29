import requests
r = requests.get("https://api.bybit.com/v5/market/tickers",
                 params={"category":"linear","symbol":"ETHUSDT"})
r.raise_for_status()
print(r.json())
