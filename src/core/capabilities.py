import httpx
from pydantic_ai import RunContext
from pydantic_ai.capabilities import Capability

weather = Capability(
    id="weather",
    description="Get current weather for any location.",
    defer_loading=True,
)


@weather.tool
async def get_weather(ctx: RunContext[None], location: str) -> str:
    """Get the current weather for a given location.

    Args:
        location: The city or region to get weather for.
    """
    url = f"https://wttr.in/{location}?format=%C+%t+%w+%h"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10)
        resp.raise_for_status()
        return f"Weather in {location}: {resp.text.strip()}"


stock_prices = Capability(
    id="stock_prices",
    description="Get current stock market prices and trading information.",
    defer_loading=True,
)


@stock_prices.tool
async def get_stock_price(ctx: RunContext[None], symbol: str) -> str:
    """Get the current stock price and trading info for a given symbol.

    Args:
        symbol: The stock ticker symbol (e.g. AAPL, GOOGL, MSFT).
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

    result = data["chart"]["result"][0]
    meta = result["meta"]
    price = meta["regularMarketPrice"]
    currency = meta["currency"]
    high = meta["regularMarketDayHigh"]
    low = meta["regularMarketDayLow"]
    volume = meta["regularMarketVolume"]
    name = meta.get("longName", symbol)

    quote = result["indicators"]["quote"][0]
    open_price = quote.get("open", [price])[0]
    close = quote.get("close", [price])[-1]
    change = close - open_price
    pct = (change / open_price * 100) if open_price else 0

    arrow = "▲" if change >= 0 else "▼"
    return (
        f"{name} ({symbol})\n"
        f"Price: {currency} {price:.2f} {arrow} {change:+.2f} ({pct:+.2f}%)\n"
        f"Day range: {low:.2f} - {high:.2f}\n"
        f"Volume: {volume:,}"
    )
