import os
import requests
from datetime import datetime, timedelta
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
ORDER_SIZE = 10
SYMBOL = "BTCUSD"

# ----------------- POSITION STATE -----------------

current_position = None     # None | LONG | SHORT
entry_price = None
entry_time = None
entry_side = None
entry_order_id = None

# ----------------- NEW HELPERS -----------------

def get_ltp():
    try:
        ticker = delta_client.get_ticker(PRODUCT_ID)
        return float(ticker["result"]["last_price"])
    except Exception:
        return 0.0


def sync_position_on_startup():
    """
    NEW FEATURE:
    Restart ke baad exchange se open position sync
    """
    global current_position, entry_price, entry_time, entry_side

    try:
        positions = delta_client.get_positions()
        if not positions or "result" not in positions:
            return

        for pos in positions["result"]:
            if pos.get("product_id") != PRODUCT_ID:
                continue

            size = float(pos.get("size", 0))
            if size == 0:
                continue

            side = pos.get("side")  # buy / sell
            entry_price = float(pos.get("entry_price", 0))
            entry_time = datetime.utcnow() - timedelta(minutes=1)

            if side == "buy":
                current_position = "LONG"
                entry_side = "BUY"
            else:
                current_position = "SHORT"
                entry_side = "SELL"

            send_telegram(
                "🔄 POSITION SYNCED AFTER RESTART\n"
                f"Symbol: {SYMBOL}\n"
                f"Side: {current_position}\n"
                f"Entry Price: {entry_price}\n"
                f"Qty: {size}"
            )

            print("✅ POSITION SYNCED FROM DELTA", flush=True)
            break

    except Exception as e:
        print("❌ POSITION SYNC FAILED:", e, flush=True)

# ----------------- EXIT WITH SUMMARY -----------------

def close_position_with_summary():
    global current_position, entry_price, entry_time, entry_side

    if current_position is None:
        return

    exit_side = "sell" if current_position == "LONG" else "buy"
    print("⚠️ CLOSING POSITION WITH SUMMARY", flush=True)

    delta_client.place_order(
        product_id=PRODUCT_ID,
        size=ORDER_SIZE,
        side=exit_side,
        order_type=OrderType.MARKET
    )

    exit_price = get_ltp()
    exit_time = datetime.utcnow()

    if entry_side == "BUY":
        pnl = (exit_price - entry_price) * ORDER_SIZE
    else:
        pnl = (entry_price - exit_price) * ORDER_SIZE

    duration = exit_time - entry_time

    send_telegram(
        "⚠️ POSITION CLOSED\n"
        f"Symbol: {SYMBOL}\n"
        f"Exit Price: {exit_price}\n"
        f"PnL: {round(pnl, 2)}\n"
        f"Holding Time: {duration}"
    )

    current_position = None
    entry_price = None
    entry_time = None
    entry_side = None

# ----------------- ORIGINAL BUY / SELL -----------------

def buy():
    global current_position, entry_price, entry_time, entry_side, entry_order_id

    print("🟢 BUY FUNCTION CALLED", flush=True)

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
    entry_price = float(result.get("avg_fill_price") or get_ltp())
    entry_order_id = result.get("id", "NA")
    entry_time = datetime.utcnow()
    entry_side = "BUY"
    current_position = "LONG"

    send_telegram(
        "🟢 BUY EXECUTED\n"
        f"Symbol: {SYMBOL}\n"
        f"Price: {entry_price}\n"
        f"Qty: {ORDER_SIZE}\n"
        f"Time (UTC): {entry_time.strftime('%Y-%m-%d %H:%M:%S')}"
    )


def sell():
    global current_position, entry_price, entry_time, entry_side, entry_order_id

    print("🔴 SELL FUNCTION CALLED", flush=True)

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
    entry_price = float(result.get("avg_fill_price") or get_ltp())
    entry_order_id = result.get("id", "NA")
    entry_time = datetime.utcnow()
    entry_side = "SELL"
    current_position = "SHORT"

    send_telegram(
        "🔴 SELL EXECUTED\n"
        f"Symbol: {SYMBOL}\n"
        f"Price: {entry_price}\n"
        f"Qty: {ORDER_SIZE}\n"
        f"Time (UTC): {entry_time.strftime('%Y-%m-%d %H:%M:%S')}"
    )

# ----------------- SIGNAL HANDLER -----------------

def handle_signal(signal):
    signal = signal.upper()
    print(f"📩 SIGNAL RECEIVED: {signal}", flush=True)

    if "BUY" in signal:
        buy()
    elif "SELL" in signal:
        sell()

# 🔥 AUTO SYNC ON IMPORT / STARTUP
sync_position_on_startup()

