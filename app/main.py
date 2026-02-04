import uuid
import logging
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.schemas import (
    IdeaInput, ClarificationQuestion, ClarificationResponse, 
    DashboardData, BusinessPlan
)
from app.llm_service import llm_client
from app.rag import rag_service

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BusinessAdvisor")

app = FastAPI(title="Business Advice Assistant", version="1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-Memory Storage (Replace with DB in Production)
sessions: Dict[str, Dict] = {}

@app.post("/api/idea/submit", response_model=Dict[str, Any])
async def submit_idea(input_data: IdeaInput):
    """
    Step 1: User submits an idea.
    Server: Generates session, finds Clarification Questions.
    """
    session_id = input_data.session_id if input_data.session_id else str(uuid.uuid4())
    
    # Store initial state
    sessions[session_id] = {
        "idea": input_data.idea_text,
        "clarifications_needed": [],
        "answers": {},
        "plan": None,
        "status": "clarification_needed"
    }
    
    # Generate questions
    try:
        questions = await llm_client.generate_clarification_questions(input_data.idea_text)
        sessions[session_id]["clarifications_needed"] = questions
        
        return {
            "session_id": session_id,
            "status": "clarification_required",
            "questions": questions,
            "message": "Please answer the following questions to refine the plan."
        }
        
    except Exception as e:
        logger.error(f"Error in submit_idea: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/idea/clarify", response_model=Dict[str, Any])
async def submit_clarification(response: ClarificationResponse):
    """
    Step 2: User answers questions.
    Server: Generates Full Business Plan.
    """
    session_id = response.session_id
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    session = sessions[session_id]
    session["answers"].update(response.answers)
    session["status"] = "generating_plan"
    
    # RAG Retrieval
    idea_text = session["idea"]
    rag_context = rag_service.search(idea_text + " " + " ".join(response.answers.values()))
    
    # Generate Plan
    try:
        plan = await llm_client.generate_business_plan(idea_text, session["answers"], rag_context)
        session["plan"] = plandict = plan.dict() # Store as dict
        session["status"] = "complete"
        
        return {
            "session_id": session_id,
            "status": "complete",
            "message": "Business Plan Generated Successfully"
        }
    except Exception as e:
        logger.error(f"Error generating plan: {e}")
        session["status"] = "error"
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/{session_id}", response_model=DashboardData)
def get_dashboard(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    sess = sessions[session_id]
    
    # Reconstruct objects if needed, or return raw dict if schema matches
    plan_obj = BusinessPlan(**sess["plan"]) if sess["plan"] else None
    
    return DashboardData(
        session_id=session_id,
        idea_summary=sess["idea"],
        plan=plan_obj,
        status=sess["status"],
        clarification_questions=sess["clarifications_needed"] if not sess["plan"] else []
    )

# Static Files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

