import yfinance as yf
from datetime import datetime

COMPANY_TERMS = {
    "AAPL": ["apple", "aapl", "iphone", "ipad", "mac", "app store", "tim cook", "john ternus"],
    "MSFT": ["microsoft", "msft", "azure", "windows", "copilot", "satya nadella", "office", "teams"],
    "NVDA": ["nvidia", "nvda", "gpu", "cuda", "datacenter", "h100", "blackwell", "jensen huang"],
    "AMZN": ["amazon", "amzn", "aws", "prime", "alexa", "andy jassy", "ecommerce"],
    "GOOGL": ["google", "googl", "alphabet", "youtube", "gemini", "search", "sundar pichai", "waymo"],
    "META": ["meta", "facebook", "instagram", "whatsapp", "mark zuckerberg", "ray-ban", "threads"],
    "TSLA": ["tesla", "tsla", "ev", "deliveries", "gigafactory", "autopilot", "robotaxi", "elon musk"],
    "AMD": ["amd", "advanced micro devices", "ryzen", "radeon", "epyc", "lisa su"],
    "AVGO": ["broadcom", "avgo", "semiconductor", "vmware", "hock tan"],
    "NFLX": ["netflix", "nflx", "streaming", "subscribers", "ted sarandos"],
    "CRM": ["salesforce", "crm", "marc benioff", "cloud software", "slack"],
    "INTC": ["intel", "intc", "pat gelsinger", "foundry", "core ultra"],
    "PLTR": ["palantir", "pltr", "alex karp", "government contract", "gotham", "foundry"],
    "MU": ["micron", "mu", "dram", "nand", "memory chip", "hbm"]
}

MARKET_CATALYST_TERMS = [
    "earnings", "revenue", "guidance", "forecast", "analyst", "upgrade", "downgrade",
    "price target", "margin", "sales", "demand", "shipment", "deliveries",
    "launch", "product launch", "quarter", "q1", "q2", "q3", "q4",
    "ban", "export", "tariff", "regulation", "lawsuit", "approval",
    "partnership", "acquisition", "buyback", "dividend", "outlook","interest rate", "fed", "inflation", "layoff", "restructuring",
    "beat", "miss", "eps", "guidance raise", "guidance cut", "short squeeze"
]

LOW_SIGNAL_TERMS = [
    "release date", "game", "gaming", "walkthrough", "how to", "tips",
    "best apps", "vs", "comparison", "rumor", "wishlist"
]

NEGATIVE_NOISE_KEYWORDS = [
    "murder", "crime", "killed", "arrested", "celebrity", "gossip",
    "shooting", "scandal"
]

TRUSTED_SOURCES = {
    "Reuters", "Bloomberg", "CNBC", "MarketWatch", "Yahoo Finance",
    "The Wall Street Journal", "Barron's", "Financial Times", "Associated Press"
    "Barron's", "Seeking Alpha", "Investor's Business Daily",
    "GuruFocus.com", "24/7 Wall St.", "Benzinga"
}


def score_article(symbol, article):
    title = (article.get("title") or "").lower()
    desc = (article.get("description") or "").lower()
    source = (article.get("source") or "").strip()
    text = f"{title} {desc}"

    score = 0

    company_hits = 0
    for term in COMPANY_TERMS.get(symbol, [symbol.lower()]):
        if term in text:
            company_hits += 1
            score += 2

    catalyst_hits = 0
    for term in MARKET_CATALYST_TERMS:
        if term in text:
            catalyst_hits += 1
            score += 3

    for term in LOW_SIGNAL_TERMS:
        if term in text:
            score -= 3

    for term in NEGATIVE_NOISE_KEYWORDS:
        if term in text:
            score -= 5

    if source in TRUSTED_SOURCES:
        score += 3
    else:
        score -= 1

    if company_hits > 0 and catalyst_hits == 0:
        score -= 2

    if company_hits == 0 and catalyst_hits == 0:
        score -= 5

    return score


def get_news(symbol, max_items=5):
    try:
        stock = yf.Ticker(symbol)
        raw_news = stock.news
    except Exception:
        return []

    if not raw_news:
        return []

    cleaned = []
    seen_titles = set()

    for item in raw_news:
        content = item.get("content") or item

        title = (content.get("title") or "").strip()
        if not title:
            continue

        title_key = title.lower()
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)

        source = (
            (content.get("provider") or {}).get("displayName")
            or content.get("publisher")
            or "Yahoo Finance"
        )

        pub_time = content.get("pubDate") or content.get("published_at") or ""
        published_at = pub_time[:10] if pub_time else datetime.now().strftime("%Y-%m-%d")

        summary = (
            content.get("summary")
            or content.get("description")
            or content.get("snippet")
            or ""
        )

        url = ""
        canonical = content.get("canonicalUrl")
        if isinstance(canonical, dict):
            url = canonical.get("url", "")
        elif isinstance(canonical, str):
            url = canonical

        article = {
            "title": title,
            "description": summary,
            "source": source,
            "published_at": published_at,
            "url": url,
        }

        article["relevance_score"] = score_article(symbol, article)
        cleaned.append(article)

    cleaned.sort(key=lambda x: (x["relevance_score"], x["published_at"]), reverse=True)
    filtered = [x for x in cleaned if x["relevance_score"] >= 5]

    return filtered[:max_items]


def format_news_for_claude(news_items):
    if not news_items:
        return "No clearly relevant recent news."

    lines = []
    for item in news_items:
        lines.append(
            f"- {item['title']} ({item['source']}, {item['published_at']}) [score={item['relevance_score']}]\n"
            f"  Summary: {item['description']}"
        )
    return "\n".join(lines)