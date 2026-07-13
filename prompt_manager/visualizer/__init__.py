"""Public exports for prompt_manager.visualizer with lazy loading."""

from importlib import import_module
from typing import Any, Dict, Tuple

__all__ = [
    "PromptVisualizationService",
    "PromptVisualizationServer",
    "run_prompt_visualization",
]

_EXPORT_MAP: Dict[str, Tuple[str, str]] = {
    "PromptVisualizationService": ("prompt_manager.visualizer.service", "PromptVisualizationService"),
    "PromptVisualizationServer": ("prompt_manager.visualizer.server", "PromptVisualizationServer"),
    "run_prompt_visualization": ("prompt_manager.visualizer.server", "run_prompt_visualization"),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORT_MAP:
        raise AttributeError(f"module 'prompt_manager.visualizer' has no attribute '{name}'")

    module_name, attr_name = _EXPORT_MAP[name]
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals().keys()) | set(__all__))
