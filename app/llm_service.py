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

    _base_url = "https://router.huggingface.co/v1/chat/completions"
    _model_name = "Qwen/Qwen2.5-Coder-32B-Instruct"
    _api_token = os.getenv("HF_TOKEN")

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            logger.info("LLMClient Singleton Initialized (HuggingFace Router)")
        return cls._instance

    def set_config(
        self,
        base_url: str,
        model_name: str,
        api_token: Optional[str] = None,
    ):
        self._base_url = base_url
        self._model_name = model_name
        if api_token:
            self._api_token = api_token

    # ------------------------------------------------------------------
    # 🔹 LOW LEVEL GENERATION
    # ------------------------------------------------------------------
    async def _generate(
        self,
        prompt: str,
        system_prompt: str,
    ) -> str:
        """
        Call HuggingFace Router API (Chat-style models)
        """

        if not self._api_token:
            return "Error: HF_TOKEN environment variable is not set."

        headers = {
            "Authorization": f"Bearer {self._api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload = {
            "model": self._model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 1500,
            "temperature": 0.7,
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    self._base_url,
                    headers=headers,
                    json=payload,
                )

                if response.status_code == 503:
                    return "Error: Model is loading on Hugging Face. Try again shortly."

                response.raise_for_status()
                data = response.json()

                # OpenAI-compatible response
                if "choices" in data and data["choices"]:
                    return data["choices"][0]["message"]["content"].strip()

                # Fallback
                if "error" in data:
                    return f"Error from HF: {data['error']}"

                return ""

        except httpx.RequestError as e:
            logger.error(f"LLM Connection Failed: {e}")
            return f"Error communicating with LLM: {e}"

        except httpx.HTTPStatusError as e:
            logger.error(f"LLM API Error: {e.response.text}")
            return f"Error communicating with LLM: {e.response.status_code} {e.response.text}"

    # ------------------------------------------------------------------
    # 🔹 UTIL: SAFE JSON EXTRACTION
    # ------------------------------------------------------------------
    def _extract_json_object(self, text: str) -> Dict[str, Any]:
        start = text.find("{")
        if start == -1:
            raise ValueError("No JSON object found in response")

        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(text[start : i + 1])

        raise ValueError("Unbalanced JSON braces")

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
Create a detailed business plan in JSON.

Idea:
{idea_text}

Clarifications:
{context_str}

Market Data:
{rag_context}

Return ONLY valid JSON.
"""

        response = await self._generate(
            prompt,
            system_prompt="You are a JSON-speaking business expert.",
        )

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
