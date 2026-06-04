import json
import re
import time
from openai import OpenAI
from app.config import Config
from app.ai.providers import BaseProvider


DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_MODEL_ALIASES = {
    "llama3-70b-8192": DEFAULT_GROQ_MODEL,
    "llama3-8b-8192": "llama-3.1-8b-instant",
}


class GroqProvider(BaseProvider):
    name = "groq"
    _cooldown_until = 0

    def __init__(self):
        self.api_key = Config.GROQ_API_KEY
        self.model = self._normalize_model(Config.GROQ_MODEL)
        self.base_url = "https://api.groq.com/openai/v1"
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

            response = self._create_completion(client, messages)
            if response is None:
                return None
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
            response = self._create_completion(client, messages)
            if response is None:
                return None
            return response.choices[0].message.content
        except Exception as e:
            self._handle_error(e)
            return None

    def _create_completion(self, client, messages):
        try:
            return client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=100,
            )
        except Exception as e:
            if not self._is_decommissioned_model_error(e):
                self._handle_error(e)
                return None

            old_model = self.model
            self.model = DEFAULT_GROQ_MODEL
            print(f"  Groq: model {old_model} is unavailable, switched to {self.model}")
            try:
                return client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=100,
                )
            except Exception as retry_error:
                self._handle_error(retry_error)
                return None

    def _normalize_model(self, model):
        clean_model = (model or "").strip().strip("'\"")
        return GROQ_MODEL_ALIASES.get(clean_model, clean_model or DEFAULT_GROQ_MODEL)

    def _is_decommissioned_model_error(self, e):
        err_str = str(e).lower()
        return "model" in err_str and (
            "decommissioned" in err_str
            or "no longer supported" in err_str
        )

    def _handle_error(self, e):
        err_str = str(e)
        status = ""
        if hasattr(e, "status_code"):
            status = str(e.status_code)
        if "429" in err_str or status == "429":
            type(self)._cooldown_until = time.time() + 300
            print("  Groq: rate limited, paused 5 min")
        elif "402" in err_str or status == "402":
            type(self)._cooldown_until = time.time() + 300
            print("  Groq: insufficient credits, paused 5 min")
        else:
            safe = err_str.split("\n")[0].encode("ascii", "ignore").decode("ascii")
            print(f"  Groq: {safe[:120]}")

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
