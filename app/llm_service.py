import httpx
import json
import logging
import os
import re
from typing import List, Dict, Any, Optional

from app.schemas import (
    ClarificationQuestion,
    BusinessPlan,
)

logger = logging.getLogger(__name__)


class LLMClient:
    _instance = None
    _pipeline = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            logger.info("Initializing Local LLM Pipeline...")
            from transformers import pipeline
            # Use the requested model
            cls._pipeline = pipeline(
                "text-generation",
                model="Qwen/Qwen3-4B-Instruct-2507",
                device_map="auto",
                trust_remote_code=True
            )
            logger.info("LLMClient Singleton Initialized (Local Pipeline)")
        return cls._instance

    # ------------------------------------------------------------------
    # 🔹 LOW LEVEL GENERATION
    # ------------------------------------------------------------------
    async def _generate(
        self,
        prompt: str,
        system_prompt: str,
    ) -> str:
        """
        Call Local Transformers Pipeline
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        
        # Apply chat template
        prompt_text = self._pipeline.tokenizer.apply_chat_template(
            messages, 
            tokenize=False, 
            add_generation_prompt=True
        )

        outputs = self._pipeline(
            prompt_text,
            max_new_tokens=4096, # Increased to prevent truncation
            do_sample=True,
            temperature=0.7,
            return_full_text=False
        )
        
        return outputs[0]["generated_text"]

    # ------------------------------------------------------------------
    # 🔹 UTIL: SAFE JSON EXTRACTION
    # ------------------------------------------------------------------
    def _extract_json_object(self, text: str) -> Dict[str, Any]:
        """
        Extracts the first valid JSON object from the text using regex.
        Matches balanced braces handled by json parser, or finds the outer block.
        """
        # Try finding the largest outer block first
        # Regex to find everything between the first { and the last }
        match = re.search(r'\{.*\}', text, re.DOTALL)
        
        if match:
            json_str = match.group(0)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # If the largest block fails, it might include extra text at the end that confuses it 
                # or be truncated.
                pass
        
        # Fallback: finding the first {
        start = text.find("{")
        if start == -1:
            # If no brace, maybe it's just the key-values? (Unlikely)
            raise ValueError("No JSON object found")
            
        # Attempt to parse from start, letting json.loads complain if truncated.
        # But json.loads(text[start:]) fails if there is trailing text.
        # We try to use the 'raw_decode' from Decoder which can stop after valid json.
        try:
            obj, idx = json.JSONDecoder().raw_decode(text[start:])
            return obj
        except json.JSONDecodeError as e:
            raise ValueError(f"Unbalanced or Invalid JSON: {e}")

    # ------------------------------------------------------------------
    # 🔹 CLARIFICATION QUESTIONS
    # ------------------------------------------------------------------
    async def generate_clarification_questions(
        self,
        idea_text: str,
    ) -> List[ClarificationQuestion]:

        prompt = f"""
Analyze this business idea:
"{idea_text}"

Identify 3–5 missing critical details.

