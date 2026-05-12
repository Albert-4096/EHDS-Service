import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel
from typing import Type, TypeVar, Any
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger()
T = TypeVar('T', bound=BaseModel)

class LLMParseError(Exception):
    """Raised when the LLM fails to extract data conforming to the schema."""
    pass

class LLMClient:
    def __init__(self):
        # OpenRouter uses the OpenAI client format
        self.client = instructor.from_openai(
            AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.openrouter_api_key,
            ),
            mode=instructor.Mode.JSON
        )
        self.model = "google/gemma-4-26b-a4b-it:free"

    async def extract_structured_data(self, text: str, schema: Type[T], system_prompt: str) -> T:
        """
        Extracts structured data from raw text using the provided Pydantic schema.
        """
        if not text.strip():
            # Return an empty/default instance if possible, though Pydantic doesn't always allow empty args
            # We'll rely on the schema to have defaults, or the caller to handle empty text before calling
            pass

        try:
            logger.debug(f"Querying OpenRouter LLM ({self.model}) with text length: {len(text)}")
            response = await self.client.chat.completions.create(
                model=self.model,
                response_model=schema,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                max_tokens=4000,
            )
            logger.info("Successfully extracted structured data from LLM.")
            return response
        except Exception as e:
            # instructor raises ValidationError or OpenAIError
            logger.error(f"LLM Extraction failed: {str(e)}")
            raise LLMParseError(f"Failed to extract structured data: {str(e)}")

# Singleton instance
llm_client = LLMClient()
