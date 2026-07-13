import difflib
import logging
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, meta


LOGGER = logging.getLogger(__name__)


class RootAnchoredEnvironment(Environment):
    """Resolve includes/extends from library root regardless of parent template location."""

    def join_path(self, template: str, parent: str) -> str:
        return template.lstrip("/")


def re_match_version(value: str) -> Optional[str]:
    value = value.strip()
    if not value.startswith("v"):
        return None
    body = value[1:]
    parts = body.split(".")
    if not parts or any(not p.isdigit() for p in parts):
        return None
    return body


class PromptVisualizationService:
    """Backend service for browsing, reviewing, editing, and versioning prompt files."""

    METADATA_BLOCK_PATTERN = re.compile(
        r"^\s*\{#\s*PROMPT_METADATA\n(?P<body>.*?)\n\s*#\}\s*\n?",
        re.DOTALL,
    )
    TITLE_PATTERN = re.compile(r"^title:\s*(.*)$", re.MULTILINE)
    NOTE_PATTERN = re.compile(r"^note:\s*$", re.MULTILINE)

    def __init__(self, library_root: Path):
        self.library_root = Path(library_root).resolve()
        if not self.library_root.exists() or not self.library_root.is_dir():
            raise FileNotFoundError(f"Prompt library root not found: {self.library_root}")
        LOGGER.info("PromptVisualizationService initialized with library_root=%s", self.library_root)

    @staticmethod
    def _version_tuple(version_text: str) -> Tuple[int, ...]:
        match = re_match_version(version_text)
        if not match:
            return tuple()
        return tuple(int(x) for x in match.split("."))

    def _safe_resolve(self, rel_path: str) -> Path:
        rel_path = rel_path.strip().lstrip("/")
        target = (self.library_root / rel_path).resolve()
        if self.library_root not in target.parents and target != self.library_root:
            raise ValueError("Path escapes library root")
        return target

    def _to_rel(self, path: Path) -> str:
        return str(path.resolve().relative_to(self.library_root)).replace("\\", "/")

    def _is_prompt_file(self, path: Path) -> bool:
        return path.is_file() and path.suffix.lower() == ".jinja2"

    def _parse_prompt_metadata(self, content: str) -> Dict[str, str]:
        match = self.METADATA_BLOCK_PATTERN.match(content)
        if not match:
            return {"title": "", "note": "", "has_metadata": False}

        body = match.group("body")
        title_match = self.TITLE_PATTERN.search(body)
        title = title_match.group(1).strip() if title_match else ""

        note = ""
        note_match = self.NOTE_PATTERN.search(body)
        if note_match:
            note_start = note_match.end()
            note = body[note_start:].strip("\n")

        return {"title": title, "note": note, "has_metadata": True}

    def _strip_prompt_metadata(self, content: str) -> str:
        return self.METADATA_BLOCK_PATTERN.sub("", content, count=1)

    @staticmethod
    def _strip_single_leading_newline(content: str) -> str:
        if content.startswith("\r\n"):
            return content[2:]
        if content.startswith("\n") or content.startswith("\r"):
            return content[1:]
        return content

    @staticmethod
    def _build_metadata_block(title: str, note: str) -> str:
        title = (title or "").strip()
        note = (note or "").rstrip("\n")
        note_section = "note:\n"
        if note:
            note_section += note + "\n"
        return "{# PROMPT_METADATA\n" + f"title: {title}\n" + note_section + "#}"

    def upsert_prompt_metadata(self, rel_path: str, title: str, note: str) -> Dict:
        file_path = self._safe_resolve(rel_path)
        if not self._is_prompt_file(file_path):
            raise ValueError("Only .jinja2 files are supported")

        content = file_path.read_text(encoding="utf-8")
        body = self._strip_prompt_metadata(content)
        updated = self._build_metadata_block(title, note) + self._strip_single_leading_newline(body)
        file_path.write_text(updated, encoding="utf-8")

        return {
            "path": self._to_rel(file_path),
            "metadata": self._parse_prompt_metadata(updated),
        }

    def annotate_all_prompts(self, default_title_prefix: str = "TODO", default_note: str = "") -> Dict:
        updated = 0
        skipped = 0
        for prompt_path in sorted(self.library_root.rglob("*.jinja2")):
            content = prompt_path.read_text(encoding="utf-8")
            metadata = self._parse_prompt_metadata(content)
            if metadata.get("has_metadata"):
                skipped += 1
                continue

            auto_title = f"{default_title_prefix}: {prompt_path.stem}"
            body = self._strip_prompt_metadata(content)
            updated_content = self._build_metadata_block(auto_title, default_note) + self._strip_single_leading_newline(body)
            prompt_path.write_text(updated_content, encoding="utf-8")
            updated += 1

        return {"updated": updated, "skipped": skipped}

    def get_version_prompt_summary(self, family_path: str, prompt_file: str) -> Dict:
        family_dir = self._safe_resolve(family_path)
        if not family_dir.exists() or not family_dir.is_dir():
            raise ValueError(f"Prompt family not found: {family_path}")
        if not prompt_file.endswith(".jinja2"):
            raise ValueError("prompt_file must end with .jinja2")

        versions = self.list_versions(family_path)
        rows = []
        for version in versions:
            candidate = family_dir / version / prompt_file
            if not candidate.exists() or not candidate.is_file():
                continue
            content = candidate.read_text(encoding="utf-8")
            md = self._parse_prompt_metadata(content)
            review = self.review_content(content, candidate)
            dt = datetime.fromtimestamp(candidate.stat().st_mtime, tz=timezone.utc).isoformat()
            rows.append(
                {
                    "version": version,
                    "path": self._to_rel(candidate),
                    "title": md.get("title", ""),
                    "has_syntax_error": not review.get("syntax_valid", True),
                    "syntax_error": review.get("syntax_error"),
                    "last_modified": dt,
                }
            )
        return {"family_path": family_path, "prompt_file": prompt_file, "versions": rows}

    def diff_prompt_versions(self, family_path: str, prompt_file: str, from_version: str, to_version: str) -> Dict:
        family_dir = self._safe_resolve(family_path)
        from_path = family_dir / from_version / prompt_file
        to_path = family_dir / to_version / prompt_file
        if not from_path.exists():
            raise ValueError(f"from_version prompt not found: {from_version}/{prompt_file}")
        if not to_path.exists():
            raise ValueError(f"to_version prompt not found: {to_version}/{prompt_file}")

        from_lines = from_path.read_text(encoding="utf-8").splitlines()
        to_lines = to_path.read_text(encoding="utf-8").splitlines()

        diff_lines = []
        for line in difflib.ndiff(from_lines, to_lines):
            prefix = line[:2]
            text = line[2:]
            if prefix == "+ ":
                diff_lines.append({"type": "add", "prefix": "+", "text": text})
            elif prefix == "- ":
                diff_lines.append({"type": "del", "prefix": "-", "text": text})
            elif prefix == "  ":
                diff_lines.append({"type": "ctx", "prefix": " ", "text": text})

        return {
            "family_path": family_path,
            "prompt_file": prompt_file,
            "from_version": from_version,
            "to_version": to_version,
            "diff_lines": diff_lines,
        }

    def build_tree(self) -> Dict:
        start = time.perf_counter()
        stats = {"dirs": 0, "files": 0}

        def walk(node: Path) -> Dict:
            if node.is_dir():
                stats["dirs"] += 1
                children = []
                for child in sorted(node.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                    if child.is_dir() or self._is_prompt_file(child):
                        children.append(walk(child))
                return {
                    "type": "dir",
                    "name": node.name if node != self.library_root else node.name,
                    "path": self._to_rel(node) if node != self.library_root else "",
                    "children": children,
                }
            stats["files"] += 1
            return {
                "type": "file",
                "name": node.name,
                "path": self._to_rel(node),
            }

        tree = walk(self.library_root)
        duration_ms = (time.perf_counter() - start) * 1000
        LOGGER.info(
            "build_tree completed in %.1f ms (dirs=%d, files=%d)",
            duration_ms,
            stats["dirs"],
            stats["files"],
        )
        return tree

    def discover_prompt_tasks(self) -> Dict:
        """Discover all prompt tasks by scanning versioned directories.
        
        A prompt task is identified by {family_path}/{prompt_file}, where:
        - family_path: path to directory containing version subdirectories (e.g., "autolabeling/accuracy")
        - prompt_file: .jinja2 filename that exists in version subdirectories
        
        Returns a dict with tasks list, each containing family_path, prompt_file, and versions.
        """
        start = time.perf_counter()
        tasks_dict = {}  # Key: (family_path, prompt_file), Value: task aggregation data
        
        # Scan all .jinja2 files in the library
        for prompt_path in self.library_root.rglob("*.jinja2"):
            # Check if parent is a version directory
            parent_dir = prompt_path.parent
            if not re_match_version(parent_dir.name):
                continue
            
            version = parent_dir.name
            prompt_file = prompt_path.name
            
            # family_path is the path from library_root to the version directory's parent
            family_dir = parent_dir.parent
            family_rel_path = self._to_rel(family_dir)
            
            # Skip if family_path is empty (shouldn't happen in well-formed libraries)
            if not family_rel_path or family_rel_path == ".":
                continue
            
            key = (family_rel_path, prompt_file)
            if key not in tasks_dict:
                tasks_dict[key] = {
                    "versions": set(),
                    "has_syntax_error": False,
                    "syntax_error_versions": [],
                }
            tasks_dict[key]["versions"].add(version)

            review = self.review_content(prompt_path.read_text(encoding="utf-8"), prompt_path)
            if not review["syntax_valid"]:
                tasks_dict[key]["has_syntax_error"] = True
                tasks_dict[key]["syntax_error_versions"].append({
                    "version": version,
                    "error": review["syntax_error"],
                })
        
        # Convert to sorted list
        tasks = []
        for (family_path, prompt_file), task_info in sorted(tasks_dict.items()):
            sorted_versions = sorted(task_info["versions"], key=self._version_tuple, reverse=True)
            syntax_error_versions = sorted(
                task_info["syntax_error_versions"],
                key=lambda item: self._version_tuple(item["version"]),
                reverse=True,
            )
            tasks.append({
                "family_path": family_path,
                "prompt_file": prompt_file,
                "display_name": f"{family_path}/{prompt_file.replace('.jinja2', '')}",
                "versions": sorted_versions,
                "has_syntax_error": task_info["has_syntax_error"],
                "syntax_error_versions": syntax_error_versions,
            })
        
        duration_ms = (time.perf_counter() - start) * 1000
        LOGGER.info(
            "discover_prompt_tasks completed in %.1f ms (tasks=%d)",
            duration_ms,
            len(tasks),
        )
        
        return {"tasks": tasks}

    def build_tasks_tree(self, tasks: List[Dict]) -> Dict:
        """Build a hierarchical tree structure from a flat list of prompt tasks.
        
        Converts a flat task list into a tree organized by family_path hierarchy.
        Example: "autolabeling/accuracy/adasset_accuracy" becomes:
        {
          "type": "dir",
          "name": "autolabeling",
          "children": [
            {
              "type": "dir",
              "name": "accuracy",
              "children": [
                {
                  "type": "task",
                  "name": "adasset_accuracy",
                  "data": {...task data...}
                }
              ]
            }
          ]
        }
        """
        start = time.perf_counter()
        
        # Build tree structure
        root: Dict = {"type": "dir", "name": "root", "children": []}
        
        for task in tasks:
            family_path = task["family_path"]
            prompt_file = task["prompt_file"]
            
            # Split family_path into parts
            path_parts = family_path.split("/")
            # Extract task name from prompt_file (remove .jinja2)
            task_name = prompt_file.replace(".jinja2", "")
            
            # Navigate/create directory structure
            current_node = root
            for part in path_parts:
                # Find or create child directory
                child = None
                if "children" not in current_node:
                    current_node["children"] = []
                
                for c in current_node["children"]:
                    if c.get("type") == "dir" and c.get("name") == part:
                        child = c
                        break
                
                if child is None:
                    child = {"type": "dir", "name": part, "children": []}
                    current_node["children"].append(child)
                
                current_node = child
            
            # Add task as leaf node
            task_node = {
                "type": "task",
                "name": task_name,
                "data": task,
            }
            if "children" not in current_node:
                current_node["children"] = []
            current_node["children"].append(task_node)
        
        # Sort children at all levels for consistent display
        def sort_tree(node):
            if "children" in node:
                # Directories first, then tasks, both alphabetically
                node["children"].sort(
                    key=lambda x: (x["type"] != "dir", x["name"].lower())
                )
                for child in node["children"]:
                    sort_tree(child)
        
        sort_tree(root)
        
        duration_ms = (time.perf_counter() - start) * 1000
        LOGGER.info(
            "build_tasks_tree completed in %.1f ms",
            duration_ms,
        )
        
        return {"tree": root["children"] if root.get("children") else []}

    def read_prompt(self, rel_path: str) -> Dict:
        start = time.perf_counter()
        file_path = self._safe_resolve(rel_path)
        if not self._is_prompt_file(file_path):
            raise ValueError("Only .jinja2 files are supported")
        content = file_path.read_text(encoding="utf-8")
        result = {
            "path": self._to_rel(file_path),
            "content": content,
            "metadata": self._parse_prompt_metadata(content),
            "review": self.review_content(content, file_path),
        }
        duration_ms = (time.perf_counter() - start) * 1000
        LOGGER.info(
            "read_prompt path=%s size=%dB completed in %.1f ms",
            rel_path,
            len(content.encode("utf-8")),
            duration_ms,
        )
        return result

    def review_content(self, content: str, file_path: Optional[Path] = None) -> Dict:
        start = time.perf_counter()
        env = Environment(autoescape=False)
        syntax_valid = True
        syntax_error = None
        variables: List[str] = []
        try:
            ast = env.parse(content)
            variables = sorted(meta.find_undeclared_variables(ast))
        except Exception as exc:
            syntax_valid = False
            lineno = getattr(exc, "lineno", None)
            msg = str(exc)
            if lineno is not None:
                # Compute char offset of the start of the error line
                lines = content.split("\n")
                char_offset = sum(len(l) + 1 for l in lines[: lineno - 1])
                syntax_error = f"{msg} (line {lineno}, char {char_offset})"
            else:
                syntax_error = msg

        line_count = content.count("\n") + (1 if content else 0)
        char_count = len(content)

        last_modified = None
        if file_path and file_path.exists():
            dt = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
            last_modified = dt.isoformat()

        result = {
            "syntax_valid": syntax_valid,
            "syntax_error": syntax_error,
            "variables": variables,
            "line_count": line_count,
            "char_count": char_count,
            "last_modified": last_modified,
        }
        duration_ms = (time.perf_counter() - start) * 1000
        if duration_ms > 100:
            LOGGER.info(
                "review_content slow path=%s duration=%.1f ms syntax_valid=%s vars=%d",
                self._to_rel(file_path) if file_path else "<memory>",
                duration_ms,
                syntax_valid,
                len(variables),
            )
        return result

    def save_prompt(self, rel_path: str, content: str) -> Dict:
        file_path = self._safe_resolve(rel_path)
        if not self._is_prompt_file(file_path):
            raise ValueError("Only .jinja2 files are supported")

        review = self.review_content(content)
        file_path.write_text(content, encoding="utf-8")

        # Return review with updated file metadata.
        review = self.review_content(content, file_path)
        return {
            "path": self._to_rel(file_path),
            "review": review,
        }

    def render_full_prompt(self, rel_path: str, context: Optional[Dict] = None) -> Dict:
        """Render prompt with file-system loader to resolve extends/includes to final text."""
        start = time.perf_counter()
        file_path = self._safe_resolve(rel_path)
        if not self._is_prompt_file(file_path):
            raise ValueError("Only .jinja2 files are supported")

        if context is None:
            context = {}
        if not isinstance(context, dict):
            raise ValueError("context must be a JSON object")

        # Use finalize to wrap every {{ expression }} output with highlight markers.
        # finalize is called only on expression outputs, never on literal template text,
        # so only actual variable substitutions are marked — not incidental matches.
        _HS = "\x00HS\x00"
        _HE = "\x00HE\x00"

        def _finalize(value):
            return f"{_HS}{value}{_HE}"

        env = RootAnchoredEnvironment(
            loader=ChoiceLoader(
                [
                    FileSystemLoader(str(self.library_root)),
                    FileSystemLoader(str(file_path.parent)),
                ]
            ),
            autoescape=False,
            finalize=_finalize if context else None,
        )
        template = env.get_template(file_path.name)
        rendered_with_markers = template.render(**context)
        # rendered_prompt is the clean final text; rendered_prompt_highlighted keeps the
        # \x00HS\x00 ... \x00HE\x00 markers around variable substitutions for the UI.
        rendered_prompt = rendered_with_markers.replace(_HS, "").replace(_HE, "")
        result = {
            "path": self._to_rel(file_path),
            "context": context,
            "rendered_prompt": rendered_prompt,
            "rendered_prompt_highlighted": rendered_with_markers,
        }
        duration_ms = (time.perf_counter() - start) * 1000
        LOGGER.info("render_full_prompt path=%s completed in %.1f ms", rel_path, duration_ms)
        return result

    def list_versions(self, family_path: str) -> List[str]:
        start = time.perf_counter()
        family_dir = self._safe_resolve(family_path)
        if not family_dir.exists() or not family_dir.is_dir():
            raise ValueError(f"Prompt family not found: {family_path}")

        versions = []
        for child in family_dir.iterdir():
            if child.is_dir() and re_match_version(child.name):
                versions.append(child.name)

        versions.sort(key=lambda v: self._version_tuple(v), reverse=True)
        duration_ms = (time.perf_counter() - start) * 1000
        LOGGER.info("list_versions family=%s found=%d in %.1f ms", family_path, len(versions), duration_ms)
        return versions

    def create_new_version(self, family_path: str, new_version: str, source_version: Optional[str] = None) -> Dict:
        if not re_match_version(new_version):
            raise ValueError("new_version must match pattern like v1 or v1.2")

        family_dir = self._safe_resolve(family_path)
        if not family_dir.exists() or not family_dir.is_dir():
            raise ValueError(f"Prompt family not found: {family_path}")

        versions = self.list_versions(family_path)
        if not versions:
            raise ValueError(f"No version directory found under family: {family_path}")

        if source_version is None:
            source_version = versions[0]
        elif source_version not in versions:
            raise ValueError(f"source_version not found: {source_version}")

        source_dir = family_dir / source_version
        target_dir = family_dir / new_version
        if target_dir.exists():
            raise ValueError(f"Target version already exists: {new_version}")

        shutil.copytree(source_dir, target_dir)

        return {
            "family_path": family_path,
            "source_version": source_version,
            "new_version": new_version,
            "created_path": self._to_rel(target_dir),
        }
