import json
import re
import time
from openai import OpenAI
from app.config import Config
from app.ai.providers import BaseProvider


class NineRouterProvider(BaseProvider):
    name = "9router"
    _cooldown_until = 0

    def __init__(self):
        self.api_key = Config.NINE_ROUTER_API_KEY
        self.model = Config.NINE_ROUTER_MODEL
        self.base_url = Config.NINE_ROUTER_BASE_URL
        self._client = None

    def has_config(self):
        return bool(self.base_url)

    def is_available(self):
        if not self.base_url:
            return False
        if time.time() < type(self)._cooldown_until:
            return False
        return True

    def _get_client(self):
        if self._client is None:
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        return self._client

    def analyze(self, prompt, system_prompt=None):
        if time.time() < type(self)._cooldown_until:
            return None
        # Retry up to 2 times if empty or unparseable
        for attempt in range(3):
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
                    max_tokens=1000,
                )
                content = response.choices[0].message.content or ""
                if not content.strip():
                    continue
                parsed = self._parse_json(content)
                if parsed:
                    return parsed
                # If parse failed, retry
                continue
            except Exception as e:
                self._handle_error(e)
                return None
        return None

    def chat(self, messages):
        if time.time() < type(self)._cooldown_until:
            return None
        for attempt in range(3):
            try:
                client = self._get_client()
                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=1000,
                )
                content = response.choices[0].message.content or ""
                if content.strip():
                    return content
            except Exception as e:
                self._handle_error(e)
                return None
        return None

    def _handle_error(self, e):
        err_str = str(e)
        safe = err_str.split("\n")[0].encode("ascii", "ignore").decode("ascii")
        print(f"  9Router: {safe[:120]}")

    def _parse_json(self, content):
        try:
            # Try direct JSON parse first
            try:
                return json.loads(content.strip())
            except json.JSONDecodeError:
                pass

            # Try to find JSON block
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if not json_match:
                return None
            text = json_match.group()
            
            # Try to parse with various fallbacks
            for attempt in range(3):
                try:
                    return json.loads(text)
                except json.JSONDecodeError as e:
                    if e.pos >= len(text) - 10:
                        text = text[:-10] + "}"
                    else:
                        break
        except Exception:
            pass
        return None
