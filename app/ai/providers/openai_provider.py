import json
import re
from app.config import Config
from app.ai.providers import BaseProvider


class OpenAIProvider(BaseProvider):
    name = "openai"

    def __init__(self):
        self.api_key = Config.OPENAI_API_KEY
        self.model = Config.OPENAI_MODEL
        self._client = None

    def has_config(self):
        return bool(self.api_key)

    def is_available(self):
        return bool(self.api_key)

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def analyze(self, prompt, system_prompt=None):
        try:
            client = self._get_client()
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
            )
            content = response.choices[0].message.content
            return self._parse_json(content)
        except Exception as e:
            print(f"OpenAI error: {e}")
            return None

    def chat(self, messages):
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI chat error: {e}")
            return None

    def _parse_json(self, content):
        try:
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception:
            pass
        return None
