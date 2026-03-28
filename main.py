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
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        return resp.ok
    except:
        return False

def build_card(d):
    ticker  = d.get("ticker", "BTCUSDT")
    side    = str(d.get("side", "SIGNAL")).upper()
    tf      = d.get("tf", "60")
    
    try:
        entry   = float(d.get("entry", 0))
        sl_dist = float(d.get("sl_dist", 0))
        tp_dist = float(d.get("tp_dist", 0))
        risk    = float(d.get("risk_usd", 25.00))
        # This captures the 'lots' from the JSON above
        lots    = d.get("lots", "0.00")
    except:
        entry = sl_dist = tp_dist = risk = 0
        lots  = "0.00"

    if "BUY" in side or "LONG" in side:
        sl_price, tp_price, emoji, action = entry - sl_dist, entry + tp_dist, "🟢", "LONG"
    else:
        sl_price, tp_price, emoji, action = entry + sl_dist, entry - tp_dist, "🔴", "SHORT"

    # Decimal precision: 2 for BTC/high price, 4+ for others
    prec = 2 if entry > 100 else 4
    rr = round(tp_dist / sl_dist, 2) if sl_dist > 0 else 0

    return (
        f"{emoji} *{action} SIGNAL: {ticker}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 *Lots to Enter:* `{lots}`\n"
        f"📈 *Entry:* `{entry:.{prec}f}`\n"
        f"🛡️ *Stop:* `{sl_price:.{prec}f}`\n"
        f"🎯 *Target:* `{tp_price:.{prec}f}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 *Risk:* `${risk:.2f}` | ⚖️ *R:R:* `1:{rr}`\n"
        f"⏱️ *TF:* `{tf}m`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 [Open Chart in TradingView](https://www.tradingview.com/chart/?symbol={ticker}&interval={tf})\n"
        f"⚡ _Manual execution required_"
    )
    
@app.route("/webhook", methods=["POST"])
def webhook():
    # This is the 'Master Key': it reads the raw data regardless of the 415 error
    raw_data = request.get_data(as_text=True)
    
    try:
        data = json.loads(raw_data)
    except Exception as e:
        print(f"Manual Parse Failed: {e}")
        # Try one last ditch effort if it's form-encoded
        data = request.form.to_dict()
    
    if not data:
        return jsonify({"error": "Empty body"}), 400

    print(f"Accepted Signal for: {data.get('ticker')}")
    card = build_card(data)
    send_telegram(card)
    return jsonify({"status": "received"}), 200

# This catches the 415 before Flask can show it to TradingView
@app.errorhandler(415)
def handle_415(e):
    return webhook()

@app.route("/health")
def health():
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
