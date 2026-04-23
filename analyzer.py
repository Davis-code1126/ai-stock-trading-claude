import anthropic
import yfinance as yf
import requests
import json
from datetime import datetime
from memory import get_memory_prompt
from config import CLAUDE_API_KEY, STOCKS
from portfolio import add_position, show_portfolio_summary, has_position, check_risk_rules
from strategy import generate_signal
from decision_engine import decide_action
from news_service import get_news, format_news_for_claude

client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)


def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def get_stock_data(symbol):
    stock = yf.Ticker(symbol)
    hist = stock.history(period="3mo")

    if hist.empty or len(hist) < 50:
        raise ValueError(f"Not enough historical data for {symbol}")

    close = hist["Close"]
    volume = hist["Volume"]

    current_price = round(close.iloc[-1], 2)
    prev_price = close.iloc[-2]
    change_pct = round((current_price - prev_price) / prev_price * 100, 2)

    ma20 = round(close.rolling(20).mean().iloc[-1], 2)
    ma50 = round(close.rolling(50).mean().iloc[-1], 2)
    avg_volume_20 = int(volume.rolling(20).mean().iloc[-1])
    rsi = round(calculate_rsi(close).iloc[-1], 2)

    return {
        "symbol": symbol,
        "current_price": current_price,
        "change_pct": change_pct,
        "volume": int(volume.iloc[-1]),
        "ma20": ma20,
        "ma50": ma50,
        "avg_volume_20": avg_volume_20,
        "rsi": rsi
    }


