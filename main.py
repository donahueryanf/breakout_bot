"""
Breakout Signal Bot
-------------------
Receives TradingView webhook alerts from the KNN Pine Script,
formats a full signal card, and sends it to Telegram.

Deploy free on Railway: https://railway.app
"""

import os
import json
import hmac
import hashlib
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ── Config (set these as environment variables on Railway) ──
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
WEBHOOK_SECRET   = os.environ.get("WEBHOOK_SECRET", "")   # optional security key


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
    if not resp.ok:
        print(f"Telegram error: {resp.text}")
    return resp.ok


def build_signal_card(d: dict) -> str:
    """Build the full signal card from parsed webhook JSON."""
    side    = d.get("side", "")
    ticker  = d.get("ticker", "???")
    tf      = d.get("tf", "?")
    entry   = float(d.get("entry", 0))
    sl_dist = float(d.get("sl_dist", 0))
    tp_dist = float(d.get("tp_dist", 0))
    lots    = float(d.get("lots", 0))
    risk    = float(d.get("risk_usd", 0))
    adx     = float(d.get("adx", 0))
    knn     = int(float(d.get("knn", 0)))

    # Calculate absolute SL and TP prices
    if side == "LONG":
        sl_price = entry - sl_dist
        tp_price = entry + tp_dist
        emoji    = "🟢"
        arrow    = "LONG"
    elif side == "SHORT":
        sl_price = entry + sl_dist
        tp_price = entry - tp_dist
        emoji    = "🔴"
        arrow    = "SHORT"
    elif side in ("CLOSE_LONG", "CLOSE_SHORT"):
        direction = "LONG" if side == "CLOSE_LONG" else "SHORT"
        return (
            f"⚠️ *CLOSE SIGNAL*\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"Asset:  `{ticker}`\n"
            f"TF:     `{tf}m`\n"
            f"Action: Close {direction} position\n"
            f"Price:  `{entry:.4f}`\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"_EMA cross or RSI extreme detected_"
        )
    else:
        return f"Unknown signal: {d}"

    # Round entry/SL/TP sensibly based on price magnitude
    decimals = 2 if entry > 100 else (4 if entry > 1 else 6)
    fmt = f"{{:.{decimals}f}}"

    rr = round(tp_dist / sl_dist, 2) if sl_dist > 0 else 0

    card = (
        f"{emoji} *{arrow} SIGNAL*\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"Asset:    `{ticker}`\n"
        f"TF:       `{tf}m`\n"
        f"Entry:    `{fmt.format(entry)}`\n"
        f"SL:       `{fmt.format(sl_price)}`\n"
        f"TP:       `{fmt.format(tp_price)}`\n"
        f"Lots:     `{lots}`\n"
        f"Risk $:   `${risk:.2f}`\n"
        f"R:R:      `1 : {rr}`\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"ADX:      `{adx:.1f}`\n"
        f"KNN Vote: `{knn}`\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"_Enter manually on Breakout terminal_"
    )
    return card


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if not data:
        return jsonify({"error": "No JSON received"}), 400
    
    # Check for secret inside the JSON message instead of headers
    received_secret = data.get("secret", "")
    if received_secret != WEBHOOK_SECRET:
        print(f"Unauthorized access attempt with secret: {received_secret}")
        return jsonify({"error": "unauthorized"}), 401

    print(f"Received valid signal for: {data.get('ticker')}")

    # Build and send the card
    try:
        card = build_signal_card(data)
        ok = send_telegram(card)
        return jsonify({"ok": ok}), 200 if ok else 500
    except Exception as e:
        print(f"Error processing signal: {e}")
        return jsonify({"error": str(e)}), 400


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "bot": "Breakout Signal Bot"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
