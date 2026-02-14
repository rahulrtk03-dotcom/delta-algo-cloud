import os
from delta_rest_client import DeltaRestClient, OrderType

# ----------------- DELTA CLIENT -----------------

delta_client = DeltaRestClient(
    base_url=os.environ.get("DELTA_BASE_URL"),
    api_key=os.environ.get("DELTA_API_KEY"),
    api_secret=os.environ.get("DELTA_API_SECRET")
)

# ----------------- CONFIG -----------------

PRODUCT_ID = 84
ORDER_SIZE = 1

# Position state (VERY IMPORTANT)
current_position = None  # None | "LONG" | "SHORT"

# ----------------- FUNCTIONS -----------------

def buy():
    global current_position

    print("🟢 BUY FUNCTION CALLED")

    if current_position == "LONG":
        print("🟢 Already in BUY position")
        return

    if current_position == "SHORT":
        close_position()

    try:
        print("🟢 PLACING BUY ORDER")
        delta_client.place_order(
            product_id=PRODUCT_ID,
            size=ORDER_SIZE,
            side='buy',
            order_type=OrderType.MARKET
        )

        current_position = "LONG"
        print("✅ BUY ORDER SUCCESS")

    except Exception as e:
        print("❌ BUY ORDER FAILED:", e)


def sell():
    global current_position

    print("🔴 SELL FUNCTION CALLED")

    if current_position == "SHORT":
        print("🔴 Already in SELL position")
        return

    if current_position == "LONG":
        close_position()

    try:
        print("🔴 PLACING SELL ORDER")
        delta_client.place_order(
            product_id=PRODUCT_ID,
            size=ORDER_SIZE,
            side='sell',
            order_type=OrderType.MARKET
        )

        current_position = "SHORT"
        print("✅ SELL ORDER SUCCESS")

    except Exception as e:
        print("❌ SELL ORDER FAILED:", e)


def close_position():
    global current_position

    if current_position is None:
        return

    side = 'sell' if current_position == "LONG" else 'buy'
    print("⚠️ CLOSING POSITION")

    try:
        delta_client.place_order(
            product_id=PRODUCT_ID,
            size=ORDER_SIZE,
            side=side,
            order_type=OrderType.MARKET
        )

        current_position = None
        print("✅ POSITION CLOSED")

    except Exception as e:
        print("❌ CLOSE POSITION FAILED:", e)

# ----------------- SIGNAL HANDLER -----------------

def handle_signal(signal):
    signal = signal.upper()
    print(f"📩 SIGNAL RECEIVED: {signal}")

    if "BUY" in signal:
        buy()

    elif "SELL" in signal:
        sell()

    else:
        print("⚠️ UNKNOWN SIGNAL")

