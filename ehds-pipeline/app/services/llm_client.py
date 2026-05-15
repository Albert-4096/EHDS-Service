import instructor
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from pydantic import BaseModel
from typing import Type, TypeVar
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger()
T = TypeVar("T", bound=BaseModel)

# Fallback models for OpenRouter. Primary model is settings.llm_model;
# on 429/404 we walk down this list.
OPENROUTER_FALLBACKS = [
    "qwen/qwen3-8b",
    "google/gemma-3-27b-it",
    "mistralai/mistral-small-3.1-24b-instruct",
]


class LLMParseError(Exception):
    """Raised when the LLM fails to extract data conforming to the schema."""
    pass


class LLMClient:
    def __init__(self):
        self.model = settings.llm_model
        self.max_tokens = settings.llm_max_tokens

        if settings.anthropic_api_key:
            self._provider = "anthropic"
            self.client = instructor.from_anthropic(
                AsyncAnthropic(api_key=settings.anthropic_api_key),
                mode=instructor.Mode.ANTHROPIC_JSON,
            )
        elif settings.openrouter_api_key:
            self._provider = "openrouter"
            self.client = instructor.from_openai(
                AsyncOpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=settings.openrouter_api_key,
                ),
                mode=instructor.Mode.JSON,
            )
        else:
            self._provider = "none"
            self.client = None

    def _models_to_try(self) -> list[str]:
        """Primary model first, then fallbacks (deduped, primary removed from list)."""
        others = [m for m in OPENROUTER_FALLBACKS if m != self.model]
        return [self.model] + others

    async def extract_structured_data(
        self,
        text: str,
        schema: Type[T],
        system_prompt: str,
        max_tokens: int | None = None,
    ) -> T:
        if not text.strip():
            return schema.model_construct()

        if self.client is None:
            raise LLMParseError("No LLM API key configured (ANTHROPIC_API_KEY or OPENROUTER_API_KEY).")

        tokens = max_tokens or self.max_tokens

        if self._provider == "anthropic":
            try:
                logger.debug(f"Querying Anthropic ({self.model}), text length: {len(text)}")
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": text}],
                    response_model=schema,
                )
                logger.info("Successfully extracted structured data from LLM.")
                return response
            except Exception as e:
                logger.error(f"LLM Extraction failed: {str(e)}")
                raise LLMParseError(f"Failed to extract structured data: {str(e)}")

        # OpenRouter: try primary model then fallbacks on 429
        last_exc: Exception | None = None
        for model in self._models_to_try():
            try:
                logger.debug(f"Querying OpenRouter ({model}), text length: {len(text)}")
                response = await self.client.chat.completions.create(
                    model=model,
                    response_model=schema,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text},
                    ],
                    max_tokens=tokens,
                    max_retries=1,
                    extra_body={"thinking": {"type": "disabled"}},
                )
                logger.info(f"Successfully extracted structured data via {model}.")
                return response
            except Exception as e:
                err = str(e)
                if "429" in err or "404" in err or "rate" in err.lower() or "no endpoints" in err.lower():
                    logger.warning(f"{model} unavailable ({err[:80]}), trying next fallback.")
                    last_exc = e
                    continue
                # Non-429 error: don't bother trying other models
                logger.error(f"LLM Extraction failed on {model}: {err}")
                raise LLMParseError(f"Failed to extract structured data: {err}")

        raise LLMParseError(
            f"All OpenRouter models rate-limited. Last error: {last_exc}"
        )


llm_client = LLMClient()
