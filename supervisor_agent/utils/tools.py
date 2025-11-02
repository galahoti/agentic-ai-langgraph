from langchain.tools import tool
import yfinance as yf
import requests
from pprint import pformat
from typing import List, Dict
from langchain_tavily import TavilySearch
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.types import interrupt
from langchain_core.tools import tool

@tool("lookup_stock")
def lookup_stock_symbol(company_name: str) -> str:
    """
    Converts a company name to its stock symbol using a financial API.

    Parameters:
        company_name (str): The full company name (e.g., 'Tesla').

    Returns:
        str: The stock symbol (e.g., 'TSLA') or an error message.
    """
    api_url = "https://www.alphavantage.co/query"
    params = {
        "function": "SYMBOL_SEARCH",
        "keywords": company_name,
        "apikey": "M6TWTX8BGKW2BCUV"
    }
    
    response = requests.get(api_url, params=params)
    data = response.json()
    
    if "bestMatches" in data and data["bestMatches"]:
        return data["bestMatches"][0]["1. symbol"]
    else:
        return f"Symbol not found for {company_name}."
    
@tool("fetch_stock_data")
def fetch_stock_data_raw(stock_symbol: str) -> dict:
    """
    Fetches comprehensive stock data for a given symbol and returns it as a combined dictionary.

    Parameters:
        stock_symbol (str): The stock ticker symbol (e.g., 'TSLA').
        period (str): The period to analyze (e.g., '1mo', '3mo', '1y').

    Returns:
        dict: A dictionary combining general stock info and historical market data.
    """
    period = "1mo"
    try:
        stock = yf.Ticker(stock_symbol)

        # Retrieve general stock info and historical market data
        stock_info = stock.info  # Basic company and stock data
        stock_history = stock.history(period=period).to_dict()  # Historical OHLCV data

        # Combine both into a single dictionary
        combined_data = {
            "stock_symbol": stock_symbol,
            "info": stock_info,
            "history": stock_history
        }

        return pformat(combined_data)

    except Exception as e:
        return {"error": f"Error fetching stock data for {stock_symbol}: {str(e)}"}

@tool
def place_order(
    symbol: str,
    action: str,
    shares: int,
    limit_price: float,
    order_type: str = "limit",
) -> dict:
    """
    Execute a stock order.

    Parameters:
    - symbol: Ticker
    - action: "buy" or "sell"
    - shares: Number of shares to trade (pre-computed by the agent)
    - limit_price: Limit price per share
    - order_type: Order type, default "limit"

    Returns:
    - status: Execution result (simulated)
    - symbol
    - shares
    - limit_price
    - total_spent
    - type: Order type used
    - action
    """
    total_spent = round(int(shares) * limit_price, 2)
    return {
        "status": "filled",
        "symbol": symbol,
        "shares": int(shares),
        "limit_price": limit_price,
        "total_spent": total_spent,
        "type": order_type,
        "action": action,
    }


FORBIDDEN_KEYWORDS = {
    "403 forbidden", "access denied", "captcha",
    "has been denied", "not authorized", "verify you are a human"
}

@tool
def web_search(query: str, max_results: int = 5) -> Dict[str, List[Dict[str, str]]]:
    """
    General-purpose web search.

    Use when you need recent or broader information from the web to answer the user's request
    (e.g., discover relevant entities, find supporting context, or gather up-to-date references).

    Parameters:
    - query (str): The search query in plain language.
    - max_results (int): Number of results to return (default 5, max 10).

    Returns:
    - {"results": [{"title": str, "url": str, "snippet": str}, ...]}

    Example:
    - query: "emerging AI hardware companies"
    """
    max_results = max(1, min(max_results, 10))
    tavily = TavilySearch(max_results=max_results)
    raw = tavily.invoke({"query": query})

    results = [
        {k: v for k, v in page.items() if k != "raw_content"}  # drop heavy field
        for page in raw["results"]
        if not any(
            k in ((page.get("content") or "").lower())
            for k in FORBIDDEN_KEYWORDS
        )
    ]

    if not results:
        return {"results": "No results found for the query."}

    return {"results": results}

RISKY_TOOLS = {"place_order"}

def halt_on_risky_tools(state):
    last = state["messages"][-1]
    print(f"Post-model hook checking for risky tools in message: {last}")
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        for tc in last.tool_calls:
            print(f"Post-model hook inspecting tool call: {tc}")
            if tc.get("name") in RISKY_TOOLS:
                decision = interrupt({"awaiting": tc["name"], "args": tc.get("args", {})})
                print(f"Post-model hook received interrupt decision: {decision}")
                # tool approved
                if isinstance(decision, dict) and decision.get("approved"):
                    return {}

                # tool rejected
                tool_msg = ToolMessage(
                    content=f"Cancelled by human. Continue without executing that tool and provide next steps.",
                    tool_call_id=tc["id"],
                    name=tc["name"]
                )
                return {"messages": [tool_msg]}

    return {}

@tool
def calculate(a: float, b: float, operation: str) -> float:
    """
    Performs a specified arithmetic operation on two numbers.

    Parameters:
    - a (float): The first number.
    - b (float): The second number.
    - operation (str): The operation to perform. Must be one of 'add', 'subtract', 'multiply', or 'divide'.

    Returns:
    - float: The result of the arithmetic operation.
    """
    if operation == 'add':
        return a + b
    elif operation == 'subtract':
        return a - b
    elif operation == 'multiply':
        return a * b
    elif operation == 'divide':
        if b == 0:
            raise ValueError("Cannot divide by zero.")
        return a / b
    else:
        raise ValueError("Invalid operation. Must be one of 'add', 'subtract', 'multiply', or 'divide'.")