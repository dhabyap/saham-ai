import json
import re
import requests
from app.config import Config
from app.ai.providers import BaseProvider


class OllamaProvider(BaseProvider):
    name = "ollama"

    def __init__(self):
        self.base_url = Config.OLLAMA_BASE_URL
        self.model = Config.OLLAMA_MODEL

    def is_available(self):
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def analyze(self, prompt, system_prompt=None):
        try:
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": full_prompt, "stream": False},
                timeout=60,
            )
            if response.status_code == 200:
                return self._parse_json(response.json().get("response", ""))
            return None
        except Exception as e:
            print(f"Ollama error: {e}")
            return None

    def chat(self, messages):
        try:
            ollama_messages = [
                {"role": m["role"], "content": m["content"]} for m in messages
            ]
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={"model": self.model, "messages": ollama_messages, "stream": False},
                timeout=60,
            )
            if response.status_code == 200:
                return response.json().get("message", {}).get("content", "")
            return None
        except Exception as e:
            print(f"Ollama chat error: {e}")
            return None

    def _parse_json(self, content):
        try:
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception:
            pass
        return None
