import json
import re
import time
from app.config import Config
from app.ai.providers import BaseProvider


class GeminiProvider(BaseProvider):
    name = "gemini"
    _cooldown_until = 0

    def __init__(self):
        self.api_key = Config.GEMINI_API_KEY
        self.model = Config.GEMINI_MODEL
        self._model = None

    def has_config(self):
        return bool(self.api_key)

    def is_available(self):
        if not self.api_key:
            return False
        if time.time() < self._cooldown_until:
            return False
        return True

    def _get_model(self):
        if self._model is None:
            from google import genai
            self._model = genai.Client(api_key=self.api_key)
        return self._model

    def analyze(self, prompt, system_prompt=None):
        if time.time() < self._cooldown_until:
            return None
        try:
            client = self._get_model()
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = client.models.generate_content(
                model=self.model,
                contents=full_prompt,
            )
            return self._parse_json(response.text)
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "quota" in err_str.lower() or "Quota" in err_str:
                self._cooldown_until = time.time() + 300
                print("  Gemini: quota exceeded, paused 5 min")
            else:
                safe = err_str.split(chr(10))[0].encode("ascii", "ignore").decode("ascii")
                print(f"  Gemini: {safe}")
            return None

    def chat(self, messages):
        if time.time() < self._cooldown_until:
            return None
        try:
            client = self._get_model()
            prompt = "\n".join(
                f"{m['role']}: {m['content']}" for m in messages
            )
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            return response.text
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "quota" in err_str.lower():
                self._cooldown_until = time.time() + 300
                print("  Gemini: quota exceeded, paused 5 min")
            else:
                safe = err_str.split(chr(10))[0].encode("ascii", "ignore").decode("ascii")
                print(f"  Gemini chat: {safe}")
            return None

    def _parse_json(self, content):
        try:
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception:
            pass
        return None
 
