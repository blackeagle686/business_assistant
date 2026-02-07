from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class IdeaInput(BaseModel):
    idea_text: str = Field(..., description="The user's initial business idea.")
    session_id: str = Field(..., description="Unique session identifier.")

class ClarificationQuestion(BaseModel):
    question_id: str
    question_text: str
    context: Optional[str] = None

class ClarificationResponse(BaseModel):
    session_id: str
    answers: Dict[str, str] = Field(..., description="Map of question_id to user answer.")

class KPI(BaseModel):
    name: str
    description: str
    formula: str
    importance: str
    frequency: str

class BusinessModelCanvas(BaseModel):
    value_proposition: List[str]
    customer_segments: List[str]
    revenue_streams: List[str]
    cost_structure: List[str]
    key_activities: List[str]
    key_resources: List[str]
    key_partners: List[str]
    channels: List[str]
    customer_relationships: List[str]

class MarketAnalysis(BaseModel):
    market_size: str
    growth_trends: List[str]
    competitors: List[str]
    opportunities: List[str]
    risks: List[str]
    relevant_use_cases: List[str]

class BusinessPlan(BaseModel):
    executive_summary: str
    market_analysis: MarketAnalysis
    business_model: BusinessModelCanvas
    kpis: List[KPI]
    assumptions_constraints: List[str]
    recommendations: str

class DashboardData(BaseModel):
    session_id: str
    idea_summary: str
    plan: Optional[BusinessPlan]
    status: str
    clarification_questions: Optional[List[ClarificationQuestion]]

class ChatRequest(BaseModel):
    session_id: str
    topic: str
    context: str
    message: str
