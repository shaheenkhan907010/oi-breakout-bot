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
page2_after = ex._get(path, {"instId": sym, "period": "1H", "limit": 100, "after": oldest})
print("\npage2 (after=oldest) len:", len(page2_after))
if page2_after:
    ts2 = [int(r[0]) for r in page2_after]
    print("page2 ts range:", min(ts2), "..", max(ts2))

newest = max(ts1)
page2_before = ex._get(path, {"instId": sym, "period": "1H", "limit": 100, "before": oldest})
print("\npage2 (before=oldest) len:", len(page2_before))
if page2_before:
    ts3 = [int(r[0]) for r in page2_before]
    print("page2(before) ts range:", min(ts3), "..", max(ts3))

# also check: is page1 sorted ascending or descending?
print("\npage1 first row ts:", ts1[0], "last row ts:", ts1[-1], "(ascending if first<last)")
