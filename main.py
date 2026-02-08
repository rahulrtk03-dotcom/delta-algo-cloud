import os
from delta_rest_client import DeltaRestClient, OrderType

delta_client = DeltaRestClient(
    base_url=os.environ.get("DELTA_BASE_URL"),
    api_key=os.environ.get("DELTA_API_KEY"),
    api_secret=os.environ.get("DELTA_API_SECRET")
)



PRODUCT_ID = 84
ORDER_SIZE = 1

# Position state (VERY IMPORTANT)
current_position = None  # None | "LONG" | "SHORT"


# ----------------- FUNCTIONS -----------------

def buy():
    global current_position

    if current_position == "LONG":
        print("🟢 Already in BUY position")
        return

    if current_position == "SHORT":
        close_position()

    print("🟢 PLACING BUY ORDER")
    delta_client.place_order(
        product_id=PRODUCT_ID,
        size=ORDER_SIZE,
        side='buy',
        order_type=OrderType.MARKET
    )

    current_position = "LONG"


def sell():
    global current_position

    if current_position == "SHORT":
        print("🔴 Already in SELL position")
        return

    if current_position == "LONG":
        close_position()

    print("🔴 PLACING SELL ORDER")
    delta_client.place_order(
        product_id=PRODUCT_ID,
        size=ORDER_SIZE,
        side='sell',
        order_type=OrderType.MARKET
    )

    current_position = "SHORT"


def close_position():
    global current_position

    if current_position is None:
        return

    side = 'sell' if current_position == "LONG" else 'buy'
    print("⚠️ CLOSING POSITION")

    delta_client.place_order(
        product_id=PRODUCT_ID,
        size=ORDER_SIZE,
        side=side,
        order_type=OrderType.MARKET
    )

    current_position = None


# ----------------- SIGNAL HANDLER -----------------

def handle_signal(signal):
    signal = signal.upper()
    print(f"📩 SIGNAL RECEIVED: {signal}")

    if "BUY" in signal:
        buy()

    elif "SELL" in signal:
        sell()

