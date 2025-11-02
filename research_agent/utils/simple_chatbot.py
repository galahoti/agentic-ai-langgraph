import os
import sqlite3
from pprint import pformat

import requests
import yfinance as yf
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langsmith import traceable
from rich.console import Console

console=Console()

load_dotenv()

os.environ["LANGSMITH_PROJECT"]="simple_chatbot"

# Custom Tool
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

# Prebuilt Tool
search_tool=DuckDuckGoSearchRun(region="us-en",max_results=2)

# Bind Tools to LLM
tools=[search_tool,lookup_stock_symbol,fetch_stock_data_raw]
# llm_with_tool=llm.bind_tools(tools,parallel_tool_calls=False) #tool_choice="any"

def dynamic_model_selector(state: MessagesState):
    """Select model depending on the query intent."""
    model = None

    user_msg = state["messages"][-1].content.lower()
    if any(word in user_msg for word in ["analyze", "invest", "risks"]):
        print("Select Model for Heavy reasoning → more powerful model (gpt-4)")
        model=init_chat_model(model="anthropic:claude-3-5-haiku-latest")
    elif "summarize" in user_msg:
        print("Select Model for Quick summarization → lightweight model (gpt-4o-mini)")
        model=init_chat_model(model="anthropic:claude-3-5-haiku-latest")
    else:
        print("Select Model for Default fallback (gpt-3.5-turbo)")
        model=init_chat_model(model="anthropic:claude-3-5-haiku-latest")
    
    return model.bind_tools(tools)

    @tool("tavily_web_search")
    def tavily_web_search(query: str) -> str:
        """
        Performs a web search using the Tavily API.

        Parameters:
            query (str): The search query.

        Returns:
            str: The search results or an error message.
        """
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return "Tavily API key not found in environment variables."

        url = "https://api.tavily.com/search"
        headers = {"Authorization": f"Bearer {api_key}"}
        params = {"query": query, "max_results": 3}

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])
            if not results:
                return "No results found."
            return pformat(results)
        except Exception as e:
            return f"Error during Tavily web search: {str(e)}"

# Define Nodes
@traceable(name="chatbot-assisstant")
def chatbot(state: MessagesState):
    """LLM Chatbot Node that may answer or request a tool call"""
    model=dynamic_model_selector(state)
    return {'messages': [model.invoke(state['messages'])]}

tool_node=ToolNode(tools)

# Build Graph
workflow=StateGraph(MessagesState)
workflow.add_node("chatbot",chatbot)
workflow.add_node("tools",tool_node)

# Logic
workflow.add_edge(START,"chatbot")
workflow.add_conditional_edges("chatbot",tools_condition)
workflow.add_edge("tools","chatbot")

# Setup DB
conn=sqlite3.connect(database="chatbot.db",check_same_thread=False)

# Setup Checkpointer
memory=SqliteSaver(conn)

# Compile
chatbot=workflow.compile()
# chatbot=workflow.compile(checkpointer=memory)

def return_all_threads():
    all_threads=set()
    for checkpoint in memory.list(None):
        all_threads.add(checkpoint.config['configurable']['thread_id'])
    return list(all_threads)


# ################### Local Testing #####################

# if __name__ == "__main__":
#     user_input={'messages':'what stock price of Microsoft'}
#     config={
#         'configurable':{'thread_id':'thread-3'},
#         'run_name':"chat_turn",
#         'tags': ['LLM Application','Chatbot','assistant'],
#         'metadata': {'thread_id':'thread-3','model':'claude-3-5-haiku-latest','app_type':'agentic'}
#         }


#     response = chatbot.stream(user_input,config,stream_mode='updates')
#     for event in response:
#          for node_name,state_update in event.items():
#             console.print(f"\n--- Update from Node: '{node_name}' ---\n")
#             console.print(f"{state_update['messages'][-1].content}")


