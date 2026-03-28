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
    # Simplified card builder to ensure it never crashes
    ticker = d.get("ticker", "UNKNOWN")
    side = d.get("side", "SIGNAL")
    entry = d.get("entry", 0)
    return f"🚀 *{side}* on `{ticker}`\nPrice: `{entry}`\n_Sent from Railway_"

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
