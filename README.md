# AI Stock Trading System

A Python-based semi-automated stock analysis system powered by Claude AI. Scans a watchlist of 14 top tech stocks daily, combines technical indicators with AI-driven news analysis, and simulates trades with full risk management.

## Features

- **Stock Scanner**: Automatically scans 14 tech stocks (AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA, AMD, AVGO, NFLX, CRM, INTC, PLTR, MU) to find candidates worth analyzing
- **Dual Signal Engine**: Combines rule-based technical analysis (MA20, MA50, RSI, volume) with Claude AI sentiment analysis
- **News Integration**: Pulls real-time stock news via yfinance and scores relevance using a custom algorithm
- **Memory System**: Tracks historical performance and feeds insights back to Claude for continuous improvement
- **Risk Management**: Automatic stop loss (5%), take profit (10%), and max holding period (10 days)
- **Portfolio Tracking**: Simulated $10,000 capital with real-time P&L tracking
- **Decision Engine**: Three-tier decision logic combining rule signals, AI confidence, and position state

## How It Works

1. **Scan**: System scans 14 watchlist stocks, filtering down to candidates showing bullish technical setups
2. **Analyze**: Each candidate gets full analysis — technical indicators + recent news + Claude AI evaluation
3. **Decide**: Decision engine combines rule signal and AI signal to make BUY/HOLD/SELL calls
4. **Risk Check**: Active positions are checked against stop loss, take profit, and max hold rules
5. **Log**: Every decision is logged with full reasoning for future memory and analysis

## Requirements

- Python 3.11+
- Anthropic API key (get one at console.anthropic.com)
- Internet connection for yfinance data

## Setup

1. Install dependencies:
pip install anthropic yfinance requests schedule

2. Rename `config.example.py` to `config.py` and add your Claude API key

3. Run the analyzer:
python analyzer.py

## Project Structure

- `analyzer.py` — Main analysis orchestrator
- `stock_scanner.py` — Scans watchlist for candidates
- `strategy.py` — Rule-based signal generation
- `decision_engine.py` — Combines rule and AI signals
- `news_service.py` — News fetching and relevance scoring
- `portfolio.py` — Position tracking and risk management
- `memory.py` — Historical performance feedback loop
- `scheduler.py` — Automated daily runs

## Important Notes

- This is a **simulation system** for learning and research purposes
- All trades are simulated with virtual capital — no real money is at stake
- Past performance does not guarantee future results
- Always do your own research before making real investment decisions

## License

MIT License — free for personal and commercial use