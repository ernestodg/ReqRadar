from pydantic import BaseModel, Field
import httpx


class ImpactAIResult(BaseModel):
    is_impacted: bool
    severity: str = Field(pattern="^(HIGH|MEDIUM|LOW)$")
    confidence: float = Field(ge=0, le=1)
    reason: str
    relationship_type: str


class AIProvider:
    async def analyze_impact(self, payload: dict) -> ImpactAIResult | None:
        raise NotImplementedError

    async def healthcheck(self) -> bool:
        return False


class NullAIProvider(AIProvider):
    async def analyze_impact(self, payload: dict) -> ImpactAIResult | None:
        return None


class OpenAIProvider(NullAIProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    async def analyze_impact(self, payload: dict) -> ImpactAIResult | None:
        if not self.api_key or not self.model:
            return None
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": f"Return impact JSON only for: {payload}"}],
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return ImpactAIResult.model_validate_json(content)

    async def healthcheck(self) -> bool:
        return bool(self.api_key and self.model)


class OllamaProvider(NullAIProvider):
    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def analyze_impact(self, payload: dict) -> ImpactAIResult | None:
        if not self.model:
            return None
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": f"Return impact JSON only for: {payload}", "stream": False},
            )
            response.raise_for_status()
        return ImpactAIResult.model_validate_json(response.json()["response"])

    async def healthcheck(self) -> bool:
        if not self.model:
            return False
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except httpx.HTTPError:
            return False


def provider_from_settings(settings) -> AIProvider:
    if settings.ai_provider == "openai":
        return OpenAIProvider(settings.openai_api_key, settings.ai_model)
    if settings.ai_provider == "ollama":
        return OllamaProvider(settings.ollama_base_url, settings.ai_model)
    return NullAIProvider()
