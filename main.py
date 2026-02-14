import os
import requests
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
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg
        }
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print("❌ Telegram error:", e, flush=True)

# ----------------- CONFIG -----------------

PRODUCT_ID = 84
ORDER_SIZE = 1

# Position state (VERY IMPORTANT)
current_position = None  # None | "LONG" | "SHORT"

# ----------------- FUNCTIONS -----------------

def buy():
    global current_position

    print("🟢 BUY FUNCTION CALLED", flush=True)

    if current_position == "LONG":
        print("🟢 Already in BUY position", flush=True)
        return

    if current_position == "SHORT":
        close_position()

    try:
        print("🟢 PLACING BUY ORDER", flush=True)
        delta_client.place_order(
            product_id=PRODUCT_ID,
            size=ORDER_SIZE,
            side='buy',
            order_type=OrderType.MARKET
        )

        current_position = "LONG"
        print("✅ BUY ORDER SUCCESS", flush=True)

        send_telegram(
            f"🟢 BUY ORDER SUCCESS\n"
            f"Product ID: {PRODUCT_ID}\n"
            f"Qty: {ORDER_SIZE}"
        )

    except Exception as e:
        print("❌ BUY ORDER FAILED:", e, flush=True)
        send_telegram(f"❌ BUY ORDER FAILED\nError: {e}")


def sell():
    global current_position

    print("🔴 SELL FUNCTION CALLED", flush=True)

    if current_position == "SHORT":
        print("🔴 Already in SELL position", flush=True)
        return

    if current_position == "LONG":
        close_position()

    try:
        print("🔴 PLACING SELL ORDER", flush=True)
        delta_client.place_order(
            product_id=PRODUCT_ID,
            size=ORDER_SIZE,
            side='sell',
            order_type=OrderType.MARKET
        )

        current_position = "SHORT"
        print("✅ SELL ORDER SUCCESS", flush=True)

        send_telegram(
            f"🔴 SELL ORDER SUCCESS\n"
            f"Product ID: {PRODUCT_ID}\n"
            f"Qty: {ORDER_SIZE}"
        )

    except Exception as e:
        print("❌ SELL ORDER FAILED:", e, flush=True)
        send_telegram(f"❌ SELL ORDER FAILED\nError: {e}")


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
        print("✅ POSITION CLOSED", flush=True)

        send_telegram("⚠️ POSITION CLOSED")

    except Exception as e:
        print("❌ CLOSE POSITION FAILED:", e, flush=True)
        send_telegram(f"❌ CLOSE POSITION FAILED\nError: {e}")

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
