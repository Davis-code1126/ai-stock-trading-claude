def decide_action(rule_signal, rule_score, ai_signal, ai_confidence, has_position):
    confidence_rank = {
        "Low": 1,
        "Medium": 2,
        "High": 3
    }

    ai_rank = confidence_rank.get(ai_confidence, 1)

    if rule_signal == "SELL":
        if has_position:
            return {
                "final_action": "SELL",
                "decision_reason": "Rule strategy detected a sell condition while position exists."
            }
        return {
            "final_action": "HOLD",
            "decision_reason": "Rule strategy suggested SELL, but there is no existing position to exit."
        }

    if rule_signal == "BUY":
        if has_position:
            return {
                "final_action": "HOLD",
                "decision_reason": "Rule strategy suggested BUY, but position already exists."
            }
        if ai_signal in ["BUY", "HOLD"] and ai_rank >= 2:
            return {
                "final_action": "BUY",
                "decision_reason": f"Strong rule BUY confirmed or not opposed by AI (AI: {ai_signal}, confidence: {ai_confidence})."
            }
        return {
            "final_action": "HOLD",
            "decision_reason": f"Rule BUY exists, but AI is too negative or uncertain (AI: {ai_signal}, confidence: {ai_confidence})."
        }

    if rule_signal == "WATCHLIST_BUY":
        if has_position:
            return {
                "final_action": "HOLD",
                "decision_reason": "Watchlist buy detected, but position already exists."
            }
        if ai_signal == "BUY" and ai_rank >= 2:
            return {
                "final_action": "BUY",
                "decision_reason": f"Partial bullish rule setup upgraded to BUY by AI confirmation (confidence: {ai_confidence})."
            }
        return {
            "final_action": "HOLD",
            "decision_reason": f"Partial bullish setup exists, but AI confirmation is insufficient (AI: {ai_signal}, confidence: {ai_confidence})."
        }

    if rule_signal == "HOLD":
        if has_position and ai_signal == "SELL" and ai_rank == 3:
            return {
                "final_action": "SELL",
                "decision_reason": "Rule is neutral, but AI strongly suggests SELL while position exists."
            }

        if (not has_position) and ai_signal == "BUY" and ai_rank == 3 and rule_score >= 3:
            return {
                "final_action": "BUY",
                "decision_reason": "Rule is neutral but close to bullish, and AI strongly suggests BUY."
            }

        return {
            "final_action": "HOLD",
            "decision_reason": f"Rule strategy is HOLD, so no trade is taken (AI signal: {ai_signal}, confidence: {ai_confidence})."
        }

    return {
        "final_action": "HOLD",
        "decision_reason": "Fallback HOLD due to unexpected signal input."
    }