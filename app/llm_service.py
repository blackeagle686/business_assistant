import httpx
import json
import logging
from typing import List, Dict, Any, Optional
from app.schemas import ClarificationQuestion, BusinessPlan, BusinessModelCanvas, KPI, MarketAnalysis

logger = logging.getLogger(__name__)

class LLMClient:
    _instance = None
    _base_url = "http://localhost:11434/api/generate"  # Default Ollama
    _model_name = "qwen2.5-coder:1.5b" # Default, can be overridden

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LLMClient, cls).__new__(cls)
            logger.info("LLMClient Singleton Initialized")
        return cls._instance

    def set_config(self, base_url: str, model_name: str):
        self._base_url = base_url
        self._model_name = model_name

    async def _generate(self, prompt: str, system_prompt: str = "You are a helpful business consultant AI.") -> str:
        """Helper to call local LLM API"""
        payload = {
            "model": self._model_name,
            "prompt": f"{system_prompt}\n\nUser: {prompt}\n\nAssistant:",
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_ctx": 4096 
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(self._base_url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
        except httpx.RequestError as e:
            logger.error(f"LLM Connection Failed: {e}")
            return f"Error communicating with LLM: {str(e)}"

    async def generate_clarification_questions(self, idea_text: str) -> List[ClarificationQuestion]:
        prompt = f"""
        Analyze this business idea: "{idea_text}"
        
        Identify 3-5 critical missing pieces of information needed to build a viable business plan.
        Return ONLY a JSON array of objects with keys: "id" (string), "text" (string question).
        
        Example format:
        [
            {{"id": "q1", "text": "Who is the target audience?"}},
            {{"id": "q2", "text": "What is your initial budget?"}}
        ]
        
        Do not include any explanation, markdown formatting, or introductory text. Just the JSON array.
        """
        response = await self._generate(prompt, system_prompt="You are a strict JSON generator. Output only valid JSON.")
        
        import re
        
        try:
            # Regex to find a JSON array pattern
            match = re.search(r'\[.*\]', response, re.DOTALL)
            if match:
                json_str = match.group(0)
                data = json.loads(json_str)
                return [ClarificationQuestion(question_id=item['id'], question_text=item['text']) for item in data]
            else:
                # Fallback: try cleaning standard markdown code blocks if regex failed (unlikely for array)
                cleaned = response.replace("```json", "").replace("```", "").strip()
                data = json.loads(cleaned)
                return [ClarificationQuestion(question_id=item['id'], question_text=item['text']) for item in data]
        except (json.JSONDecodeError, AttributeError, KeyError) as e:
            logger.error(f"Failed to parse LLM response: {response} | Error: {e}")
            # Fallback questions if LLM fails completely
            return [
                ClarificationQuestion(question_id="default_1", question_text="Can you describe your target customer in more detail?"),
                ClarificationQuestion(question_id="default_2", question_text="What is your primary revenue model?")
            ]

    def _sanitize_plan_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure all required fields for BusinessPlan exist, filling defaults if missing."""
        
        # Default structures
        default_market = {
            "market_size": "Unknown",
            "growth_trends": [],
            "competitors": [],
            "opportunities": [],
            "risks": [],
            "relevant_use_cases": []
        }
        
        default_bmc = {
            "value_proposition": [],
            "customer_segments": [],
            "revenue_streams": [],
            "cost_structure": [],
            "key_activities": [],
            "key_resources": [],
            "key_partners": [],
            "channels": [],
            "customer_relationships": []
        }
        
        # Ensure top level fields
        data.setdefault("executive_summary", "Detailed plan generation incomplete.")
        data.setdefault("recommendations", "Review inputs and try again.")
        data.setdefault("assumptions_constraints", [])
        
        # Ensure Nested Models
        if "market_analysis" not in data or not isinstance(data["market_analysis"], dict):
            data["market_analysis"] = default_market
        else:
            # fill missing keys in nested dict
            for k, v in default_market.items():
                data["market_analysis"].setdefault(k, v)
                
        if "business_model" not in data or not isinstance(data["business_model"], dict):
            data["business_model"] = default_bmc
        else:
            for k, v in default_bmc.items():
                data["business_model"].setdefault(k, v)
        
        # KPIs - tricky because it's a list of objects.
        # If it's not a list, make it empty.
        if "kpis" not in data or not isinstance(data["kpis"], list):
            data["kpis"] = []
        else:
            # Filter out invalid KPIs or try to fix them?
            valid_kpis = []
            for item in data["kpis"]:
                if isinstance(item, dict) and "name" in item:
                    # ensure other fields exist
                    item.setdefault("description", "")
                    item.setdefault("formula", "")
                    item.setdefault("importance", "Medium")
                    item.setdefault("frequency", "Monthly")
                    valid_kpis.append(item)
            data["kpis"] = valid_kpis
            
        return data

    async def generate_business_plan(self, idea_text: str, clarifications: Dict[str, str], rag_context: str) -> BusinessPlan:
        
        context_str = "\n".join([f"Q: {q} A: {a}" for q, a in clarifications.items()])
        
        prompt = f"""
        Act as an expert business consultant. Create a detailed Business Plan.
        
        Idea: {idea_text}
        Context: {context_str}
        Market Data: {rag_context}
        
        Output valid JSON with strictly this structure:
        {{
            "executive_summary": "string",
            "market_analysis": {{
                "market_size": "string",
                "growth_trends": ["string", ...],
                "competitors": ["string", ...],
                "opportunities": ["string", ...],
                "risks": ["string", ...],
                "relevant_use_cases": ["string", ...]
            }},
            "business_model": {{
                "value_proposition": ["string"],
                "customer_segments": ["string"],
                "revenue_streams": ["string"],
                "cost_structure": ["string"],
                "key_activities": ["string"],
                "key_resources": ["string"],
                "key_partners": ["string"],
                "channels": ["string"],
                "customer_relationships": ["string"]
            }},
            "kpis": [
                {{
                    "name": "string",
                    "description": "string",
                    "formula": "string",
                    "importance": "string",
                    "frequency": "string"
                }}
            ],
            "assumptions_constraints": ["string"],
            "recommendations": "string"
        }}
        """
        
        response = await self._generate(prompt, system_prompt="You are a JSON-speaking business expert. Do not output markdown, just JSON.")
        
        # Check for connection errors first
        if response.startswith("Error"):
            logger.error(f"LLM Generation Error: {response}")
            # Return a graceful error plan
            return self._create_fallback_plan(error_message=response)

        import re
        
        try:
            # Regex to find the main JSON object
            match = re.search(r'\{.*\}', response, re.DOTALL)
            json_str = match.group(0) if match else response.replace("```json", "").replace("```", "").strip()
            
            if "}" in json_str:
                json_str = json_str[:json_str.rfind("}")+1] # basic trim
            
            if not json_str:
                raise ValueError("Empty JSON string received from LLM")

            data = json.loads(json_str)
            
            # Sanitize to prevent crashes
            clean_data = self._sanitize_plan_data(data)
            
            return BusinessPlan(**clean_data)
                
        except Exception as e:
            logger.error(f"Plan Generation Failed: {e}\nResponse: {response}")
            return self._create_fallback_plan(error_message=f"Parsing Error: {str(e)}")

    def _create_fallback_plan(self, error_message: str) -> BusinessPlan:
        """Create a valid but empty BusinessPlan object to prevent 500 errors."""
        empty_data = self._sanitize_plan_data({})
        empty_data["executive_summary"] = f"Plan generation failed. System Message: {error_message}. Please check your connection to Ollama or try again."
        empty_data["recommendations"] = "Ensure Ollama is running (default: http://localhost:11434)."
        return BusinessPlan(**empty_data)

llm_client = LLMClient()
