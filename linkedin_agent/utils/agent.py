# !pip install langgraph langchain rich langsmith langchain-google-genai langchain[anthropic]

import operator
import os
from typing import Annotated, List, Literal, Optional, TypedDict

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langsmith import traceable
from pydantic import BaseModel, Field
from rich.console import Console

console = Console()

os.environ['LANGSMITH_PROJECT']="Linkedin_Post_Agent"

load_dotenv()
# generator_llm= init_chat_model(model="google_genai:gemini-2.5-pro")
generator_llm= init_chat_model(model="google_genai:gemini-2.5-flash-lite")
critic_llm= init_chat_model(model="google_genai:gemini-2.5-flash")
optimize_llm=init_chat_model(model="anthropic:claude-3-5-haiku-latest") #anthropic:claude-opus-4-1-20250805

# State
class LinkedinState(MessagesState):
    topic: str
    linkedin_post:str
    critic_feedback: str
    critic_status: Literal['Approved','Needs_Improvement']
    iteration: int
    max_iteration: int
    post_history: Annotated[list[str],operator.add]
    feedback_history: Annotated[list[str],operator.add]

class criticState(BaseModel):
    status: Literal["Approved","Needs_Improvement"] = Field(...,description="Assess the quality of the LinkedIn post. Choose 'Approved' if it meets all criteria for engagement and clarity. Choose 'Needs_Improvement' if there are specific issues to address based on the feedback.")
    feedback: str = Field(...,description="A detailed, constructive critique of the LinkedIn post. Focus on actionable advice. Mention specific strengths and weaknesses related to tone, clarity, call-to-action, and use of hashtags. If the post 'Needs_Improvement', provide clear instructions for revision.")

# Define Structured LLM for Critic Node
structured_critic_llm=critic_llm.with_structured_output(criticState)

# Define Nodes

@traceable(name="Generate_Node",metadata={'model_provider':'google'})
def generate_post(state: LinkedinState):
    
    # Prompt
    system_message=SystemMessage(content="You are an authoritative B2B thought leader and career strategist on LinkedIn. Your goal is to provide insightful, actionable advice.") 
    human_message=HumanMessage(content=f"""
    Write an extremely professional, structured, and insightful LinkedIn post on the topic: {state['topic']}.

    Rules:
    - The tone must be polished, serious, and motivational.
    - Focus on career development, leadership, or strategic business application related to the topic.
    - Structure the post for maximum professional readability (use line breaks, short paragraphs, and professional emojis sparingly).
    - Include a strong opening hook (the common mistake or major insight).
    - End the post with a concise, actionable takeaway or question to encourage professional engagement.
    - Include 3-5 relevant, high-traffic professional hashtags (e.g., #Leadership, #CareerGrowth)
    - **CRITICAL: The entire post must be concise and under 250 words to maximize readability and engagement.**.""")
    

    # Invoke Generator LLM
    response = generator_llm.invoke([system_message] + [human_message])

    # Return response    
    return {'linkedin_post':response.content,'post_history':[response.content]}

@traceable(name="Critic_Node",metadata={'model_provider':'google'})
def critic_post(state: LinkedinState):
    # Prompt
    system_message=SystemMessage(content=
    """
    You are a **supportive LinkedIn Content Editor and Mentor** for a top-tier B2B publication. Your expertise lies in empowering authors to create effective and engaging content. You are known for being a fair, practical, and **encouraging critic**.
    ** Your role is to guide authors towards excellence**
    For posts that are not yet ready for approval, your goal is to identify 1-2 *concrete, actionable suggestions* to elevate the post to an acceptable standard. 
    For approved posts, provide brief positive affirmation, optionally with very minor, non-critical suggestions for future consideration.
    **Always ensure your feedback (excluding the 'Judgment') is less than 100 words.**
    """
    ) 
    human_message=HumanMessage(content=f"""
    Your task is to critically evaluate the provided LinkedIn post against a strict set of professional criteria and user's original ask on the topic and provide a final judgment.
    Your goal is to find the single biggest weakness that prevents this post from achieving maximum impact and engagement
    Based on your evaluation, provide a clear, concise **Judgment** ("Approved" or "Needs Improvement") followed by your **Feedback**.
                               
    ** Input Details:**
    Topic : {state['topic']}
    Linkedin Post : {state['linkedin_post']}

    **Evaluation Criteria (Consider these to affirm strengths or suggest opportunities):**

    1.  **Hook:** Does it immediately grab attention and make the reader want to learn more?
    2.  **Insight:** Does it offer genuine value, a unique perspective, or a thought-provoking idea?
    3.  **Clarity & Structure:** Is it easy to read, scannable, and free of unnecessary complexity?
    4.  **Call to Action (CTA):** Is it clear, encouraging engagement, and leads to a desired outcome?
    5.  **Tone:** Is the tone appropriate for a professional audience, authentic, and engaging?
    6.  **Hashtags:** Are they relevant, well-chosen, and likely to maximize visibility?
    7.  **Brevity:** Is the post concise, impactful, and respects the reader's time?
    """)

    # Invoke Critic LLM
    response = structured_critic_llm.invoke([system_message] + [human_message])
    
    # Return response
    return {'critic_feedback':response.feedback,'critic_status':response.status,'feedback_history':[response.feedback]}