Return ONLY a JSON array:
[
  {{ "id": "q1", "text": "question" }}
]
"""

        response = await self._generate(
            prompt,
            system_prompt="You are a strict JSON generator. Output only valid JSON.",
        )

        try:
            match = re.search(r"\[.*\]", response, re.DOTALL)
            if not match:
                raise ValueError("No JSON array found")

            data = json.loads(match.group(0))

            return [
                ClarificationQuestion(
                    question_id=item["id"],
                    question_text=item["text"],
                )
                for item in data
            ]

        except Exception as e:
            logger.error(f"Clarification parse failed: {e} | {response}")
            return [
                ClarificationQuestion(
                    question_id="default_1",
                    question_text="Who is your target customer?",
                ),
                ClarificationQuestion(
                    question_id="default_2",
                    question_text="What is your revenue model?",
                ),
            ]

    # ------------------------------------------------------------------
    # 🔹 SANITIZATION
    # ------------------------------------------------------------------
    def _sanitize_plan_data(self, data: Dict[str, Any]) -> Dict[str, Any]:

        data.setdefault("executive_summary", "Plan generation incomplete.")
        data.setdefault("recommendations", "Please retry with more details.")
        data.setdefault("assumptions_constraints", [])

        data.setdefault(
            "market_analysis",
            {
                "market_size": "Unknown",
                "growth_trends": [],
                "competitors": [],
                "opportunities": [],
                "risks": [],
                "relevant_use_cases": [],
            },
        )

        data.setdefault(
            "business_model",
            {
                "value_proposition": [],
                "customer_segments": [],
                "revenue_streams": [],
                "cost_structure": [],
                "key_activities": [],
                "key_resources": [],
                "key_partners": [],
                "channels": [],
                "customer_relationships": [],
            },
        )

        if not isinstance(data.get("kpis"), list):
            data["kpis"] = []

        return data

    # ------------------------------------------------------------------
    # 🔹 BUSINESS PLAN
    # ------------------------------------------------------------------
    async def generate_business_plan(
        self,
        idea_text: str,
        clarifications: Dict[str, str],
        rag_context: str,
    ) -> BusinessPlan:

        context_str = "\n".join(
            f"Q: {q}\nA: {a}" for q, a in clarifications.items()
        )

        prompt = f"""
        You are a business expert. Generate a Business Plan for the idea: "{idea_text}" in JSON format.
        
        Context: {context_str}
        Market Data: {rag_context}
        
        Strictly follow this JSON structure. Do not output markdown, just the JSON object:
        {{
            "executive_summary": "A brief summary of the business...",
            "market_analysis": {{
                "market_size": "Estimate of market value...",
                "growth_trends": ["trend 1", "trend 2"],
                "competitors": ["comp 1", "comp 2"],
                "opportunities": ["opp 1"],
                "risks": ["risk 1"],
                "relevant_use_cases": ["case 1"]
            }},
            "business_model": {{
                "value_proposition": ["prop 1"],
                "customer_segments": ["seg 1"],
                "revenue_streams": ["stream 1"],
                "cost_structure": ["cost 1"],
                "key_activities": ["act 1"],
                "key_resources": ["res 1"],
                "key_partners": ["partner 1"],
                "channels": ["channel 1"],
                "customer_relationships": ["rel 1"]
            }},
            "kpis": [
                {{
                    "name": "Revenue Growth",
                    "description": "Monthly growth rate",
                    "formula": "(Rev - LastRev)/LastRev",
                    "importance": "High",
                    "frequency": "Monthly"
                }}
            ],
            "assumptions_constraints": ["assume stable economy"],
            "recommendations": "Start small and validate."
        }}
        """

        response = await self._generate(
            prompt,
            system_prompt="You are a JSON-speaking business expert.",
        )
        
        logger.info(f"--------------------------------------------------")
        logger.info(f"Raw LLM Response (First 500 chars): {response[:500]}...")
        logger.info(f"--------------------------------------------------")

        if response.startswith("Error"):
            return self._create_fallback_plan(response)

        try:
            data = self._extract_json_object(response)
            clean = self._sanitize_plan_data(data)
            return BusinessPlan(**clean)

        except Exception as e:
            logger.error(f"Plan parsing failed: {e}\n{response}")
            return self._create_fallback_plan(str(e))

    # ------------------------------------------------------------------
    # 🔹 FALLBACK
    # ------------------------------------------------------------------
    def _create_fallback_plan(self, error_message: str) -> BusinessPlan:
        data = self._sanitize_plan_data({})
        data["executive_summary"] = (
            f"Plan generation failed. System Message: {error_message}"
        )
        data["recommendations"] = (
            "Check HF_TOKEN, model availability, and request format."
        )
        return BusinessPlan(**data)


llm_client = LLMClient()
