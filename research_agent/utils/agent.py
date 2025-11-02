from langgraph.graph import END, START, StateGraph

from research_agent.utils.nodes import (create_research_analyst,
                                        human_feedback, should_continue)
from research_agent.utils.state import State

# Build Graph
workflow=StateGraph(State)
workflow.add_node("create_research_analyst",create_research_analyst)
workflow.add_node("human_feedback",human_feedback)

# Logic
workflow.add_edge(START,"create_research_analyst")
workflow.add_edge("create_research_analyst","human_feedback")
workflow.add_conditional_edges("human_feedback",should_continue,{
    "feedback_provided": "create_research_analyst",
    "no_feedback": END
})
workflow.add_edge("create_research_analyst",END)

# Compile
graph=workflow.compile(interrupt_before=['human_feedback'])

# print("Successfully compiled the graph")
# user_input=input("Enter the research topic: ")

# state={"topic":user_input,"max_analysts":3}

# response=graph.invoke(state)

# print(response)

# print("Research Team:")
# for analyst in response["research_team"].analysts:
#     print(analyst.persona)  