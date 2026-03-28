import os
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Config from Railway Variables
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

def send_telegram(message: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Error: Missing Telegram Config")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown", "disable_web_page_preview": False}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        return resp.ok
    except Exception as e:
        print(f"❌ Telegram Fail: {e}")
        return False

def build_card(d):
    # FALLBACKS: "BTCUSDT" and "60" are just defaults if the data is missing
    ticker  = d.get("ticker", "BTCUSDT")
    side    = str(d.get("side", "SIGNAL")).upper()
    tf      = d.get("tf", "60")
    
    try:
        entry   = float(d.get("entry", 0))
        sl_dist = float(d.get("sl_dist", 0))
        tp_dist = float(d.get("tp_dist", 0))
        risk    = float(d.get("risk_usd", 25.00))
        lots    = d.get("lots", "0.00")
    except:
        entry = sl_dist = tp_dist = risk = 0
        lots  = "0.00"

    # Calc Directional Prices
    if "BUY" in side or "LONG" in side:
        sl_p, tp_p, emoji, action = entry - sl_dist, entry + tp_dist, "🟢", "LONG"
    else:
        sl_p, tp_p, emoji, action = entry + sl_dist, entry - tp_dist, "🔴", "SHORT"

    # Precision for crypto vs stocks/forex
    prec = 2 if entry > 100 else (4 if entry > 1 else 6)
    rr = round(tp_dist / sl_dist, 2) if sl_dist > 0 else 0

    return (
        f"{emoji} *{action} SIGNAL: {ticker}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 *Lots to Enter:* `{lots}`\n"
        f"📈 *Entry:* `{entry:.{prec}f}`\n"
        f"🛡️ *Stop:* `{sl_p:.{prec}f}`\n"
        f"🎯 *Target:* `{tp_p:.{prec}f}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 *Risk:* `${risk:.2f}` | ⚖️ *R:R:* `1:{rr}`\n"
        f"⏱️ *TF:* `{tf}m`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 [Open Chart in TradingView](https://www.tradingview.com/chart/?symbol={ticker}&interval={tf})\n"
        f"⚡ _Manual execution required_"
    )

@app.route("/webhook", methods=["POST"])
def webhook():
    # Force JSON parsing even if content-type is wrong
    data = request.get_json(force=True, silent=True)
    if not data:
        try:
            data = json.loads(request.data.decode('utf-8'))
        except:
            return jsonify({"error": "Format Error"}), 400

    print(f"✅ Received signal for {data.get('ticker')}")
    card = build_card(data)
    send_telegram(card)
    return jsonify({"status": "delivered"}), 200

@app.errorhandler(415)
def handle_415(e):
    return webhook()

@app.route("/health")
def health():
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
