import json
import yfinance as yf
from datetime import datetime
import os
from config import (
    TOTAL_CAPITAL,
    MAX_POSITION_SIZE,
    STOP_LOSS_PCT,
    TAKE_PROFIT_PCT,
    MAX_HOLD_DAYS
)

PORTFOLIO_FILE = "portfolio.json"


def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass

    return {
        "capital": TOTAL_CAPITAL,
        "positions": [],
        "history": []
    }


def save_portfolio(portfolio):
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, indent=2, ensure_ascii=False)


def get_position(symbol):
    portfolio = load_portfolio()
    for p in portfolio["positions"]:
        if p["symbol"] == symbol:
            return p
    return None


def has_position(symbol):
    return get_position(symbol) is not None


def days_between(date_str1, date_str2):
    d1 = datetime.strptime(date_str1, "%Y-%m-%d")
    d2 = datetime.strptime(date_str2, "%Y-%m-%d")
    return (d2 - d1).days


def add_position(symbol, action, price, amount=MAX_POSITION_SIZE, reason=""):
    portfolio = load_portfolio()

    if action == "BUY":
        existing = next((p for p in portfolio["positions"] if p["symbol"] == symbol), None)
        if existing:
            print(f"  [ALREADY HELD] {symbol} — skipping duplicate buy")
            return

        remaining = portfolio["capital"]
        if remaining < amount:
            print(f"  [INSUFFICIENT FUNDS] Remaining ${remaining}, cannot buy {symbol} (requires ${amount})")
            return

        shares = round(amount / price, 4)
        position = {
            "symbol": symbol,
            "buy_date": datetime.now().strftime("%Y-%m-%d"),
            "buy_price": price,
            "shares": shares,
            "amount_invested": amount,
            "entry_reason": reason
        }

        portfolio["positions"].append(position)
        portfolio["capital"] = round(remaining - amount, 2)

        print(f"  [SIMULATED BUY] {symbol} x{shares} @ ${price} = ${amount} | Remaining capital: ${portfolio['capital']}")

    elif action == "SELL":
        existing = next((p for p in portfolio["positions"] if p["symbol"] == symbol), None)
        if not existing:
            print(f"  [NO POSITION] {symbol} — no position to sell")
            return

        profit = round((price - existing["buy_price"]) * existing["shares"], 2)
        profit_pct = round((price - existing["buy_price"]) / existing["buy_price"] * 100, 2)

        record = {
            "symbol": symbol,
            "buy_date": existing["buy_date"],
            "sell_date": datetime.now().strftime("%Y-%m-%d"),
            "buy_price": existing["buy_price"],
            "sell_price": price,
            "shares": existing["shares"],
            "amount_invested": existing["amount_invested"],
            "profit": profit,
            "profit_pct": profit_pct,
            "entry_reason": existing.get("entry_reason", ""),
            "exit_reason": reason
        }

        portfolio["history"].append(record)
        portfolio["capital"] = round(portfolio["capital"] + existing["amount_invested"] + profit, 2)
        portfolio["positions"].remove(existing)

        print(f"  [SIMULATED SELL] {symbol} P&L: ${profit} ({profit_pct}%) | Remaining capital: ${portfolio['capital']}")
        if reason:
            print(f"  [EXIT REASON] {reason}")

    save_portfolio(portfolio)


def check_risk_rules(symbol, current_price):
    """
    Check whether a held position has triggered any risk management rules.
    Returns:
        {
            "triggered": bool,
            "action": "SELL" or "HOLD",
            "reason": str
        }
    """
    position = get_position(symbol)
    if not position:
        return {
            "triggered": False,
            "action": "HOLD",
            "reason": "No open position."
        }

    buy_price = position["buy_price"]
    pnl_pct = (current_price - buy_price) / buy_price
    hold_days = days_between(position["buy_date"], datetime.now().strftime("%Y-%m-%d"))

    if pnl_pct <= -STOP_LOSS_PCT:
        return {
            "triggered": True,
            "action": "SELL",
            "reason": f"Stop loss triggered: return {round(pnl_pct * 100, 2)}%"
        }

    if pnl_pct >= TAKE_PROFIT_PCT:
        return {
            "triggered": True,
            "action": "SELL",
            "reason": f"Take profit triggered: return {round(pnl_pct * 100, 2)}%"
        }

    if hold_days >= MAX_HOLD_DAYS:
        return {
            "triggered": True,
            "action": "SELL",
            "reason": f"Max hold days reached: {hold_days} days"
        }

    return {
        "triggered": False,
        "action": "HOLD",
        "reason": "No risk rule triggered."
    }


def get_current_price(symbol):
    stock = yf.Ticker(symbol)
    hist = stock.history(period="1d")
    if hist.empty:
        raise ValueError(f"Could not fetch current price for {symbol}")
    return round(hist["Close"].iloc[-1], 2)


def show_portfolio_summary():
    portfolio = load_portfolio()
    positions = portfolio["positions"]
    history = portfolio["history"]

    print("\n===== Simulated Account =====")
    print(f"Available capital: ${portfolio['capital']} / Total capital: ${TOTAL_CAPITAL}")

    print("\n----- Current Positions -----")
    if not positions:
        print("No open positions")

    total_value = 0
    total_cost = 0

    for p in positions:
        try:
            current_price = get_current_price(p["symbol"])
            current_value = round(current_price * p["shares"], 2)
            profit = round(current_value - p["amount_invested"], 2)
            profit_pct = round(profit / p["amount_invested"] * 100, 2)
            hold_days = days_between(p["buy_date"], datetime.now().strftime("%Y-%m-%d"))

            total_value += current_value
            total_cost += p["amount_invested"]

            print(
                f"{p['symbol']}: Invested ${p['amount_invested']} → Current value ${current_value} | "
                f"P&L ${profit} ({profit_pct}%) | Held since {p['buy_date']} | Days held: {hold_days}"
            )
        except Exception as e:
            print(f"{p['symbol']}: Failed to fetch current price ({e})")

    if positions:
        total_profit = round(total_value - total_cost, 2)
        total_pct = round(total_profit / total_cost * 100, 2)
        print(f"\nTotal invested: ${total_cost} | Total value: ${total_value} | Total P&L: ${total_profit} ({total_pct}%)")

    total_assets = round(portfolio["capital"] + total_value, 2)
    total_return = round(total_assets - TOTAL_CAPITAL, 2)
    total_return_pct = round(total_return / TOTAL_CAPITAL * 100, 2)
    print(f"\nTotal assets: ${total_assets} | Total return: ${total_return} ({total_return_pct}%)")

    print("\n----- Trade History -----")
    if not history:
        print("No completed trades")

    for h in history:
        print(
            f"{h['symbol']}: Bought {h['buy_date']} → Sold {h['sell_date']} | "
            f"P&L ${h['profit']} ({h['profit_pct']}%) | Exit reason: {h.get('exit_reason', '')}"
        )

    if history:
        total_realized = round(sum(h["profit"] for h in history), 2)
        print(f"Total realized P&L: ${total_realized}")


if __name__ == "__main__":
    show_portfolio_summary()