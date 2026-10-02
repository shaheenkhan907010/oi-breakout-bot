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
    raise RuntimeError(f"OKX request exhausted retries: {path}")


def _paginate(path, base_params, limit, total, max_pages=30, start_after=None):
    """Page an OKX market-data endpoint backwards in time via `after`.
    Stops on: no rows, a short page (end of data), no progress (ts not
    decreasing -- guards against `after` being ignored), or max_pages."""
    out = {}
    after = start_after
    for _ in range(max_pages):
        if len(out) >= total:
            break
        params = dict(base_params, limit=limit)
        if after:
            params["after"] = after
        rows = _get(path, params)
        if not rows:
            break
        oldest = min(int(row[0]) for row in rows)
        for row in rows:
            out[int(row[0])] = row
        if after is not None and oldest >= after:
            break  # no progress -- stop instead of looping forever
        after = oldest
        if len(rows) < limit:
            break
    return out


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
    base = {"instId": inst_id, "bar": "1H"}
    out = _paginate("/api/v5/market/candles", base, 300, total)
    if len(out) < total:
        oldest_so_far = min(out) if out else None
        more = _paginate("/api/v5/market/history-candles", base, 100,
                          total - len(out), start_after=oldest_so_far)
        out.update(more)

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
    base = {"instId": inst_id, "period": "1H"}
    rows = _paginate("/api/v5/rubik/stat/contracts/open-interest-history", base, 100, total)
    return [{"t": ts, "v": float(rows[ts][2])} for ts in sorted(rows.keys())]
