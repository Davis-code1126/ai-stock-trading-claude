import json
import os
from datetime import datetime, timedelta
from glob import glob


def load_recent_logs(days=14):
    """Load log entries from the past N days"""
    logs = []
    for i in range(days):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        filename = f"log_{date}.json"
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    entries = json.load(f)
                    logs.extend(entries)
            except:
                continue
    return logs


def analyze_signal_performance(logs):
    """Analyze win rate of various signal combinations"""
    results = {}

    for entry in logs:
        symbol = entry.get("symbol")
        final_action = entry.get("final_action")
        buy_price = entry.get("price")
        date = entry.get("date")

        if final_action != "BUY" or not buy_price:
            continue

        key = f"{symbol}_{date}"
        results[key] = {
            "symbol": symbol,
            "date": date,
            "buy_price": buy_price,
            "rule_signal": entry.get("rule_signal"),
            "ai_signal": entry.get("ai_signal"),
            "ai_confidence": entry.get("ai_confidence"),
            "rule_score": entry.get("rule_score", 0)
        }

    return results


def generate_memory_summary(logs):
    """Generate experience summary to inject into Claude's prompt"""
    if not logs:
        return "No historical data available yet."

    summary_lines = []
    symbol_stats = {}

    for entry in logs:
        symbol = entry.get("symbol")
        if symbol not in symbol_stats:
            symbol_stats[symbol] = {
                "total": 0,
                "buy_count": 0,
                "hold_count": 0,
                "sell_count": 0,
                "high_rsi_held": 0,
                "watchlist_ai_hold": 0,
                "rule_scores": [],
                "recent_actions": []
            }

        stats = symbol_stats[symbol]
        stats["total"] += 1
        final_action = entry.get("final_action") or entry.get("recommendation", "HOLD")
        rule_signal = entry.get("rule_signal", "")
        ai_signal = entry.get("ai_signal") or entry.get("sentiment", "")
        rsi = entry.get("rsi", 0)
        rule_score = entry.get("rule_score", 0)

        if final_action == "BUY":
            stats["buy_count"] += 1
        elif final_action == "SELL":
            stats["sell_count"] += 1
        else:
            stats["hold_count"] += 1

        # Track overbought RSI without a SELL being triggered
        if rsi and rsi > 85 and final_action != "SELL":
            stats["high_rsi_held"] += 1

        # Track WATCHLIST_BUY where AI said HOLD
        if rule_signal == "WATCHLIST_BUY" and ai_signal == "HOLD":
            stats["watchlist_ai_hold"] += 1

        if rule_score:
            stats["rule_scores"].append(rule_score)

        # Keep only the last 3 actions
        stats["recent_actions"].append({
            "date": entry.get("date"),
            "action": final_action,
            "rule": rule_signal,
            "ai": ai_signal,
            "confidence": entry.get("ai_confidence")
        })

    # Generate summary text
    for symbol, stats in symbol_stats.items():
        lines = [f"{symbol} ({stats['total']} analyses):"]

        lines.append(
            f"  - Actions: BUY={stats['buy_count']}, "
            f"HOLD={stats['hold_count']}, SELL={stats['sell_count']}"
        )

        if stats["high_rsi_held"] > 0:
            lines.append(
                f"  - RSI>85 was observed {stats['high_rsi_held']} time(s) "
                f"without triggering SELL — watch for pullback risk"
            )

        if stats["watchlist_ai_hold"] > 1:
            lines.append(
                f"  - WATCHLIST_BUY + AI HOLD occurred "
                f"{stats['watchlist_ai_hold']} times — low conviction setup"
            )

        # Last 3 actions
        recent = stats["recent_actions"][-3:]
        recent_str = ", ".join(
            [f"{r['date']}:{r['action']}(rule={r['rule']},ai={r['ai']})"
             for r in recent]
        )
        lines.append(f"  - Recent: {recent_str}")

        summary_lines.extend(lines)

    return "\n".join(summary_lines)


def get_memory_prompt():
    """Return a memory block ready to inject into the Claude prompt"""
    logs = load_recent_logs(days=14)

    if not logs:
        return ""

    summary = generate_memory_summary(logs)

    return f"""
System Memory (last 14 days of trading history):
{summary}

Use this historical context to improve your analysis. 
If a pattern has repeatedly failed, lower your confidence. 
If a setup has been reliable, you may increase confidence accordingly.
"""


if __name__ == "__main__":
    logs = load_recent_logs(days=14)
    print(f"Loaded {len(logs)} log entries\n")
    print(generate_memory_summary(logs))