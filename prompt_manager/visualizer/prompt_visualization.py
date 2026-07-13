"""Compatibility module that re-exports visualizer components from split modules."""

from prompt_manager.visualizer.handler import PromptVisualizationHandler
from prompt_manager.visualizer.server import (
    PromptVisualizationServer,
    main,
    run_prompt_visualization,
)
from prompt_manager.visualizer.service import PromptVisualizationService, re_match_version
from prompt_manager.visualizer.ui import HTML_PAGE

__all__ = [
    "HTML_PAGE",
    "PromptVisualizationHandler",
    "PromptVisualizationService",
    "PromptVisualizationServer",
    "run_prompt_visualization",
    "re_match_version",
    "main",
]


if __name__ == "__main__":
    main()
