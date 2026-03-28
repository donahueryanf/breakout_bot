"""
Breakout Signal Bot (V4 - Universal Receiver)
--------------------------------------------
Forcibly bypasses Flask's 415 error by allowing all content types.
"""

import os
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ── Config (set these as environment variables on Railway) ──
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

def send_telegram(message: str):
    """Send a Markdown-formatted message to your Telegram chat."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: TELEGRAM_TOKEN or TELEGRAM_CHAT_ID not set")
        return False
    url  = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       message,
        "parse_mode": "Markdown",
    }
    resp = requests.post(url, data=data, timeout=10)
    return resp.ok

def build_signal_card(d: dict) -> str:
    """Build the full signal card from parsed webhook JSON."""
    side    = d.get("side", "")
    ticker  = d.get("ticker", "???")
    tf      = d.get("tf", "?")
    
    try:
        entry   = float(d.get("entry", 0))
        sl_dist = float(d.get("sl_dist", 0))
        tp_dist = float(d.get("tp_dist", 0))
        lots    = float(d.get("lots", 0))
        risk    = float(d.get("risk_usd", 0))
        adx     = float(d.get("adx", 0))
        knn     = int(float(d.get("knn", 0)))
    except:
        entry = sl_dist = tp_dist = lots = risk = adx = knn = 0

    if side == "LONG":
        sl_price, tp_price, emoji, arrow = entry - sl_dist, entry + tp_dist, "🟢", "LONG"
    elif side == "SHORT":
        sl_price, tp_price, emoji, arrow = entry + sl_dist, entry - tp_dist, "🔴", "SHORT"
    elif "CLOSE" in str(side):
        return f"⚠️ *CLOSE SIGNAL*\n━━━━━━━━━━━━━━━━\nAsset: `{ticker}`\nAction: Close {side}\nPrice: `{entry:.4f}`"
    else:
        return f"Unknown signal: {d}"

    decimals = 2 if entry > 100 else 4
    fmt = f"{{:.{decimals}f}}"
    rr = round(tp_dist / sl_dist, 2) if sl_dist > 0 else 0

    return (
        f"{emoji} *{arrow} SIGNAL*\n━━━━━━━━━━━━━━━━\n"
        f"Asset: `{ticker}` | TF: `{tf}m`\n"
        f"Entry: `{fmt.format(entry)}` | Lots: `{lots}`\n"
        f"SL: `{fmt.format(sl_price)}` | TP: `{fmt.format(tp_price)}`\n"
        f"Risk: `${risk:.2f}` | RR: `1:{rr}`\n"
        f"ADX: `{adx:.1f}` | KNN: `{knn}`\n━━━━━━━━━━━━━━━━"
    )

# THE FIX: force_json=True tells Flask to ignore the 415 check
@app.route("/webhook", methods=["POST"])
def webhook():
    # Attempt to parse data regardless of what the header says
    data = request.get_json(force=True, silent=True)
    
    if not data:
        # If it's not JSON, try reading the raw body text
        try:
            raw_data = request.data.decode('utf-8')
            data = json.loads(raw_data)
        except:
            print(f"FAILED TO PARSE: {request.data}")
            return jsonify({"error": "Unsupported Media Type - please send JSON"}), 415

    print(f"SIGNAL RECEIVED: {data.get('ticker')}")
    try:
        card = build_signal_card(data)
        ok = send_telegram(card)
        return jsonify({"ok": ok}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
