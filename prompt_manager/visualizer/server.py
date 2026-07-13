import argparse
import logging
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Optional

from prompt_manager.visualizer.handler import PromptVisualizationHandler
from prompt_manager.visualizer.service import PromptVisualizationService


LOGGER = logging.getLogger(__name__)


class PromptVisualizationServer:
    """Wrapper around ThreadingHTTPServer for prompt visualization plugin."""

    def __init__(self, library_root: Path, host: str = "127.0.0.1", port: int = 8010):
        self.service = PromptVisualizationService(library_root)
        self.host = host
        self.port = port
        self.httpd: Optional[ThreadingHTTPServer] = None
        self.thread: Optional[threading.Thread] = None

    def start(self):
        if self.httpd is not None:
            raise RuntimeError("Server is already running")

        handler_cls = type(
            "BoundPromptVisualizationHandler",
            (PromptVisualizationHandler,),
            {"service": self.service},
        )
        self.httpd = ThreadingHTTPServer((self.host, self.port), handler_cls)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None
        if self.thread is not None:
            self.thread.join(timeout=2)
            self.thread = None

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/"


def run_prompt_visualization(library_root: Path, host: str = "127.0.0.1", port: int = 8010):
    """Run the prompt visualization server in foreground mode."""
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )

    LOGGER.info("Starting prompt visualizer host=%s port=%s library_root=%s", host, port, library_root)
    server = PromptVisualizationServer(library_root=library_root, host=host, port=port)
    server.start()
    print(f"Prompt Visualization running at {server.url}")
    print("Press Ctrl+C to stop")
    try:
        while True:
            threading.Event().wait(3600)
    except KeyboardInterrupt:
        server.stop()


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run prompt visualization web UI")
    parser.add_argument("library_root", help="Path to prompt library root")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=8010, help="Port to bind")
    return parser


def main():
    args = _build_arg_parser().parse_args()
    run_prompt_visualization(Path(args.library_root), host=args.host, port=args.port)
