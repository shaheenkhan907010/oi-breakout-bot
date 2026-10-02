"""
One-off connectivity check, run from GitHub Actions, to see which exchange's
futures REST API (klines/candles + open-interest history) is reachable from
GitHub's (US) runners. Binance is known to geo-block US IPs with 451/403 on
some endpoints -- this confirms it either way instead of guessing.
"""
import json
import sys
import urllib.request
import urllib.error

TIMEOUT = 15


def fetch(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read()
            return r.status, body[:300]
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:300]
    except Exception as e:
        return None, str(e)[:300]


def check(name, klines_url, oi_url):
    print(f"\n=== {name} ===")
    ok = True
    status, body = fetch(klines_url)
    print(f"klines  -> status={status} body={body}")
    if status != 200:
        ok = False
    status, body = fetch(oi_url)
    print(f"oi_hist -> status={status} body={body}")
    if status != 200:
        ok = False
    print(f"{name} USABLE = {ok}")
    return ok


results = {}

results["binance"] = check(
    "binance",
    "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=1h&limit=5",
    "https://fapi.binance.com/futures/data/openInterestHist?symbol=BTCUSDT&period=1h&limit=5",
)

results["bybit"] = check(
    "bybit",
    "https://api.bybit.com/v5/market/kline?category=linear&symbol=BTCUSDT&interval=60&limit=5",
    "https://api.bybit.com/v5/market/open-interest?category=linear&symbol=BTCUSDT&intervalTime=1h&limit=5",
)

results["okx"] = check(
    "okx",
    "https://www.okx.com/api/v5/market/candles?instId=BTC-USDT-SWAP&bar=1H&limit=5",
    "https://www.okx.com/api/v5/rubik/stat/contracts/open-interest-history?instId=BTC-USDT-SWAP&period=1H&limit=5",
)

print("\n=== SUMMARY ===")
print(json.dumps(results, indent=2))

usable = [k for k, v in results.items() if v]
print("\nUSABLE EXCHANGES:", usable)
if not usable:
    print("NONE of binance/bybit/okx are reachable with both endpoints from this runner.")
    sys.exit(1)
