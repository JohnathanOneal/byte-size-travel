import os
from openai import OpenAI
from typing import Optional

class OpenAIClient:
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize OpenAI client with API key from parameter or environment variable
        
        Args:
            api_key: Optional API key. If not provided, will look for OPENAI_API_KEY env var
            model: OpenAI model to use
        """
        # Use provided API key or get from environment
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not found. Either pass api_key parameter or "
                "set OPENAI_API_KEY environment variable"
            )
            
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        
    def analyze(self, system_prompt: str, content: str) -> str:
        """Analyze content using OpenAI API"""
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content}
                ]
            )
            return completion.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")