"""Temporary probe: understand OKX open-interest-history pagination semantics.
Not part of the production workflow -- delete once confirmed."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import okx_client as ex

sym = "BTC-USDT-SWAP"
path = "/api/v5/rubik/stat/contracts/open-interest-history"

page1 = ex._get(path, {"instId": sym, "period": "1H", "limit": 100})
print("page1 len:", len(page1))
ts1 = [int(r[0]) for r in page1]
print("page1 ts range:", min(ts1), "..", max(ts1))

oldest = min(ts1)
page2_end = ex._get(path, {"instId": sym, "period": "1H", "limit": 100, "end": oldest - 1})
print("\npage2 (end=oldest-1) len:", len(page2_end))
if page2_end:
    ts2 = [int(r[0]) for r in page2_end]
    print("page2 ts range:", min(ts2), "..", max(ts2))

# also check: is page1 sorted ascending or descending?
print("\npage1 first row ts:", ts1[0], "last row ts:", ts1[-1], "(ascending if first<last)")

print("\n--- full get_oi_hist_1h(total=700) ---")
full = ex.get_oi_hist_1h(sym, total=700)
print("points:", len(full))
if full:
    print("range:", full[0]["t"], "..", full[-1]["t"],
          "=", (full[-1]["t"] - full[0]["t"]) / 3600000, "hours")