@traceable(name="Optimize_Node",metadata={'model_provider':'anthropic'})
def optimize_post(state: LinkedinState):
    # Prompt
    system_message=SystemMessage(content=
    """
    You are an elite B2B and Technical Content Optimizer and Copywriter. You are not a generator; you are a refiner. 
    Your specialty is taking a good draft and specific, critical feedback, then producing a final, polished version that is significantly more impactful. 
    You are precise, tactical, and your revisions are always aligned with the provided critique.
    ** Always ensure that length of the feedback is less than 100 words **.
    """
    ) 
    human_message=HumanMessage(content=f"""
    Your task is to meticulously rewrite and improve the provided "Initial Draft" based *directly* on the "Critical Feedback" you have been given. 
    Your goal is to produce a final, publication-ready version of the LinkedIn post.

    ** Key Inputs: **
    1. Topic : {state['topic']} 
    2. Linkedin Post : {state['linkedin_post']}
    3. Feedback : {state['critic_feedback']} 

    **RULES FOR REVISION:**

    1.  **Address the Feedback Directly:** Your primary and most important goal is to solve the specific problems identified in the "Critical Feedback". If the feedback mentions a weak hook, your top priority is to write a stronger hook. If it mentions wordiness, you must make the post more concise.
    2.  **Preserve the Core Message:** Do not change the fundamental topic or intent of the original post. You are improving its delivery, not changing its message.
    3.  **Enhance, Don't Just Replace:** Your revision should be a clear upgrade. This may involve rephrasing sentences for impact, strengthening the call-to-action, or replacing generic phrases with more powerful language, as suggested by the feedback.
    4.  **Maintain All Original Constraints:** The final, optimized post must still adhere to all the original rules:
        -   Authoritative and professional tone.
        -   Proper structure (short paragraphs, line breaks).
        -   3-5 relevant hashtags.
        -   **Strictly under the 250-word limit.**

    **FINAL OUTPUT:**

    Your final output must ONLY be the full text of the revised, improved LinkedIn post. 
    Do not include any preambles, explanations, or commentary like "Here is the revised post:". Just provide the post content itself.
    """)

    # Invoke Optimize LLM
    response = optimize_llm.invoke([system_message] + [human_message])
    iteration=state['iteration']+1

    # Return response    
    return {'linkedin_post':response.content, 'iteration':iteration, 'post_history':[response.content]}

def should_continue(state: LinkedinState) -> Literal['Approved','Needs_Improvement']:
    
    if state["critic_status"] == 'Approved' or state['iteration'] >= state['max_iteration']:
        return 'Approved'
    else:
        return 'Needs_Improvement'

# Build Graph and Add Nodes
workflow=StateGraph(LinkedinState)
workflow.add_node("generator",generate_post)
workflow.add_node("critic",critic_post)
workflow.add_node("optimizer",optimize_post)


# Add Business Logic
workflow.add_edge(START,"generator")
workflow.add_edge("generator","critic")
workflow.add_conditional_edges("critic",should_continue,{'Approved':END,"Needs_Improvement":"optimizer"})
workflow.add_edge("optimizer","critic")

# Compile Grpah
linkedin_agent=workflow.compile()



# Invoke the Agent/Workflow
user_input={'topic':'Does AI Agents has potential to generate meaningful business value for Enterprises?','max_iteration':5,'iteration':0}

config={
    'run_name':"Linkedin_Agent",
    'tags': ['Agentic Application','Research','Assistant'],
    'metadata': {'model_provider':'Anthropic-Google','app_type':'agentic'}
    }

# agent_response=linkedin_agent.invoke(user_input,config)

# print(linkedin_agent.get_graph().draw_ascii())

################################### Testing  #####################################

if __name__ == "__main__":
    user_input={'topic':'What is the biggest challenge in operationalizing the agents to production and how to solve it uusing AWS AgentCore ?','max_iteration':2,'iteration':0}
    
    import json 
# Ensure stream_mode="updates" is correctly passed
    for event in linkedin_agent.stream(user_input, stream_mode="updates"):
        # The 'event' itself is the update, e.g., {'critic': {...}}

        # Iterate over the single key-value pair in the event dictionary
        for node_name, output_value in event.items():
            console.print(f"\n--- Node: [{node_name}] ---")
            # The output_value might be a dictionary (like your 'critic' example),
            # so print it in a readable format.
            if isinstance(output_value, dict):
                console.print(json.dumps(output_value, indent=2))
            else:
                console.print(output_value)
            
            console.print("-" * 30) # Add a separator for better readability between node outputs
    
    # agent_response=linkedin_agent.invoke(user_input)


    # console.print(f"\n #### User Topic #### \n {agent_response['topic']} \n")
    # console.print(f"\n #### Generated Linkedin Post #### \n  {agent_response['linkedin_post']} \n")
    # console.print(f"\n #### Critic Status #### \n  {agent_response['critic_status']} \n")
    # console.print(f"\n #### Critic Feedback #### \n  {agent_response['critic_feedback']} \n")
    # console.print(f"\n #### Iteration #### \n  {agent_response['iteration']} \n")
    # console.print(f"\n #### Refined Linkedin Post #### \n  {agent_response['linkedin_post']} \n")

    # # print("\n #### Post History ####")
    # # for i, post in enumerate(agent_response['post_history']):
    # #     console.print(f"\n #### Message {i+1} #### \n  {post} \n")
    # #     for j, feedback in enumerate(agent_response['feedback_history']):
    # #         console.print(f"\n #### Feedback {i+1} #### \n  {feedback} \n")
    # #         exit
            
    # console.print("\n #### Post History ####")
    # history_pairs = zip(agent_response['post_history'], agent_response['feedback_history'])

    # for i, (post, feedback) in enumerate(history_pairs, start=1):
    #     console.print(f"\n #### Message {i} #### \n  {post} \n")
    #     console.print(f"\n #### Feedback {i} #### \n  {feedback} \n")
