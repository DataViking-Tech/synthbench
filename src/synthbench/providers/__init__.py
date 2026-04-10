from synthbench.providers.base import Distribution, PersonaSpec, Provider, Response

PROVIDERS: dict[str, str] = {
    "raw-anthropic": "synthbench.providers.raw_anthropic:RawAnthropicProvider",
    "raw-openai": "synthbench.providers.raw_openai:RawOpenAIProvider",
    "raw-gemini": "synthbench.providers.raw_gemini:RawGeminiProvider",
    "openrouter": "synthbench.providers.openrouter:OpenRouterProvider",
    "ollama": "synthbench.providers.ollama:OllamaProvider",
    "synthpanel": "synthbench.providers.synthpanel:SynthPanelProvider",
    "http": "synthbench.providers.http:HttpProvider",
    "random": "synthbench.providers.random_baseline:RandomBaselineProvider",
    "majority": "synthbench.providers.majority_baseline:MajorityBaselineProvider",
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


__all__ = [
    "Distribution",
    "PersonaSpec",
    "Provider",
    "Response",
    "PROVIDERS",
    "load_provider",
]
