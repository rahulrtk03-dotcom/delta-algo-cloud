import os
import requests
from datetime import datetime
from delta_rest_client import DeltaRestClient, OrderType

# ----------------- DELTA CLIENT -----------------

delta_client = DeltaRestClient(
    base_url=os.environ.get("DELTA_BASE_URL"),   # testnet OR mainnet
    api_key=os.environ.get("DELTA_API_KEY"),
    api_secret=os.environ.get("DELTA_API_SECRET")
)

# ----------------- TELEGRAM -----------------

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=5)
    except:
        pass

# ----------------- CONFIG -----------------

SYMBOL_KEYWORD = "BTC"
ORDER_SIZE = float(os.environ.get("ORDER_SIZE", "0.001"))  # SAFE SIZE
PRODUCT_ID = None

# ----------------- POSITION STATE -----------------

current_position = None
entry_price = None
entry_time = None
entry_side = None

# ----------------- PRODUCT DETECTION -----------------

def detect_product():
    global PRODUCT_ID

    products = delta_client.get_products()
    for p in products.get("result", []):
        if SYMBOL_KEYWORD in p.get("symbol", "") and p.get("contract_type") == "perpetual_futures":
            PRODUCT_ID = p["id"]
            send_telegram(f"✅ PRODUCT DETECTED\n{p['symbol']} | ID: {PRODUCT_ID}")
            return

    raise Exception("❌ BTC FUTURES PRODUCT NOT FOUND")

# ----------------- SAFE ORDER -----------------

def place_market_order(side):
    resp = delta_client.place_order(
        product_id=PRODUCT_ID,
        size=ORDER_SIZE,
        side=side,
        order_type=OrderType.MARKET
    )

    print("DELTA RESPONSE =>", resp, flush=True)

    if not resp or resp.get("success") is False:
        error = resp.get("error", "Unknown error")
        send_telegram(f"❌ ORDER FAILED\n{error}")
        return None

    return resp

# ----------------- PRICE -----------------

def get_ltp():
    try:
        ticker = delta_client.get_ticker(PRODUCT_ID)
        return float(ticker["result"]["last_price"])
    except:
        return 0.0

# ----------------- TRADING LOGIC -----------------

def buy():
    global current_position, entry_price, entry_time, entry_side

    if current_position == "LONG":
        return

    if current_position == "SHORT":
        close_position()

    resp = place_market_order("buy")
    if not resp:
        return

    entry_price = get_ltp()
    entry_time = datetime.utcnow()
    entry_side = "BUY"
    current_position = "LONG"

    send_telegram(f"🟢 BUY EXECUTED\nPrice: {entry_price}\nQty: {ORDER_SIZE}")


def sell():
    global current_position, entry_price, entry_time, entry_side

    if current_position == "SHORT":
        return

    if current_position == "LONG":
        close_position()

    resp = place_market_order("sell")
    if not resp:
        return

    entry_price = get_ltp()
    entry_time = datetime.utcnow()
    entry_side = "SELL"
    current_position = "SHORT"

    send_telegram(f"🔴 SELL EXECUTED\nPrice: {entry_price}\nQty: {ORDER_SIZE}")


def close_position():
    global current_position, entry_price, entry_time, entry_side

    side = "sell" if current_position == "LONG" else "buy"
    resp = place_market_order(side)
    if not resp:
        return

    exit_price = get_ltp()
    pnl = (
        (exit_price - entry_price)
        if entry_side == "BUY"
        else (entry_price - exit_price)
    ) * ORDER_SIZE

    send_telegram(
        f"⚠️ POSITION CLOSED\n"
        f"Exit Price: {exit_price}\n"
        f"PnL: {round(pnl, 4)}"
    )

    current_position = None
    entry_price = None
    entry_time = None
    entry_side = None

# ----------------- SIGNAL HANDLER -----------------

def handle_signal(signal):
    signal = signal.upper()
    if "BUY" in signal:
        buy()
    elif "SELL" in signal:
        sell()

# ----------------- STARTUP -----------------

detect_product()

send_telegram(
    "⚠️ BOT STARTED\n"
    "Delta product detected\n"
    "Manual position check recommended"
)

