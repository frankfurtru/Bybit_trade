from fastapi import FastAPI
import requests
app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ticker/{symbol}")
def ticker(symbol: str):
    r = requests.get("https://api.bybit.com/v5/market/tickers",
                     params={"category":"linear","symbol":symbol})
    r.raise_for_status()
    return r.json()
