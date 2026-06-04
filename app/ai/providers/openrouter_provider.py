import json
import re
import time
from openai import OpenAI
from app.config import Config
from app.ai.providers import BaseProvider


class OpenRouterProvider(BaseProvider):
    name = "openrouter"
    _cooldown_until = 0

    def __init__(self):
        self.api_key = Config.OPENROUTER_API_KEY
        self.model = Config.OPENROUTER_MODEL
        self.base_url = Config.OPENROUTER_BASE_URL
        self.site_url = Config.OPENROUTER_SITE_URL
        self.site_name = Config.OPENROUTER_SITE_NAME
        self._client = None

    def has_config(self):
        return bool(self.api_key)

    def is_available(self):
        if not self.api_key:
            return False
        if time.time() < type(self)._cooldown_until:
            return False
        return True

    def _get_client(self):
        if self._client is None:
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                default_headers={
                    "HTTP-Referer": self.site_url,
                    "X-Title": self.site_name,
                } if self.site_url else {},
            )
        return self._client

    def analyze(self, prompt, system_prompt=None):
        if time.time() < type(self)._cooldown_until:
            return None
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
                max_tokens=30,
            )
            content = response.choices[0].message.content
            parsed = self._parse_json(content)
            return parsed
        except Exception as e:
            self._handle_error(e)
            return None

    def chat(self, messages):
        if time.time() < type(self)._cooldown_until:
            return None
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=30,
            )
            return response.choices[0].message.content
        except Exception as e:
            self._handle_error(e)
            return None

    def _handle_error(self, e):
        err_str = str(e)
        code = ""
        if hasattr(e, "status_code"):
            code = str(e.status_code)
        if "402" in err_str or code == "402":
            type(self)._cooldown_until = time.time() + 300
            print("  OpenRouter: insufficient credits, paused 5 min")
        elif "429" in err_str or code == "429":
            type(self)._cooldown_until = time.time() + 300
            print("  OpenRouter: rate limited, paused 5 min")
        else:
            safe = err_str.split("\n")[0].encode("ascii", "ignore").decode("ascii")
            print(f"  OpenRouter: {safe[:120]}")

    def _parse_json(self, content):
        try:
            json_match = re.search(r"\{.*", content, re.DOTALL)
            if not json_match:
                return None
            text = json_match.group().rstrip()
            while text:
                try:
                    candidate = text + "}" if not text.endswith("}") else text
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    if "\n" not in text:
                        break
                    text = text.rsplit("\n", 1)[0]
        except Exception:
            pass
        return None
