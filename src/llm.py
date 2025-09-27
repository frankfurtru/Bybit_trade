from typing import Sequence, Optional
from openai import OpenAI


class LLMError(Exception):
    def __init__(self, message: str, *, code: str | None = None, status: int | None = None):
        super().__init__(message)
        self.code = code
        self.status = status


class ZaiClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.novita.ai/openai",
        *,
        default_model: str = "openai/gpt-oss-120b",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        self._enabled = bool(api_key)
        self._client = OpenAI(api_key=api_key, base_url=base_url) if api_key else None
        self._default_model = default_model
        self._temperature = float(temperature)
        self._max_tokens = int(max_tokens)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def chat(
        self,
        messages: Sequence[dict],
        model: Optional[str] = None,
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        if not self._client:
            raise RuntimeError("ZaiClient disabled: missing ZAI_API_KEY")
        try:
            completion = self._client.chat.completions.create(
                model=model or self._default_model,
                messages=list(messages),
                temperature=self._temperature if temperature is None else temperature,
                max_tokens=self._max_tokens if max_tokens is None else max_tokens,
            )
            return completion.choices[0].message.content or ""
        except Exception as e:
            # Handle common provider insufficient balance error (e.g., 429/1113)
            msg = str(e)
            lowered = msg.lower()
            if "insufficient balance" in lowered or "no resource package" in lowered or " 429" in msg or "1113" in msg:
                raise LLMError(
                    "Saldo/paket provider LLM tidak cukup. Silakan isi saldo atau aktifkan paket.",
                    code="1113",
                    status=429,
                ) from e
            raise
