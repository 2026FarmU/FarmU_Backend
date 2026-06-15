import json
from typing import Any

import httpx

from src.main.config import get_settings


class GeminiUnavailableError(RuntimeError):
    pass


class GeminiClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.gemini_api_key
        self._model = settings.gemini_model
        self._timeout = settings.gemini_timeout_seconds

    @property
    def model(self) -> str:
        return self._model

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    async def generate_json(
        self,
        *,
        system_instruction: str,
        prompt: str,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        if not self._api_key:
            raise GeminiUnavailableError("GEMINI_API_KEY가 설정되지 않았습니다.")

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent"
        )
        payload = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
            },
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    url,
                    params={"key": self._api_key},
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
            text = body["candidates"][0]["content"]["parts"][0]["text"]
            result = json.loads(text)
            if not isinstance(result, dict):
                raise ValueError("Gemini JSON response is not an object")
            return result
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise GeminiUnavailableError("Gemini 응답을 처리할 수 없습니다.") from exc
