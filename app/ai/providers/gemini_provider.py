import json
import re
from app.config import Config
from app.ai.providers import BaseProvider


class GeminiProvider(BaseProvider):
    name = "gemini"

    def __init__(self):
        self.api_key = Config.GEMINI_API_KEY
        self.model = Config.GEMINI_MODEL
        self._model = None

    def is_available(self):
        return bool(self.api_key)

    def _get_model(self):
        if self._model is None:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel(self.model)
        return self._model

    def analyze(self, prompt, system_prompt=None):
        try:
            model = self._get_model()
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = model.generate_content(full_prompt)
            return self._parse_json(response.text)
        except Exception as e:
            print(f"Gemini error: {e}")
            return None

    def chat(self, messages):
        try:
            model = self._get_model()
            prompt = "\n".join(
                f"{m['role']}: {m['content']}" for m in messages
            )
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Gemini chat error: {e}")
            return None

    def _parse_json(self, content):
        try:
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception:
            pass
        return None
