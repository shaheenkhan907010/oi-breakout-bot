"""Temporary debug script: exercises the full pipeline (symbols -> klines -> OI ->
agg -> detect) on GitHub Actions without sending any email, so it needs no secrets.
Not part of the production workflow -- delete once the pipeline is confirmed.
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import okx_client as ex
from pattern import agg, oi_for, detect, look_bars, DEFAULT_PARAMS, H

t0 = time.time()
syms = ex.get_symbols(1_000_000)
print(f"symbols with 24h vol >= $1M: {len(syms)}")
print("sample:", syms[:10])

test_syms = syms[:8] if syms else ["BTC-USDT-SWAP", "ETH-USDT-SWAP"]
total_signals = 0
for sym in test_syms:
    try:
        b1 = ex.get_klines_1h(sym, total=800)
    except Exception as e:
        print(f"{sym}: klines error {e}")
        continue
    if len(b1) < 30:
        print(f"{sym}: only {len(b1)} 1h bars, skipping")
        continue
    try:
        oi_raw = ex.get_oi_hist_1h(sym, total=700)
    except Exception as e:
        print(f"{sym}: oi error {e}")
        oi_raw = []

    now = int(time.time() * 1000)
    row = [sym, len(b1), len(oi_raw)]
    for tf in [1, 2, 3, 4, 24]:
        b = agg(b1, tf)
        if len(b) < 12:
            continue
        params = dict(DEFAULT_PARAMS)
        params["lookBars"] = look_bars(b)
        last = len(b) - 1
        oi = oi_for(b, oi_raw)
        sigs_hist = detect(b, oi, params, max(params["gap"] + 2, 0), last)
        fresh = "fresh" if now - b[last]["ct"] <= tf * H else "stale"
        row.append(f"tf{tf}:bars={len(b)}:{fresh}:hist_sigs={len(sigs_hist)}")
        total_signals += len(sigs_hist)
    print(row)

print(f"\nDone in {time.time()-t0:.1f}s. total historical signals across sample: {total_signals}")
