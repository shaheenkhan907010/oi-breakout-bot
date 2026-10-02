"""
OKX public REST client (USDT-margined perpetual swaps).

Binance Futures and Bybit are both geo-blocked (451 / 403) from GitHub Actions'
US-based runners -- confirmed with a live test run. OKX's public market-data
API is reachable and provides both candles and open-interest history, so this
bot is built on OKX.
"""
import time
import requests

BASE = "https://www.okx.com"
H = 3600_000  # 1 hour in ms
TIMEOUT = 20
session = requests.Session()
session.headers.update({"User-Agent": "oi-breakout-bot/1.0"})


def _get(path, params=None, tries=4):
    url = BASE + path
    for i in range(tries):
        try:
            r = session.get(url, params=params, timeout=TIMEOUT)
            if r.status_code == 429:
                time.sleep(1.5 * (i + 1))
                continue
            r.raise_for_status()
            data = r.json()
            if data.get("code") != "0":
                raise RuntimeError(f"OKX error {data.get('code')}: {data.get('msg')}")
            return data["data"]
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(0.6 * (i + 1))


def get_symbols(min_vol_usd):
    """USDT-margined perpetual swaps with 24h quote volume >= min_vol_usd."""
    instruments = _get("/api/v5/public/instruments", {"instType": "SWAP"})
    live = {
        row["instId"]
        for row in instruments
        if row.get("state") == "live" and row["instId"].endswith("-USDT-SWAP")
    }
    tickers = _get("/api/v5/market/tickers", {"instType": "SWAP"})
    vol = {row["instId"]: float(row.get("volCcy24h") or 0) for row in tickers}
    syms = [s for s in live if vol.get(s, 0) >= min_vol_usd]
    syms.sort(key=lambda s: vol.get(s, 0), reverse=True)
    return syms


def get_klines_1h(inst_id, total=800):
    """Closed 1H candles, oldest -> newest: [{t,o,h,l,c,v,ct}, ...]."""
    out = {}
    after = None
    # 1) recent candles (kept for a limited lookback window)
    while len(out) < total:
        params = {"instId": inst_id, "bar": "1H", "limit": 300}
        if after:
            params["after"] = after
        rows = _get("/api/v5/market/candles", params)
        if not rows:
            break
        oldest = None
        for row in rows:
            ts = int(row[0])
            oldest = ts if oldest is None else min(oldest, ts)
            out[ts] = row
        after = oldest
        if len(rows) < 300:
            break
    # 2) deep history for anything still missing
    while len(out) < total:
        rows = _get("/api/v5/market/history-candles", {
            "instId": inst_id, "bar": "1H", "limit": 100, "after": after,
        })
        if not rows:
            break
        oldest = None
        for row in rows:
            ts = int(row[0])
            oldest = ts if oldest is None else min(oldest, ts)
            out[ts] = row
        after = oldest
        if len(rows) < 100:
            break

    now = int(time.time() * 1000)
    bars = []
    for ts in sorted(out.keys()):
        row = out[ts]
        o, h, l, c, v, confirm = float(row[1]), float(row[2]), float(row[3]), float(row[4]), float(row[5]), row[8]
        ct = ts + H - 1
        if confirm != "1" or ct > now:
            continue
        bars.append({"t": ts, "o": o, "h": h, "l": l, "c": c, "v": v, "ct": ct})
    return bars


def get_oi_hist_1h(inst_id, total=700):
    """Open interest history (coin-denominated, oiCcy), oldest -> newest."""
    out = {}
    after = None
    while len(out) < total:
        params = {"instId": inst_id, "period": "1H", "limit": 100}
        if after:
            params["after"] = after
        rows = _get("/api/v5/rubik/stat/contracts/open-interest-history", params)
        if not rows:
            break
        oldest = None
        for row in rows:
            ts = int(row[0])
            oldest = ts if oldest is None else min(oldest, ts)
            out[ts] = float(row[2])  # oiCcy
        if len(rows) < 100:
            break
        after = oldest

    return [{"t": ts, "v": out[ts]} for ts in sorted(out.keys())]
