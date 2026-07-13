import json
import logging
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict
from urllib.parse import parse_qs, unquote, urlparse

from prompt_manager.visualizer.service import PromptVisualizationService
from prompt_manager.visualizer.ui import get_ui_html


LOGGER = logging.getLogger(__name__)


class PromptVisualizationHandler(BaseHTTPRequestHandler):
    """HTTP handler for prompt visualization APIs and UI."""

    service: PromptVisualizationService = None

    def _log_request_done(self, method: str, path: str, start: float):
        status = getattr(self, "_last_status", "?")
        duration_ms = (time.perf_counter() - start) * 1000
        LOGGER.info("%s %s -> %s in %.1f ms", method, path, status, duration_ms)

    def _json_response(self, payload: Dict, status: int = HTTPStatus.OK):
        data = json.dumps(payload).encode("utf-8")
        self._last_status = int(status)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _html_response(self, html: str, status: int = HTTPStatus.OK):
        data = html.encode("utf-8")
        self._last_status = int(status)
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _file_response(self, file_path: Path, content_type: str = "application/octet-stream"):
        """Serve a static file."""
        if not file_path.exists():
            self._json_response({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
            return
        
        try:
            data = file_path.read_bytes()
            self._last_status = int(HTTPStatus.OK)
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as exc:
            LOGGER.exception("Failed to serve file: %s", file_path)
            self._json_response({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _read_json_body(self) -> Dict:
        content_len = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_len) if content_len > 0 else b"{}"
        return json.loads(raw.decode("utf-8"))

    def do_GET(self):  # noqa: N802
        start = time.perf_counter()
        self._last_status = HTTPStatus.OK
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path == "/" or path == "/index.html":
                self._html_response(get_ui_html())
                return

            # Serve static files (CSS, JS)
            if path.startswith("/static/"):
                static_dir = Path(__file__).parent / "static"
                file_name = path[8:]  # Remove "/static/" prefix
                file_path = (static_dir / file_name).resolve()
                
                # Security check: ensure file is within static directory
                if not str(file_path).startswith(str(static_dir.resolve())):
                    self._json_response({"error": "Access denied"}, status=HTTPStatus.FORBIDDEN)
                    return
                
                # Determine content type
                suffix = file_path.suffix.lower()
                content_types = {
                    ".css": "text/css; charset=utf-8",
                    ".js": "application/javascript; charset=utf-8",
                    ".json": "application/json; charset=utf-8",
                }
                content_type = content_types.get(suffix, "application/octet-stream")
                self._file_response(file_path, content_type)
                return

            if path == "/api/tree":
                self._json_response({"tree": self.service.build_tree()})
                return

            if path == "/api/tasks":
                self._json_response(self.service.discover_prompt_tasks())
                return

            if path == "/api/tasks_tree":
                tasks_data = self.service.discover_prompt_tasks()
                tree_data = self.service.build_tasks_tree(tasks_data["tasks"])
                self._json_response(tree_data)
                return

            if path == "/api/prompt":
                params = parse_qs(parsed.query)
                rel_path = unquote(params.get("path", [""])[0])
                if not rel_path:
                    raise ValueError("Missing query parameter: path")
                self._json_response(self.service.read_prompt(rel_path))
                return

            if path == "/api/review":
                params = parse_qs(parsed.query)
                rel_path = unquote(params.get("path", [""])[0])
                if not rel_path:
                    raise ValueError("Missing query parameter: path")
                prompt_info = self.service.read_prompt(rel_path)
                self._json_response({"path": prompt_info["path"], "review": prompt_info["review"]})
                return

            if path == "/api/version_view":
                params = parse_qs(parsed.query)
                family_path = unquote(params.get("family_path", [""])[0]).strip()
                prompt_file = unquote(params.get("prompt_file", [""])[0]).strip()
                if not family_path or not prompt_file:
                    raise ValueError("family_path and prompt_file are required")
                self._json_response(self.service.get_version_prompt_summary(family_path, prompt_file))
                return

            self._json_response({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
        except Exception as exc:
            LOGGER.exception("GET %s failed", path)
            self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        finally:
            self._log_request_done("GET", path, start)

    def do_POST(self):  # noqa: N802
        start = time.perf_counter()
        self._last_status = HTTPStatus.OK
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path == "/api/save":
                payload = self._read_json_body()
                rel_path = payload.get("path", "")
                content = payload.get("content", "")
                if not rel_path:
                    raise ValueError("Missing body field: path")
                self._json_response(self.service.save_prompt(rel_path, content))
                return

            if path == "/api/create_version":
                payload = self._read_json_body()
                family_path = payload.get("family_path", "").strip()
                source_version = payload.get("source_version", "").strip() or None
                new_version = payload.get("new_version", "").strip()
                if not family_path or not new_version:
                    raise ValueError("family_path and new_version are required")
                result = self.service.create_new_version(
                    family_path=family_path,
                    new_version=new_version,
                    source_version=source_version,
                )
                self._json_response(result)
                return

            if path == "/api/save_metadata":
                payload = self._read_json_body()
                rel_path = payload.get("path", "").strip()
                title = payload.get("title", "")
                note = payload.get("note", "")
                if not rel_path:
                    raise ValueError("path is required")
                result = self.service.upsert_prompt_metadata(rel_path=rel_path, title=title, note=note)
                self._json_response(result)
                return

            if path == "/api/annotate_all":
                payload = self._read_json_body()
                title_prefix = payload.get("default_title_prefix", "TODO")
                default_note = payload.get("default_note", "")
                result = self.service.annotate_all_prompts(
                    default_title_prefix=title_prefix,
                    default_note=default_note,
                )
                self._json_response(result)
                return

            if path == "/api/diff_versions":
                payload = self._read_json_body()
                family_path = payload.get("family_path", "").strip()
                prompt_file = payload.get("prompt_file", "").strip()
                from_version = payload.get("from_version", "").strip()
                to_version = payload.get("to_version", "").strip()
                if not family_path or not prompt_file or not from_version or not to_version:
                    raise ValueError("family_path, prompt_file, from_version, to_version are required")
                result = self.service.diff_prompt_versions(
                    family_path=family_path,
                    prompt_file=prompt_file,
                    from_version=from_version,
                    to_version=to_version,
                )
                self._json_response(result)
                return

            if path == "/api/render_full":
                payload = self._read_json_body()
                rel_path = payload.get("path", "").strip()
                context = payload.get("context", {})
                if not rel_path:
                    raise ValueError("path is required")
                result = self.service.render_full_prompt(rel_path=rel_path, context=context)
                self._json_response(result)
                return

            self._json_response({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
        except Exception as exc:
            LOGGER.exception("POST %s failed", path)
            self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        finally:
            self._log_request_done("POST", path, start)

    def log_message(self, format, *args):  # noqa: A003
        # Keep output concise for plugin usage.
        return
