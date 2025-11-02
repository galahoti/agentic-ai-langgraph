from typing import Annotated, List, Optional, TypedDict

from pydantic import BaseModel, Field


class ResearchAnalyst(BaseModel):
    """
    Represents a specialized research analyst profile within a research team.
    """
    name: str = Field(..., description="The name of the research analyst.")
    role: str = Field(..., description="The primary functional role of the analyst (e.g., 'Data Scientist', 'Market Strategist', 'Technical Lead').")
    designation: str = Field(..., description="The professional designation or title of the analyst (e.g., 'Senior Research Fellow', 'Associate Analyst', 'Lead Engineer').")
    skillset: List[str] = Field(..., description="A list of core skills and expertise areas relevant to their role and the research topic.")
    contribution_focus: str = Field(..., description="A concise description of this analyst's specific angle or primary contribution to the research topic. This should align with the overall topic's requirements.")
    brief_bio: Optional[str] = Field(None, description="An optional, brief background or summary of the analyst's experience, providing context for their expertise.")

    @property
    def persona(self) -> str:
        return f"Name: {self.name}\nRole: {self.role}\nDesignation: {self.designation}\nSkillset: {self.skillset}\nContribution_Focus: {self.contribution_focus}\nBrief_Bio: {self.brief_bio}\n"

class ResearchTeam(BaseModel):
    """
    Represents a full team of specialized research analysts assigned to a particular research topic.
    """
    analysts: List[ResearchAnalyst] = Field(
        ...,
        description="A comprehensive list of specialized research analysts forming the research team for a given topic."
    )

class State(TypedDict):
   topic: Annotated[str,"Research topic"]
   max_analysts: Annotated[int,"Number of analysts"]
   research_team: Annotated[List[ResearchAnalyst],"list of specialized research analysts forming the research team for a given topic"]
   human_feedback: Annotated[Optional[str],"human feedback"]