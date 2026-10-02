import os
import smtplib
from email.mime.text import MIMEText

TFN = {1: "1H", 2: "2H", 3: "3H", 4: "4H", 24: "1D"}


def tv_link(inst_id):
    base = inst_id.split("-")[0]
    return f"https://www.tradingview.com/chart/?symbol=OKX:{base}USDT.P"


def send_email(subject, body):
    user = os.environ["GMAIL_USER"]
    password = os.environ["GMAIL_APP_PASSWORD"]
    to = os.environ["ALERT_TO"]

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as s:
        s.starttls()
        s.login(user, password)
        s.sendmail(user, [to], msg.as_string())


def signal_email(inst_id, tf, sig, price, close_time_ms):
    import datetime
    tfn = TFN[tf]
    when = datetime.datetime.utcfromtimestamp(close_time_ms / 1000).strftime("%Y-%m-%d %H:%M UTC")
    subject = f"OI Breakout: {inst_id} {tfn} — {price:.6g}"
    body = (
        f"Coin: {inst_id}\n"
        f"Timeframe: {tfn}\n"
        f"Candle closed: {when}\n"
        f"Breakout level (pump top): {sig['lvl']:.6g}\n"
        f"Price (breakout close): {price:.6g}\n"
        f"Pump: +{sig['pump']:.1f}%\n"
        f"OI pump: +{sig['oiPump']:.1f}%\n"
        f"Dump from top: -{sig['dump']:.1f}%\n"
        f"OI change on breakout candle: {sig['oiChg']:+.1f}%\n"
        f"OI vs pump peak: {sig['oiVsPk']:+.1f}%\n"
        f"TradingView: {tv_link(inst_id)}\n"
        f"\nSource: OKX futures (Binance/Bybit are geo-blocked on GitHub Actions runners).\n"
    )
    return subject, body
