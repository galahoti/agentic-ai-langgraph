from typing import Literal

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage

from research_agent.utils.state import ResearchTeam, State

load_dotenv()

llm=init_chat_model(model="anthropic:claude-3-5-haiku-latest")

system_instructions_template = """ You are an expert AI assistant tasked with orchestrating a high-performing deep research team. Your goal is to generate profiles for a specified number of unique research specialists, or "analysts," based on a given research {topic} and the desired number of analysts.
Each analyst must have a distinct role, skillset, and a clear contribution focus that is *directly relevant and complementary* to the provided research topic. Their combined expertise should offer a comprehensive, multi-faceted approach to the topic.
Examine any editorial feedback that has been optionally provided to guide creation of the analysts: {human_feedback} 

**Constraints & Guidelines:**
1.  **Relevance:** Every analyst's profile (role, skillset, contribution focus) must be highly relevant to the `research_topic`.
2.  **Diversity:** Aim for a diverse range of perspectives and expertise if the topic allows (e.g., technical, business, ethical, historical, social, economic, scientific). Avoid redundant skillsets or roles.
3.  **Realism:** Generate plausible, professional-sounding names, roles, and designations.
4.  **Contribution Focus:** The `contribution_focus` should be a concise, actionable statement describing *how* that analyst will specifically contribute to researching the `research_topic`.
5.  **Skillset:** Provide a list of 3-5 distinct, relevant skills for each analyst.
6.  **Quantity:** Ensure the total number of analysts generated exactly matches the {max_analysts} input."""

# create analyst node
def create_research_analyst(state: State) -> State:
  """ creates analyst for the research team """
  topic=state["topic"]
  max_analysts=state["max_analysts"]
  human_feedback=state.get("human_feedback", "")

  structured_llm=llm.with_structured_output(ResearchTeam)

  # create a system instruction
  system_instructions = system_instructions_template.format(topic=topic, max_analysts=max_analysts, human_feedback=human_feedback)

  response = structured_llm.invoke([SystemMessage(content=system_instructions)] + [HumanMessage(content="create the set of analyst")])

  return {"research_team": response}

# No-ops node
def human_feedback(state: State) -> State:
  """ human feedback """
  pass

def should_continue(state: State) -> Literal["feedback_provided","no_feedback"]:
  """ Return the human feedback status"""
  human_feedback=state.get('human_feedback',None)
  if human_feedback:
    return "feedback_provided"
  else:
    return 'no_feedback'