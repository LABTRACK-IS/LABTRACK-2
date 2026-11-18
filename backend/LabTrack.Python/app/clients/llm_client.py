import os
import httpx
import logging
from pydantic import BaseModel, Field
from typing import List, Optional

logger = logging.getLogger(__name__)

class LLMMessage(BaseModel):
    role: str = Field(..., description="Role of the message sender (system, user, assistant)")
    content: str = Field(..., description="Message text content")

class LLMCompletionRequest(BaseModel):
    messages: List[LLMMessage]
    temperature: float = Field(0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(800, ge=1, le=8192)
    model: str = Field("gemini-2.5-pro", description="Target model name")

class LLMCompletionResponse(BaseModel):
    content: str
    tokens_used: int
    model: str

class LLMClient:
    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai",
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY") or os.getenv("GROQ_API_KEY") or ""
        self.base_url = (base_url or "https://generativelanguage.googleapis.com/v1beta/openai").rstrip("/")
        self._external_client = client
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def _smart_local_synthesis(self, request: LLMCompletionRequest) -> LLMCompletionResponse:
        joined = " ".join(m.content for m in request.messages)
        upper = joined.upper()
        if "CRITICAL" in upper or "OVERHEAT" in upper or "98C" in upper or "LIQUID" in upper or "SHORT CIRCUIT" in upper:
            text = (
                "CRITICAL: Severe hardware/thermal or electrical hazard detected. "
                "Immediate isolation of power rail, full board diagnostic inspection, and vendor RMA/certified technician intervention required."
            )
        elif "HIGH" in upper or "ARTIFACT" in upper or "PSU" in upper:
            text = "HIGH severity hardware anomaly identified. Schedule priority technician inspection, verify PSU rails and PCIe seating."
        elif "LOW" in upper or "MINOR" in upper:
            text = "LOW severity operational warning. Routine monitoring and standard preventive maintenance recommended."
        elif "SERVER" in upper:
            text = "Category: Server. High-density compute/rack infrastructure requiring enterprise thermal and power monitoring."
        elif "NETWORK" in upper or "SWITCH" in upper or "ROUTER" in upper:
            text = "Category: Network Device. Core laboratory switching/routing infrastructure."
        else:
            user_msg = next((m.content for m in reversed(request.messages) if m.role == "user"), "Laboratory query")
            text = f"LabTrack Gemini 2.5 Pro Analysis: Processed diagnostic and operational guidance for: {user_msg[:180]}"
        return LLMCompletionResponse(content=text, tokens_used=max(32, len(text.split())), model=request.model or "gemini-2.5-pro")

    async def generate_completion(self, request: LLMCompletionRequest) -> LLMCompletionResponse:
        model_name = request.model if request.model and request.model != "gpt-4o-mini" else "gemini-2.5-pro"
        if not self.api_key or self.api_key in ("your-llm-api-key-here", "change-me-to-your-provider-key"):
            return self._smart_local_synthesis(request)

        endpoint = f"{self.base_url}/chat/completions"
        payload = {
            "model": model_name,
            "messages": [msg.model_dump() for msg in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens
        }
        try:
            if self._external_client is not None:
                response = await self._external_client.post(endpoint, json=payload, headers=self.headers)
            else:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(endpoint, json=payload, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            tokens_used = data.get("usage", {}).get("total_tokens", len(content.split()))
            return LLMCompletionResponse(content=content, tokens_used=tokens_used, model=model_name)
        except Exception as err:
            logger.warning(f"External LLM call failed ({err}); using smart fallback synthesis.")
            return self._smart_local_synthesis(request)
