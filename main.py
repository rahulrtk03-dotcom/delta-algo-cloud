import os
import requests
from datetime import datetime
from delta_rest_client import DeltaRestClient, OrderType

# ----------------- DELTA CLIENT -----------------

delta_client = DeltaRestClient(
    base_url=os.environ.get("DELTA_BASE_URL"),
    api_key=os.environ.get("DELTA_API_KEY"),
    api_secret=os.environ.get("DELTA_API_SECRET")
)

# ----------------- TELEGRAM CONFIG -----------------

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print("❌ Telegram error:", e, flush=True)

# ----------------- CONFIG -----------------

PRODUCT_ID = 84
ORDER_SIZE = 1
SYMBOL = "BTCUSD"   # 👉 future me dynamic bana sakte ho

# Position state
current_position = None  # None | "LONG" | "SHORT"

# 🔥 NEW TRADE STATE (FEATURE ADDITION)
entry_price = None
entry_time = None
entry_side = None
entry_order_id = None

# ----------------- FUNCTIONS -----------------

def buy():
    global current_position, entry_price, entry_time, entry_side, entry_order_id

    print("🟢 BUY FUNCTION CALLED", flush=True)

    if current_position == "LONG":
        return

    if current_position == "SHORT":
        close_position()

    try:
        print("🟢 PLACING BUY ORDER", flush=True)
        resp = delta_client.place_order(
            product_id=PRODUCT_ID,
            size=ORDER_SIZE,
            side='buy',
            order_type=OrderType.MARKET
        )

        result = resp.get("result", {})
        entry_price = float(result.get("avg_fill_price", 0))
        entry_order_id = result.get("id", "NA")
        entry_time = datetime.utcnow()
        entry_side = "BUY"

        current_position = "LONG"

        msg = (
            "🟢 BUY EXECUTED\n"
            f"Symbol: {SYMBOL}\n"
            f"Price: {entry_price}\n"
            f"Qty: {ORDER_SIZE}\n"
            f"Order ID: {entry_order_id}\n"
            f"Time (UTC): {entry_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        print(msg, flush=True)
        send_telegram(msg)

    except Exception as e:
        send_telegram(f"❌ BUY FAILED\n{e}")


def sell():
    global current_position, entry_price, entry_time, entry_side, entry_order_id

    print("🔴 SELL FUNCTION CALLED", flush=True)

    if current_position == "SHORT":
        return

    if current_position == "LONG":
        close_position()

    try:
        print("🔴 PLACING SELL ORDER", flush=True)
        resp = delta_client.place_order(
            product_id=PRODUCT_ID,
            size=ORDER_SIZE,
            side='sell',
            order_type=OrderType.MARKET
        )

        result = resp.get("result", {})
        exit_price = float(result.get("avg_fill_price", 0))
        exit_order_id = result.get("id", "NA")
        exit_time = datetime.utcnow()

        # 📊 PnL calculation (previous trade)
        pnl = 0
        if entry_side == "BUY":
            pnl = (exit_price - entry_price) * ORDER_SIZE

        duration = exit_time - entry_time

        msg = (
            "🔴 SELL EXECUTED\n"
            f"Symbol: {SYMBOL}\n"
            f"Exit Price: {exit_price}\n"
            f"Qty: {ORDER_SIZE}\n"
            f"Order ID: {exit_order_id}\n\n"
            "📊 TRADE SUMMARY\n"
            f"Entry Price: {entry_price}\n"
            f"PnL: {round(pnl, 2)}\n"
            f"Duration: {duration}"
        )

        print(msg, flush=True)
        send_telegram(msg)

        # reset state
        current_position = "SHORT"
        entry_price = exit_price
        entry_time = exit_time
        entry_side = "SELL"
        entry_order_id = exit_order_id

    except Exception as e:
        send_telegram(f"❌ SELL FAILED\n{e}")


def close_position():
    global current_position

    if current_position is None:
        return

    side = 'sell' if current_position == "LONG" else 'buy'
    print("⚠️ CLOSING POSITION", flush=True)

    try:
        delta_client.place_order(
            product_id=PRODUCT_ID,
            size=ORDER_SIZE,
            side=side,
            order_type=OrderType.MARKET
        )

        current_position = None
        send_telegram("⚠️ POSITION CLOSED")

    except Exception as e:
        send_telegram(f"❌ CLOSE POSITION FAILED\n{e}")

# ----------------- SIGNAL HANDLER -----------------

def handle_signal(signal):
    signal = signal.upper()
    print(f"📩 SIGNAL RECEIVED: {signal}", flush=True)

    if "BUY" in signal:
        buy()

    elif "SELL" in signal:
        sell()

    else:
        print("⚠️ UNKNOWN SIGNAL", flush=True)

