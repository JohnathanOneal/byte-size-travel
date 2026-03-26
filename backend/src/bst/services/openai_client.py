from typing import TypeVar

import openai
import structlog
from openai import OpenAI
from pydantic import BaseModel

from bst.settings import settings

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class OpenAIClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        key = api_key or settings.openai_api_key
        if not key:
            msg = (
                "OpenAI API key not found. Set OPENAI_API_KEY"
                " in .env or pass api_key parameter."
            )
            raise ValueError(msg)

        self.client = OpenAI(api_key=key)
        self.model = model or settings.openai_model

    def parse(
        self,
        response_model: type[T],
        system_prompt: str,
        content: str,
    ) -> T:
        """Extract structured data from content using OpenAI.

        Uses Structured Outputs to guarantee the response
        matches the Pydantic model schema exactly.
        """
        logger.debug(
            "openai_parse_request",
            model=self.model,
            response_model=response_model.__name__,
        )

        try:
            completion = self.client.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content},
                ],
                response_format=response_model,
            )
        except openai.OpenAIError as err:
            logger.exception("openai_api_error")
            msg = f"OpenAI API error: {err!s}"
            raise RuntimeError(msg) from err

        message = completion.choices[0].message
        if message.refusal:
            logger.warning("openai_refusal", refusal=message.refusal)
            msg = f"OpenAI refused the request: {message.refusal}"
            raise ValueError(msg)

        if message.parsed is None:
            msg = "OpenAI returned no parsed content"
            raise ValueError(msg)

        logger.debug(
            "openai_parse_success",
            model=self.model,
            response_model=response_model.__name__,
        )
        return message.parsed
