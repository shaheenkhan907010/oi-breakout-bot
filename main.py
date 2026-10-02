import json
import os
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import okx_client as ex  # noqa: E402
from pattern import agg, oi_for, detect, look_bars, DEFAULT_PARAMS, H  # noqa: E402
import emailer  # noqa: E402

TFS = [1, 2, 3, 4, 24]
MIN_VOL_USD = float(os.environ.get("MIN_VOL_USD", "1000000"))
SEEN_FILE = os.path.join(os.path.dirname(__file__), "cache", "seen.json")
SEEN_TTL_MS = 5 * 24 * H
WORKERS = 6


def load_seen():
    try:
        with open(SEEN_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_seen(seen):
    os.makedirs(os.path.dirname(SEEN_FILE), exist_ok=True)
    now = int(time.time() * 1000)
    seen = {k: v for k, v in seen.items() if now - v <= SEEN_TTL_MS}
    with open(SEEN_FILE, "w") as f:
        json.dump(seen, f)


def scan_symbol(sym):
    """Returns a list of (tf, sig, bars, close_time_ms, price) fresh signals for this symbol."""
    results = []
    try:
        b1 = ex.get_klines_1h(sym, total=800)
    except Exception:
        return results
    if len(b1) < 30:
        return results

    now = int(time.time() * 1000)
    candidates = []
    for tf in TFS:
        b = agg(b1, tf)
        if len(b) < 12:
            continue
        last = len(b) - 1
        if now - b[last]["ct"] > tf * H:
            continue  # this timeframe's candle did not just close
        params = dict(DEFAULT_PARAMS)
        params["lookBars"] = look_bars(b)
        if detect(b, None, params, last, last):
            candidates.append((tf, b, params))

    if not candidates:
        return results

    try:
        oi_raw = ex.get_oi_hist_1h(sym, total=700)
    except Exception:
        return results

    for tf, b, params in candidates:
        oi = oi_for(b, oi_raw)
        last = len(b) - 1
        sigs = detect(b, oi, params, last, last)
        if sigs:
            g = sigs[0]
            results.append((tf, g, b[last]["ct"], b[last]["c"]))
    return results


def run_scan():
    seen = load_seen()
    sent = 0
    try:
        syms = ex.get_symbols(MIN_VOL_USD)
    except Exception as e:
        print("ERROR fetching symbol list:", e)
        traceback.print_exc()
        return 1
    print(f"Scanning {len(syms)} symbols (min 24h vol ${MIN_VOL_USD:,.0f})...")

    new_signals = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = {pool.submit(scan_symbol, s): s for s in syms}
        done = 0
        for fut in as_completed(futs):
            sym = futs[fut]
            done += 1
            try:
                for tf, g, close_t, price in fut.result():
                    new_signals.append((sym, tf, g, close_t, price))
            except Exception as e:
                print(f"  [{sym}] error: {e}")
            if done % 25 == 0 or done == len(syms):
                print(f"  progress {done}/{len(syms)}")

    for sym, tf, g, close_t, price in new_signals:
        key = f"{sym}|{tf}|{close_t}"
        if key in seen:
            continue
        seen[key] = int(time.time() * 1000)
        try:
            subject, body = emailer.signal_email(sym, tf, g, price, close_t)
            emailer.send_email(subject, body)
            sent += 1
            print(f"ALERT sent: {key} — {subject}")
        except Exception as e:
            print(f"  failed to email {key}: {e}")
            traceback.print_exc()

    save_seen(seen)
    print(f"Done. {len(new_signals)} signals found, {sent} new emails sent.")
    return 0


def run_test_email():
    subject = "OI Breakout Bot — test email"
    body = (
        "This is a test email from oi-breakout-bot.\n"
        "If you received this, Gmail SMTP + GitHub Actions secrets are working.\n"
        "Data source: OKX futures (Binance/Bybit are geo-blocked on GitHub Actions runners).\n"
    )
    emailer.send_email(subject, body)
    print("Test email sent.")
    return 0


if __name__ == "__main__":
    if os.environ.get("TEST_EMAIL", "false").lower() == "true":
        sys.exit(run_test_email())
    sys.exit(run_scan())
