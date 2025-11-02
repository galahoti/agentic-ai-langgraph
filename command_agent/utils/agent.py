import operator
import random
from typing import Annotated, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command


# Define graph state
class State(TypedDict):
    foo: str

def node_a(state: State) -> Command[Literal["node_b", "node_c"]]:
    print("Called A")
    value = random.choice(["b", "c"])
    # this is a replacement for a conditional edge function
    if value == "b":
        goto = "node_b"
    else:
        goto = "node_c"

    # note how Command allows you to BOTH update the graph state AND route to the next node
    return Command(
        # this is the state update
        update={"foo": value},
        # this is a replacement for an edge
        goto=goto,
        graph=Command.PARENT
    )



def node_b(state: State):
    print("Called B")
    return {"foo": state["foo"] + "b"}

subgraph = (StateGraph(State).add_node(node_b).add_edge(START,"node_b")).compile()

def node_c(state: State):
    print("Called C")
    return {"foo": state["foo"] + "c"}

# --- Build the main graph ---
builder = StateGraph(State)

# Add all nodes
builder.add_node("node_a", node_a)
builder.add_node("node_b", subgraph)
builder.add_node("node_c", node_c)

# Set the entrypoint
builder.add_edge(START, "node_a")
builder.add_edge("node_b", END)
builder.add_edge("node_c", END)

graph = builder.compile()

