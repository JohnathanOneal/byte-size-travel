import os

import openai
from openai import OpenAI


class OpenAIClient:
    def __init__(
        self, api_key: str | None = None, model: str = "gpt-4.1-mini-2025-04-14"
    ) -> None:
        """
        Initialize OpenAI client.

        Args:
            api_key: API key. Falls back to OPENAI_API_KEY env var.
            model: OpenAI model to use.
        """
        # Use provided API key or get from environment
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            msg = (
                "OpenAI API key not found. Either pass api_key parameter or "
                "set OPENAI_API_KEY environment variable"
            )
            raise ValueError(msg)

        self.client = OpenAI(api_key=self.api_key)
        self.model = model

    def analyze(self, system_prompt: str, content: str) -> str:
        """Analyze content using OpenAI API"""
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content},
                ],
            )
            return completion.choices[0].message.content
        except openai.OpenAIError as err:
            msg = f"OpenAI API error: {err!s}"
            raise RuntimeError(msg) from err
