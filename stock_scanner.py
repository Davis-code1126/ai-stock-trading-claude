import yfinance as yf
from strategy import generate_signal
from analyzer import get_stock_data, calculate_rsi

WATCHLIST = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA",
    "AMD", "AVGO", "NFLX", "CRM", "INTC", "PLTR", "MU"
]

def scan_watchlist():
    """Scan all watchlist stocks and return candidates worth analyzing"""
    print("\n=== Stock Scanner ===\n")

    candidates = []
    skipped = []

    for symbol in WATCHLIST:
        try:
            stock_data = get_stock_data(symbol)
            signal_data = generate_signal(stock_data)

            result = {
                "symbol": symbol,
                "price": stock_data["current_price"],
                "change_pct": stock_data["change_pct"],
                "rsi": stock_data["rsi"],
                "rule_signal": signal_data["signal"],
                "rule_score": signal_data["score"],
            }

            if signal_data["signal"] in ["BUY", "WATCHLIST_BUY"]:
                candidates.append(result)
                print(f"  [{signal_data['signal']}] {symbol} @ ${stock_data['current_price']} | RSI={stock_data['rsi']} | Score={signal_data['score']}")
            else:
                skipped.append(symbol)

        except Exception as e:
            print(f"  [ERROR] {symbol}: {str(e)}")

    print(f"\nSkipped (HOLD): {', '.join(skipped)}")
    print(f"\nCandidates found: {len(candidates)}")

    # Sort by score, highest first
    candidates.sort(key=lambda x: x["rule_score"], reverse=True)
    return candidates


if __name__ == "__main__":
    results = scan_watchlist()

    if results:
        print("\n=== Top Candidates ===")
        for r in results:
            print(f"{r['symbol']}: ${r['price']} | {r['change_pct']}% | RSI={r['rsi']} | Signal={r['rule_signal']} | Score={r['rule_score']}")