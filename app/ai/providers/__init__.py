from app.config import Config


class BaseProvider:
    name = "base"

    def has_config(self):
        """Check if this provider has configuration (API key etc.)"""
        return False

    def is_available(self):
        return self.has_config()

    def analyze(self, prompt, system_prompt=None):
        raise NotImplementedError

    def chat(self, messages):
        raise NotImplementedError


_PROVIDER_NAMES = ("9router",)

_PROVIDER_MAP = {
    "9router": ("app.ai.providers.nine_router_provider", "NineRouterProvider"),
}


def _import_provider(name):
    """Lazy-import and instantiate a provider by name."""
    module_path, cls_name = _PROVIDER_MAP[name]
    import importlib
    mod = importlib.import_module(module_path)
    cls = getattr(mod, cls_name)
    return cls()


def get_provider(provider_name=None):
    if provider_name is None:
        provider_name = Config.AI_PROVIDER
    if provider_name not in _PROVIDER_MAP:
        return None
    return _import_provider(provider_name)


def get_all_providers():
    """Return list of ALL provider instances that have config (no cooldown check)."""
    result = []
    for name in _PROVIDER_NAMES:
        try:
            provider = _import_provider(name)
            if provider.has_config():
                provider.name = name
                result.append(provider)
        except Exception:
            continue
    return result


def get_available_providers():
    providers = []
    for name in _PROVIDER_NAMES:
        provider = get_provider(name)
        if provider and provider.is_available():
            providers.append({"name": name, "model": provider.model})
    return providers


def get_best_provider():
    for name in _PROVIDER_NAMES:
        provider = get_provider(name)
        if provider and provider.is_available():
            return provider
    return None
