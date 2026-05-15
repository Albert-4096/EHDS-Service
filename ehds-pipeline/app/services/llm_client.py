import instructor
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from pydantic import BaseModel
from typing import Type, TypeVar
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger()
T = TypeVar("T", bound=BaseModel)


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

        try:
            logger.debug(
                f"Querying LLM ({self._provider}, {self.model}) with text length: {len(text)}"
            )
            if self._provider == "anthropic":
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": text}],
                    response_model=schema,
                )
            else:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    response_model=schema,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text},
                    ],
                    max_tokens=tokens,
                )
            logger.info("Successfully extracted structured data from LLM.")
            return response
        except Exception as e:
            logger.error(f"LLM Extraction failed: {str(e)}")
            raise LLMParseError(f"Failed to extract structured data: {str(e)}")


llm_client = LLMClient()