def analyze_with_claude(stock_data, news, signal_data):
    memory = get_memory_prompt()
    reasons_text = "\n".join([f"- {r}" for r in signal_data["reasons"]])

    prompt = f"""{memory}
You are an AI stock trading assistant.

A rule-based trading system has already generated this rule signal:

Rule Signal: {signal_data['signal']}
Rule Score: {signal_data['score']}
Rule Reasons:
{reasons_text}

Market data:
Symbol: {stock_data['symbol']}
Current Price: ${stock_data['current_price']}
Today's Change: {stock_data['change_pct']}%
Volume: {stock_data['volume']}
MA20: {stock_data['ma20']}
MA50: {stock_data['ma50']}
20-day Avg Volume: {stock_data['avg_volume_20']}
RSI: {stock_data['rsi']}

Recent News:
{news}

Please evaluate the stock independently and provide:
1. Sentiment (Bullish/Neutral/Bearish)
2. AI Signal (BUY/HOLD/SELL)
3. Confidence (Low/Medium/High)
4. Brief reasoning (2-3 sentences)
5. Main risk (1 sentence)

Important:
- You may disagree with the rule signal if justified.
- Base your answer on the market data and news above.
- Reply with ONLY a JSON object, no markdown, no backticks.
- Base your analysis strictly on the news items provided above.
- Do not introduce facts, events, or claims that are not explicitly mentioned in the news.
- If the news is insufficient, weakly relevant, or mixed, say so clearly and lower your confidence accordingly.
- Do not infer specific executive changes, financial results, or business events unless they are explicitly stated in the provided news items.
- Use system memory only as secondary context.
- Do not let prior summaries outweigh today's market data and current news.

Expected format:
{{"sentiment": "", "ai_signal": "", "confidence": "", "reasoning": "", "risk": ""}}
"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = message.content[0].text.strip()

        if raw.startswith("```"):
            parts = raw.split("```")
            if len(parts) >= 2:
                raw = parts[1]
            if raw.startswith("json"):
                raw = raw[4:]

        raw = raw.strip()
        data = json.loads(raw)

        required_keys = ["sentiment", "ai_signal", "confidence", "reasoning", "risk"]
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Missing key: {key}")

        ai_signal = str(data["ai_signal"]).upper().strip()
        if ai_signal not in ["BUY", "HOLD", "SELL"]:
            ai_signal = "HOLD"

        confidence = str(data["confidence"]).capitalize().strip()
        if confidence not in ["Low", "Medium", "High"]:
            confidence = "Low"

        sentiment = str(data["sentiment"]).capitalize().strip()
        if sentiment not in ["Bullish", "Neutral", "Bearish"]:
            sentiment = "Neutral"

        data["ai_signal"] = ai_signal
        data["confidence"] = confidence
        data["sentiment"] = sentiment

        return data

    except Exception as e:
        return {
            "sentiment": "Neutral",
            "ai_signal": "HOLD",
            "confidence": "Low",
            "reasoning": f"Claude analysis failed or could not be parsed: {str(e)}",
            "risk": "Model output unavailable, so this analysis should not be trusted."
        }


def save_log(symbol, stock_data, signal_data, ai_analysis, decision, risk_check, final_action, decision_reason):
    today = datetime.now().strftime("%Y-%m-%d")

    log_entry = {
        "date": today,
        "symbol": symbol,
        "price": stock_data["current_price"],
        "change_pct": stock_data["change_pct"],
        "volume": stock_data["volume"],
        "ma20": stock_data["ma20"],
        "ma50": stock_data["ma50"],
        "avg_volume_20": stock_data["avg_volume_20"],
        "rsi": stock_data["rsi"],

        "rule_signal": signal_data["signal"],
        "rule_score": signal_data["score"],
        "rule_reasons": signal_data["reasons"],

        "sentiment": ai_analysis["sentiment"],
        "ai_signal": ai_analysis["ai_signal"],
        "ai_confidence": ai_analysis["confidence"],
        "ai_reasoning": ai_analysis["reasoning"],
        "risk": ai_analysis["risk"],

        "decision_engine_action": decision["final_action"],
        "decision_engine_reason": decision["decision_reason"],

        "risk_triggered": risk_check["triggered"],
        "risk_reason": risk_check["reason"],

        "final_action": final_action,
        "decision_reason": decision_reason
    }

    filename = f"log_{today}.json"

    try:
        with open(filename, "r", encoding="utf-8") as f:
            logs = json.load(f)
    except FileNotFoundError:
        logs = []
    except json.JSONDecodeError:
        logs = []

    logs.append(log_entry)

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)

    return log_entry


def run_daily_analysis():
    from stock_scanner import scan_watchlist
    from portfolio import load_portfolio

    print(f"\n=== AI Trading Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M')} ===\n")

    # Scan for candidate stocks first
    candidates = scan_watchlist()
    candidate_symbols = [c["symbol"] for c in candidates]

    # Held positions also need analysis (check stop loss / take profit)
    portfolio = load_portfolio()
    held_symbols = [p["symbol"] for p in portfolio["positions"]]

    # Merge: candidates + held positions, deduplicated
    symbols_to_analyze = list(set(candidate_symbols + held_symbols))

    if not symbols_to_analyze:
        print("No candidates found and no open positions. Skipping analysis.")
        show_portfolio_summary()
        return

    print(f"\nAnalyzing {len(symbols_to_analyze)} stock(s): {', '.join(symbols_to_analyze)}\n")

    for symbol in symbols_to_analyze:
        print(f"Analyzing {symbol}...")

        try:
            stock_data = get_stock_data(symbol)
            news_items = get_news(symbol)
            news_text = format_news_for_claude(news_items)
            signal_data = generate_signal(stock_data)
            ai_analysis = analyze_with_claude(stock_data, news_text, signal_data)
            position_exists = has_position(symbol)

            decision = decide_action(
                rule_signal=signal_data["signal"],
                rule_score=signal_data["score"],
                ai_signal=ai_analysis["ai_signal"],
                ai_confidence=ai_analysis["confidence"],
                has_position=position_exists
            )

            risk_check = check_risk_rules(symbol, stock_data["current_price"])

            if risk_check["triggered"]:
                final_action = risk_check["action"]
                decision_reason = f"{decision['decision_reason']} | Risk Override: {risk_check['reason']}"
            else:
                final_action = decision["final_action"]
                decision_reason = decision["decision_reason"]

            log = save_log(
                symbol=symbol,
                stock_data=stock_data,
                signal_data=signal_data,
                ai_analysis=ai_analysis,
                decision=decision,
                risk_check=risk_check,
                final_action=final_action,
                decision_reason=decision_reason
            )

            print(f"\n{symbol} @ ${log['price']} ({log['change_pct']}%)")
            print(f"Rule Signal: {log['rule_signal']} | Rule Score: {log['rule_score']}")
            print(f"AI Signal: {log['ai_signal']} | Sentiment: {log['sentiment']} | Confidence: {log['ai_confidence']}")
            print(f"Decision Engine Action: {log['decision_engine_action']}")
            print(f"Final Action: {log['final_action']}")

            print("Rule Reasons:")
            for reason in log["rule_reasons"]:
                print(f"  - {reason}")

            print("Relevant News:")
            if news_items:
                for item in news_items:
                    print(f"  - {item['title']} ({item['source']}, {item['published_at']}) [score={item['relevance_score']}]")
            else:
                print("  - No clearly relevant recent news")

            print(f"AI Reasoning: {log['ai_reasoning']}")
            print(f"Main Risk: {log['risk']}")
            print(f"Decision Reason: {log['decision_reason']}")

            if log["risk_triggered"]:
                print(f"Risk Override: {log['risk_reason']}")

            add_position(
                symbol,
                final_action,
                stock_data["current_price"],
                reason=decision_reason
            )

            print("-" * 60)

        except Exception as e:
            print(f"[ERROR] Failed to analyze {symbol}: {str(e)}")
            print("-" * 60)

    show_portfolio_summary()
    print("\nAnalysis complete. Log saved.")


if __name__ == "__main__":
    run_daily_analysis()