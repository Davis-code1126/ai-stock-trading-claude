def generate_signal(stock_data):
    reasons = []
    score = 0

    price = stock_data.get("current_price")
    ma20 = stock_data.get("ma20")
    ma50 = stock_data.get("ma50")
    volume = stock_data.get("volume")
    avg_volume_20 = stock_data.get("avg_volume_20")
    rsi = stock_data.get("rsi")

    required_fields = {
        "current_price": price,
        "ma20": ma20,
        "ma50": ma50,
        "volume": volume,
        "avg_volume_20": avg_volume_20,
        "rsi": rsi
    }

    missing = [k for k, v in required_fields.items() if v is None]
    if missing:
        return {
            "signal": "HOLD",
            "score": 0,
            "reasons": [f"Missing required fields: {', '.join(missing)}"]
        }

    cond_price_above_ma20 = price > ma20
    cond_ma20_above_ma50 = ma20 > ma50
    cond_volume_confirm = volume > avg_volume_20
    cond_rsi_ok = 45 <= rsi < 70

    if cond_price_above_ma20:
        score += 1
        reasons.append("Price is above MA20")
    else:
        reasons.append("Price is below or equal to MA20")

    if cond_ma20_above_ma50:
        score += 1
        reasons.append("MA20 is above MA50")
    else:
        reasons.append("MA20 is below or equal to MA50")

    if cond_volume_confirm:
        score += 1
        reasons.append("Volume is above 20-day average")
    else:
        reasons.append("Volume is below or equal to 20-day average")

    if cond_rsi_ok:
        score += 1
        reasons.append("RSI is in a healthy bullish range")
    elif rsi < 45:
        reasons.append("RSI is below 45, momentum is weak")
    elif 70 <= rsi < 80:
        reasons.append("RSI is above 70, overbought risk is increasing")
    else:
        reasons.append("RSI is extremely high, pullback risk is elevated")

    if price < ma20 and ma20 < ma50:
        signal = "SELL"
        reasons.append("Downtrend detected: price < MA20 < MA50")

    elif cond_price_above_ma20 and cond_ma20_above_ma50 and cond_volume_confirm and cond_rsi_ok:
        signal = "BUY"
        reasons.append("Strong bullish setup detected")

    elif cond_price_above_ma20 and score >= 3 and rsi < 75:
        signal = "WATCHLIST_BUY"
        reasons.append("Partial bullish setup detected; worth allowing AI to confirm")

    else:
        signal = "HOLD"
        reasons.append("Conditions are mixed or insufficient for a high-conviction trade")

    return {
        "signal": signal,
        "score": score,
        "reasons": reasons
    }