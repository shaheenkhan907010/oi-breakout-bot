# oi-breakout-bot

24/7 scanner (runs on GitHub Actions, no server/laptop needed) for this pattern on
USDT-margined perpetual futures:

1. **Pump**: price up >=40% within 20 candles, with open interest up >=30% over the
   same window.
2. **Dump**: price then falls >=15% from that pump's top.
3. **Breakout**: a candle closes above that top for the first time.
4. **OI red**: on the breakout candle, OI is lower than the prior candle *and* still
   below the pump-window OI peak.

Timeframes: 1H, 2H, 3H, 4H, 1D — all aggregated from 1H candles. Only closed candles
are evaluated. Coins are filtered to >= $1M 24h quote volume.

Ported directly from the `detect()`/`agg()`/`oiFor()` logic in the original
`oi-breakout-scanner.html` prototype — see `src/pattern.py`.

## Data source: OKX

Binance Futures and Bybit are both geo-blocked (HTTP 451 / 403) from GitHub Actions'
US-based runners. This was confirmed with a live test workflow before writing any
scanning code — not assumed. **OKX's public market-data API works** and provides
both candles and open-interest history, so the bot is built on it
(`src/okx_client.py`).

## How it runs

- `.github/workflows/scan.yml` runs every hour at minute 2 (UTC) via cron, plus
  `workflow_dispatch` for a manual run (with a `test_email` option to just verify
  SMTP without scanning).
- Already-alerted signals are deduplicated across runs using a GitHub Actions cache
  (`cache/seen.json`), pruned after 5 days.
- Alerts are emailed via Gmail SMTP. Required repo secrets: `GMAIL_USER`,
  `GMAIL_APP_PASSWORD` (a Gmail App Password, not the account password),
  `ALERT_TO`.

## Local layout

- `src/okx_client.py` — OKX REST client (symbols, 1H klines, OI history).
- `src/pattern.py` — pump/dump/breakout/OI-red detection (ported 1:1 from the HTML).
- `src/emailer.py` — email formatting + Gmail SMTP send.
- `main.py` — orchestration, dedup cache, entry point.
