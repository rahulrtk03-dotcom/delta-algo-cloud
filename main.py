import os
import json
import time
import requests
from datetime import datetime
from threading import Lock
from delta_rest_client import DeltaRestClient, OrderType

STATE_FILE = "state.json"

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
SYMBOL = "BTCUSD"

# ----------------- GLOBAL SAFETY -----------------

signal_lock = Lock()
last_signal_time = 0
COOLDOWN_SECONDS = 2    # 🔥 1S TF ke liye safe (5m TF me negligible)

last_known_ltp = None

# ----------------- POSITION STATE -----------------

current_position = None     # None | LONG | SHORT
entry_price = None
entry_time = None
entry_side = None
entry_order_id = None

# ----------------- STATE FILE -----------------

def save_state():
    data = {
        "current_position": current_position,
        "entry_price": entry_price,
        "entry_time": entry_time.isoformat() if entry_time else None,
        "entry_side": entry_side,
        "entry_order_id": entry_order_id
    }
    with open(STATE_FILE, "w") as f:
        json.dump(data, f)

def load_state():
    global current_position, entry_price, entry_time, entry_side, entry_order_id

    if not os.path.exists(STATE_FILE):
        return

    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)

        current_position = data.get("current_position")
        entry_price = data.get("entry_price")
        entry_side = data.get("entry_side")
        entry_order_id = data.get("entry_order_id")

        et = data.get("entry_time")
        entry_time = datetime.fromisoformat(et) if et else None

        print("✅ STATE LOADED:", current_position, flush=True)

    except Exception as e:
        print("❌ STATE LOAD FAILED:", e, flush=True)

# ----------------- SAFE LTP -----------------

def get_ltp(retry=5, delay=1):
    global last_known_ltp

    for _ in range(retry):
        try:
            ticker = delta_client.get_ticker(PRODUCT_ID)
            price = float(ticker["result"]["last_price"])
            if price > 0:
                last_known_ltp = price
                return price
        except Exception:
            pass
        time.sleep(delay)

    if last_known_ltp:
        return last_known_ltp

    return entry_price if entry_price else 0.0

# ----------------- EXIT -----------------

def close_position_with_summary():
    global current_position, entry_price, entry_time, entry_side, entry_order_id

    if current_position is None:
        return

    exit_side = "sell" if current_position == "LONG" else "buy"

    delta_client.place_order(
        product_id=PRODUCT_ID,
        size=ORDER_SIZE,
        side=exit_side,
        order_type=OrderType.MARKET
    )

    exit_price = get_ltp()
    exit_time = datetime.utcnow()

    pnl = (
        (exit_price - entry_price) * ORDER_SIZE
        if entry_side == "BUY"
        else (entry_price - exit_price) * ORDER_SIZE
    )

    send_telegram(
        "⚠️ POSITION CLOSED\n"
        f"Symbol: {SYMBOL}\n"
        f"Side: {entry_side}\n"
        f"Entry: {entry_price}\n"
        f"Exit: {exit_price}\n"
        f"PnL: {round(pnl, 2)}\n"
        f"Time Held: {exit_time - entry_time}"
    )

    current_position = None
    entry_price = None
    entry_time = None
    entry_side = None
    entry_order_id = None
    save_state()

# ----------------- BUY -----------------

def buy():
    global current_position, entry_price, entry_time, entry_side, entry_order_id

    if current_position == "LONG":
        return

    if current_position == "SHORT":
        close_position_with_summary()

    resp = delta_client.place_order(
        product_id=PRODUCT_ID,
        size=ORDER_SIZE,
        side="buy",
        order_type=OrderType.MARKET
    )

    result = resp.get("result", {})
    entry_price = float(result.get("avg_fill_price") or 0)

    if entry_price <= 0:
        time.sleep(1)
        entry_price = get_ltp()

    entry_time = datetime.utcnow()
    entry_side = "BUY"
    entry_order_id = result.get("id", "NA")
    current_position = "LONG"

    save_state()

    send_telegram(
        "🟢 BUY EXECUTED\n"
        f"{SYMBOL}\nPrice: {entry_price}\nQty: {ORDER_SIZE}"
    )

# ----------------- SELL -----------------

def sell():
    global current_position, entry_price, entry_time, entry_side, entry_order_id

    if current_position == "SHORT":
        return

    if current_position == "LONG":
        close_position_with_summary()

    resp = delta_client.place_order(
        product_id=PRODUCT_ID,
        size=ORDER_SIZE,
        side="sell",
        order_type=OrderType.MARKET
    )

    result = resp.get("result", {})
    entry_price = float(result.get("avg_fill_price") or 0)

    if entry_price <= 0:
        time.sleep(1)
        entry_price = get_ltp()

    entry_time = datetime.utcnow()
    entry_side = "SELL"
    entry_order_id = result.get("id", "NA")
    current_position = "SHORT"

    save_state()

    send_telegram(
        "🔴 SELL EXECUTED\n"
        f"{SYMBOL}\nPrice: {entry_price}\nQty: {ORDER_SIZE}"
    )

# ----------------- SIGNAL HANDLER (CRASH PROOF) -----------------

def handle_signal(signal):
    global last_signal_time

    now = time.time()
    signal = signal.upper()

    if not signal_lock.acquire(blocking=False):
        print("⏳ Busy, signal skipped", flush=True)
        return

    try:
        if now - last_signal_time < COOLDOWN_SECONDS:
            print("⏱️ Cooldown skip", flush=True)
            return

        print(f"📩 SIGNAL RECEIVED: {signal}", flush=True)

        if "BUY" in signal and current_position == "LONG":
            return
        if "SELL" in signal and current_position == "SHORT":
            return

        if "BUY" in signal:
            buy()
        elif "SELL" in signal:
            sell()

        last_signal_time = now

    finally:
        signal_lock.release()

# ----------------- STARTUP -----------------

load_state()

