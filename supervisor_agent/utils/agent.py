import os
import sqlite3
from pprint import pformat

import requests
import yfinance as yf
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
from supervisor_agent.utils.tools import fetch_stock_data_raw, lookup_stock_symbol, place_order, web_search,halt_on_risky_tools, calculate
from supervisor_agent.utils.prompts import trading_system_message, research_system_message,supervisor_system_message
from langgraph.checkpoint.memory import InMemorySaver
from rich.console import Console
from langchain_core.messages import AIMessage

console=Console()

load_dotenv()

os.environ["LANGSMITH_PROJECT"]="supervisor_agent"


# Initialize the chat model
llm=init_chat_model(model="anthropic:claude-3-5-haiku-latest")

def safe_post_model_hook(state):
    """Composite hook: enforce non-empty AI output & risky tool halt.
    1. Run existing halt_on_risky_tools logic.
    2. If last AI message has empty/whitespace content, replace with placeholder guidance.
    """
    # First apply risky tool interception
    risky_result = halt_on_risky_tools(state)
    if risky_result:
        return risky_result
    last = state["messages"][-1]
    if isinstance(last, AIMessage):
        # Anthropic requires non-empty content
        content = getattr(last, "content", None)
        if isinstance(content, str) and not content.strip():
            last.content = "CLARIFICATION_NEEDED: Unable to proceed – previous step produced no content. Provide missing info (ticker, action, budget) or ask for research."  # mutate directly
        elif isinstance(content, list):  # some models return list of blocks
            joined = "".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in content])
            if not joined.strip():
                last.content = "CLARIFICATION_NEEDED: No usable content generated. Please restate request or add missing parameters."  # overwrite
    return {}

# Recreate agents using composite hook
trading_agent=create_react_agent(
    prompt=trading_system_message,
    tools=[lookup_stock_symbol, fetch_stock_data_raw, place_order, calculate],
    model=llm,
    name="trading_agent",
    version='v2',
    post_model_hook=safe_post_model_hook
)


research_agent = create_react_agent(
    model=llm,
    tools=[web_search],
    prompt=research_system_message,
    name="research_agent",
    post_model_hook=safe_post_model_hook
)

supervisor=create_supervisor(
    model=llm,
    agents=[research_agent,trading_agent],
    prompt=supervisor_system_message,
    output_mode="full_history",
    post_model_hook=safe_post_model_hook,
    ).compile()
    


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


