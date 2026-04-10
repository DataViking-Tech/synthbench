from synthbench.providers.base import Provider

PROVIDERS: dict[str, str] = {
    "raw-anthropic": "synthbench.providers.raw_anthropic:RawAnthropicProvider",
    "raw-openai": "synthbench.providers.raw_openai:RawOpenAIProvider",
    "http": "synthbench.providers.http:HttpProvider",
}


def load_provider(name: str, **kwargs) -> Provider:
    """Load a provider by name. Raises KeyError if not found."""
    if name not in PROVIDERS:
        raise KeyError(f"Unknown provider '{name}'. Available: {list(PROVIDERS)}")
    module_path, class_name = PROVIDERS[name].rsplit(":", 1)
    import importlib
    mod = importlib.import_module(module_path)
    cls = getattr(mod, class_name)
    return cls(**kwargs)


__all__ = ["Provider", "PROVIDERS", "load_provider"]
