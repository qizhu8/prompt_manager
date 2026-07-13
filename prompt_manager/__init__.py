"""Public package exports for prompt_manager.

Exports are resolved lazily to avoid import-time side effects and speed up startup.
"""

from importlib import import_module
from typing import Any, Dict, Tuple

__all__ = [
    "MyPromptBase",
    "PromptGeneratorLight",
    "PromptMode",
    "CONSTANT_PREFIX",
    "SUPPORTED_PROMPT_TYPES",
    "convert_prompt_to_chat_format",
    "is_prompt_matches_endpoint_mode",
    "TemplateConverter",
    "PromptTemplateRegistry",
    "PromptVisualizationService",
    "PromptVisualizationServer",
    "run_prompt_visualization",
]

_EXPORT_MAP: Dict[str, Tuple[str, str]] = {
    "MyPromptBase": ("prompt_manager.prompt_base", "MyPromptBase"),
    "PromptGeneratorLight": ("prompt_manager.prompt_generator_light", "PromptGeneratorLight"),
    "PromptMode": ("prompt_manager.prompt_generator_light", "PromptMode"),
    "CONSTANT_PREFIX": ("prompt_manager.prompt_generator_light", "CONSTANT_PREFIX"),
    "SUPPORTED_PROMPT_TYPES": ("prompt_manager.prompt_generator_light", "SUPPORTED_PROMPT_TYPES"),
    "convert_prompt_to_chat_format": ("prompt_manager.prompt_util", "convert_prompt_to_chat_format"),
    "is_prompt_matches_endpoint_mode": ("prompt_manager.prompt_util", "is_prompt_matches_endpoint_mode"),
    "TemplateConverter": ("prompt_manager.prompt_converter", "TemplateConverter"),
    "PromptTemplateRegistry": ("prompt_manager.prompt_converter", "PromptTemplateRegistry"),
    "PromptVisualizationService": ("prompt_manager.visualizer.prompt_visualization", "PromptVisualizationService"),
    "PromptVisualizationServer": ("prompt_manager.visualizer.prompt_visualization", "PromptVisualizationServer"),
    "run_prompt_visualization": ("prompt_manager.visualizer.prompt_visualization", "run_prompt_visualization"),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORT_MAP:
        raise AttributeError(f"module 'prompt_manager' has no attribute '{name}'")

    module_name, attr_name = _EXPORT_MAP[name]
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals().keys()) | set(__all__))
