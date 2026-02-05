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

    async def generate_business_plan(self, idea_text: str, clarifications: Dict[str, str], rag_context: str) -> BusinessPlan:
        
        context_str = "\n".join([f"Q: {q} A: {a}" for q, a in clarifications.items()])
        
        prompt = f"""
        Act as an expert business consultant. Create a detailed Business Plan for the following idea:
        
        Idea: {idea_text}
        Additional Context: {context_str}
        
        Market Research Insights (incorporate these):
        {rag_context}
        
        Output valid JSON with the following structure exactly:
        {{
            "executive_summary": "...",
            "market_analysis": {{
                "market_size": "...",
                "growth_trends": ["..."],
                "competitors": ["..."],
                "opportunities": ["..."],
                "risks": ["..."],
                "relevant_use_cases": ["..."]
            }},
            "business_model": {{
                "value_proposition": ["..."],
                "customer_segments": ["..."],
                "revenue_streams": ["..."],
                "cost_structure": ["..."],
                "key_activities": ["..."],
                "key_resources": ["..."],
                "key_partners": ["..."],
                "channels": ["..."],
                "customer_relationships": ["..."]
            }},
            "kpis": [
                {{
                    "name": "...",
                    "description": "...",
                    "formula": "...",
                    "importance": "...",
                    "frequency": "..."
                }}
            ],
            "assumptions_constraints": ["..."],
            "recommendations": "..."
        }}
        """
        
        response = await self._generate(prompt, system_prompt="You are a JSON-speaking business expert. Do not output markdown, just JSON.")
        
        import re
        
        try:
            # Regex to find the main JSON object
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                json_str = match.group(0)
                # Attempt to fix common Trailing comma issues if simple load fails? 
                # For now, just trust the match is reasonably good or use a tolerant parser if available.
                data = json.loads(json_str)
                return BusinessPlan(**data)
            else:
                # Fallback clean
                cleaned = response.replace("```json", "").replace("```", "").strip()
                if "}" in cleaned:
                    cleaned = cleaned[:cleaned.rfind("}")+1]
                data = json.loads(cleaned)
                return BusinessPlan(**data)
                
        except Exception as e:
            logger.error(f"Plan Generation Failed: {e}\nResponse: {response}")
            raise e

llm_client = LLMClient()
