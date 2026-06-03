from app.config import Config


class BaseProvider:
    name = "base"

    def is_available(self):
        return False

    def analyze(self, prompt, system_prompt=None):
        raise NotImplementedError

    def chat(self, messages):
        raise NotImplementedError


def get_provider(provider_name=None):
    if provider_name is None:
        provider_name = Config.AI_PROVIDER

    if provider_name == "openai":
        from app.ai.providers.openai_provider import OpenAIProvider
        return OpenAIProvider()
    elif provider_name == "gemini":
        from app.ai.providers.gemini_provider import GeminiProvider
        return GeminiProvider()
    elif provider_name == "ollama":
        from app.ai.providers.ollama_provider import OllamaProvider
        return OllamaProvider()
    return None


def get_available_providers():
    providers = []
    for name in ("openai", "gemini", "ollama"):
        provider = get_provider(name)
        if provider and provider.is_available():
            providers.append({"name": name, "model": provider.model})
    return providers


def get_best_provider():
    for name in ("openai", "gemini", "ollama"):
        provider = get_provider(name)
        if provider and provider.is_available():
            return provider
    return None
