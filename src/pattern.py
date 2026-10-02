"""
Direct Python port of the detect()/agg()/oiFor() logic from
~/Desktop/oi-breakout-scanner.html -- same rules, same indices, same order
of checks. Do not "simplify" the checks without re-reading that file first.
"""

H = 3600_000  # 1 hour in ms

DEFAULT_PARAMS = {
    "pump": 40,      # % price pump
    "win": 20,       # candles window for the pump low
    "oiPump": 30,    # % OI pump
    "dump": 15,      # % dump from the pump top
    "oiRed": True,   # breakout candle's OI must be red (lower than prior candle)
    "oiBelow": True, # breakout candle's OI must be below the pump-window OI peak
    "gap": 3,        # min candles between pump top and breakout candle
}


def agg(b1, tf):
    """1H bars -> tf-hour bars (UTC aligned), closed groups only."""
    if tf == 1:
        return list(b1)
    ms = tf * H
    out = []
    cur = None
    cnt = 0
    for x in b1:
        g = x["t"] // ms
        if cur is None or cur["g"] != g:
            if cur is not None and cnt == tf:
                out.append(cur)
            cur = {"g": g, "t": g * ms, "o": x["o"], "h": x["h"], "l": x["l"],
                   "c": x["c"], "v": x["v"], "ct": g * ms + ms - 1}
            cnt = 1
        else:
            cur["h"] = max(cur["h"], x["h"])
            cur["l"] = min(cur["l"], x["l"])
            cur["c"] = x["c"]
            cur["v"] += x["v"]
            cnt += 1
    if cur is not None and cnt == tf:
        out.append(cur)
    return out


def oi_for(bars, oi):
    """OI snapshot as of each bar's close time (within a 2h tolerance)."""
    out = [None] * len(bars)
    k = -1
    for i, b in enumerate(bars):
        T = b["ct"] + 1
        while k + 1 < len(oi) and oi[k + 1]["t"] <= T:
            k += 1
        if k >= 0 and T - oi[k]["t"] <= 2 * H:
            out[i] = oi[k]["v"]
    return out


def look_bars(bars):
    """~26 days of lookback, in units of this timeframe's bar count."""
    if len(bars) > 1:
        return round(26 * 24 * H / (bars[1]["t"] - bars[0]["t"]))
    return 150


def detect(bars, oi, params, frm, to):
    """
    Returns signals for i in [frm, to] where:
      1. price pumped >= params['pump']% within params['win'] candles into a top (pk),
         and OI pumped >= params['oiPump']% over the same window (when oi given),
      2. price then dumped >= params['dump']% from that top,
      3. bar i is the FIRST close back above that top (breakout),
      4. OI on bar i is red vs bar i-1, and below the pump-window OI peak
         (when oi given and params['oiRed']/['oiBelow'] are set).
    """
    out = []
    n = len(bars)
    gap = params["gap"]
    lb = params.get("lookBars") or look_bars(bars)
    for i in range(max(frm, gap + 2), to + 1):
        if not (bars[i]["c"] > bars[i - 1]["h"]):
            continue
        s = max(0, i - lb)
        pk = s
        for j in range(s, i):
            if bars[j]["h"] >= bars[pk]["h"]:
                pk = j
        if i - pk < gap:
            continue
        lvl = bars[pk]["h"]
        if not (bars[i]["c"] > lvl and bars[i - 1]["c"] <= lvl):
            continue
        ws = max(0, pk - params["win"])
        lo = ws
        for j in range(ws, pk + 1):
            if bars[j]["l"] < bars[lo]["l"]:
                lo = j
        pump = (lvl / bars[lo]["l"] - 1) * 100
        if pump < params["pump"]:
            continue
        mn = float("inf")
        for j in range(pk + 1, i):
            mn = min(mn, bars[j]["l"])
        dump = (lvl - mn) / lvl * 100
        if dump < params["dump"]:
            continue
        sig = {"i": i, "pk": pk, "lo": lo, "lvl": lvl, "pump": pump, "dump": dump}
        if oi is not None:
            if oi[i] is None or oi[i - 1] is None:
                continue
            o_min, o_max = float("inf"), float("-inf")
            for j in range(max(0, lo - 1), min(n - 1, pk + 1) + 1):
                if oi[j] is None:
                    continue
                if j <= pk:
                    o_min = min(o_min, oi[j])
                o_max = max(o_max, oi[j])
            if not (o_min < float("inf") and o_max > float("-inf")):
                continue
            sig["oiPump"] = (o_max / o_min - 1) * 100
            if sig["oiPump"] < params["oiPump"]:
                continue
            sig["oiChg"] = (oi[i] / oi[i - 1] - 1) * 100
            sig["oiVsPk"] = (oi[i] / o_max - 1) * 100
            if params["oiRed"] and not (oi[i] < oi[i - 1]):
                continue
            if params["oiBelow"] and not (oi[i] < o_max):
                continue
        out.append(sig)
    return out
