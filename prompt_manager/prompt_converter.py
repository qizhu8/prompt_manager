"""
Conversion utilities for migrating templates from CDEX and LangChain formats to Jinja2.

Supported conversions:
- CDEX (#placeholder#) -> Jinja2 ({{ placeholder }})
- LangChain ({variable}) -> Jinja2 ({{ variable }})
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

from jinja2 import Environment


class TemplateConverter:
    """Converts templates between different formats."""

    # Regex patterns for identifying placeholders
    CDEX_PATTERN = re.compile(r"#([a-zA-Z_][a-zA-Z0-9_]*)#")
    LANGCHAIN_PATTERN = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")
    JINJA2_PATTERN = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")
    LITERAL_JINJA_BLOCK_PATTERN = re.compile(r"\{\{.*?\}\}", re.DOTALL)

    @staticmethod
    def _protect_literal_jinja_blocks(text: str) -> Tuple[str, List[str]]:
        """Replace literal double-brace blocks with sentinels during conversion.

        Source formats like CDEX or LangChain may contain literal ``{{...}}`` text
        in examples or JSON snippets. If carried directly into a Jinja2 template,
        Jinja will try to parse them as expressions. Protect them before placeholder
        conversion, then restore them as raw blocks afterwards.
        """
        protected_blocks: List[str] = []

        def replace_block(match: re.Match) -> str:
            index = len(protected_blocks)
            protected_blocks.append(match.group(0))
            return f"__PM_LITERAL_JINJA_BLOCK_{index}__"

        return TemplateConverter.LITERAL_JINJA_BLOCK_PATTERN.sub(replace_block, text), protected_blocks

    @staticmethod
    def _restore_literal_jinja_blocks(text: str, protected_blocks: List[str]) -> str:
        """Restore protected literal double-brace blocks as raw Jinja text."""
        restored = text
        for index, block in enumerate(protected_blocks):
            restored = restored.replace(
                f"__PM_LITERAL_JINJA_BLOCK_{index}__",
                f"{{% raw %}}{block}{{% endraw %}}",
            )
        return restored

    @staticmethod
    def _detect_source_format(file_path: Path) -> Optional[str]:
        """Detect source template format from extension."""
        ext = file_path.suffix.lower()
        if ext == ".txt":
            return "cdex"
        if ext == ".json":
            return "langchain"
        if ext == ".jinja2":
            return "jinja2"
        return None

    @staticmethod
    def _normalized_relative_path(source_root: Path, source_file: Path) -> Path:
        """
        Build normalized path under output root.

        If the first path segment is a format bucket (cdex/langchain/jinja2),
        remove it to produce a clean hierarchy.
        """
        rel = source_file.relative_to(source_root)
        parts = rel.parts
        if parts and parts[0].lower() in {"cdex", "langchain", "jinja2"}:
            rel = Path(*parts[1:])
        return rel

    @staticmethod
    def extract_cdex_variables(text: str) -> Set[str]:
        """
        Extract variable names from CDEX format (#placeholder#).

        Args:
            text: Template text in CDEX format

        Returns:
            Set of variable names found in the template
        """
        return set(TemplateConverter.CDEX_PATTERN.findall(text))

    @staticmethod
    def extract_langchain_variables(text: str) -> Set[str]:
        """
        Extract variable names from LangChain format ({variable}).

        Args:
            text: Template text in LangChain format

        Returns:
            Set of variable names found in the template
        """
        return set(TemplateConverter.LANGCHAIN_PATTERN.findall(text))

    @staticmethod
    def extract_jinja2_variables(text: str) -> Set[str]:
        """
        Extract variable names from Jinja2 format ({{ variable }}).

        Args:
            text: Template text in Jinja2 format

        Returns:
            Set of variable names found in the template
        """
        return set(TemplateConverter.JINJA2_PATTERN.findall(text))

    @staticmethod
    def cdex_to_jinja2(cdex_text: str) -> str:
        """
        Convert CDEX format (#placeholder#) to Jinja2 format ({{ placeholder }}).

        Args:
            cdex_text: Template text in CDEX format

        Returns:
            Template text in Jinja2 format
        """
        protected_text, protected_blocks = TemplateConverter._protect_literal_jinja_blocks(cdex_text)

        def replace_cdex(match):
            var_name = match.group(1)
            return f"{{{{ {var_name} }}}}"

        converted = TemplateConverter.CDEX_PATTERN.sub(replace_cdex, protected_text)
        return TemplateConverter._restore_literal_jinja_blocks(converted, protected_blocks)

    @staticmethod
    def langchain_to_jinja2(langchain_text: str) -> str:
        """
        Convert LangChain format ({variable}) to Jinja2 format ({{ variable }}).

        Args:
            langchain_text: Template text in LangChain format

        Returns:
            Template text in Jinja2 format
        """
        protected_text, protected_blocks = TemplateConverter._protect_literal_jinja_blocks(langchain_text)

        def replace_langchain(match):
            var_name = match.group(1)
            return f"{{{{ {var_name} }}}}"

        converted = TemplateConverter.LANGCHAIN_PATTERN.sub(replace_langchain, protected_text)
        return TemplateConverter._restore_literal_jinja_blocks(converted, protected_blocks)

    @staticmethod
    def cdex_file_to_jinja2(
        cdex_file_path: Path, output_file_path: Optional[Path] = None
    ) -> Tuple[str, Path]:
        """
        Convert a CDEX template file (.txt) to Jinja2 format (.jinja2).

        Args:
            cdex_file_path: Path to CDEX template file
            output_file_path: Path for output file (default: replace .txt with .jinja2)

        Returns:
            Tuple of (converted_content, output_path)
        """
        cdex_file_path = Path(cdex_file_path)

        if not cdex_file_path.exists():
            raise FileNotFoundError(f"CDEX file not found: {cdex_file_path}")

        # Read CDEX file
        cdex_content = cdex_file_path.read_text(encoding="utf-8")

        # Convert
        jinja2_content = TemplateConverter.cdex_to_jinja2(cdex_content)

        # Determine output path
        if output_file_path is None:
            output_file_path = cdex_file_path.with_suffix(".jinja2")
        else:
            output_file_path = Path(output_file_path)

        # Write output
        output_file_path.parent.mkdir(parents=True, exist_ok=True)
        output_file_path.write_text(jinja2_content, encoding="utf-8")

        return jinja2_content, output_file_path

    @staticmethod
    def langchain_json_to_jinja2(
        langchain_json_path: Path, output_file_path: Optional[Path] = None
    ) -> Tuple[str, Path, Dict]:
        """
        Convert a LangChain template file (.json) to Jinja2 format (.jinja2).
        Also returns extracted metadata.

        Args:
            langchain_json_path: Path to LangChain template JSON file
            output_file_path: Path for output file (default: replace .json with .jinja2)

        Returns:
            Tuple of (converted_content, output_path, metadata_dict)
        """
        langchain_json_path = Path(langchain_json_path)

        if not langchain_json_path.exists():
            raise FileNotFoundError(f"LangChain JSON file not found: {langchain_json_path}")

        # Read JSON
        with open(langchain_json_path, "r", encoding="utf-8") as f:
            langchain_data = json.load(f)

        # Extract template and metadata
        template = langchain_data.get("template", "")
        metadata = {
            "input_variables": langchain_data.get("input_variables", []),
            "optional_variables": langchain_data.get("optional_variables", []),
            "output_parser": langchain_data.get("output_parser"),
            "partial_variables": langchain_data.get("partial_variables", {}),
            "metadata": langchain_data.get("metadata"),
            "tags": langchain_data.get("tags"),
            "name": langchain_data.get("name"),
            "template_format": langchain_data.get("template_format", "f-string"),
        }

        # Convert template
        jinja2_content = TemplateConverter.langchain_to_jinja2(template)

        # Determine output path
        if output_file_path is None:
            output_file_path = langchain_json_path.with_suffix(".jinja2")
        else:
            output_file_path = Path(output_file_path)

        # Write output
        output_file_path.parent.mkdir(parents=True, exist_ok=True)
        output_file_path.write_text(jinja2_content, encoding="utf-8")

        return jinja2_content, output_file_path, metadata

    @staticmethod
    def langchain_metadata_to_yaml(metadata: Dict) -> str:
        """
        Convert LangChain metadata to YAML format for documentation.

        Args:
            metadata: LangChain metadata dictionary

        Returns:
            YAML formatted string
        """
        yaml_lines = [
            "---",
            f"# Converted from LangChain template",
            f"# Original input_variables: {metadata.get('input_variables', [])}",
        ]

        if metadata.get("name"):
            yaml_lines.append(f"# Name: {metadata['name']}")

        if metadata.get("template_format"):
            yaml_lines.append(f"# Template format: {metadata['template_format']}")

        if metadata.get("tags"):
            yaml_lines.append(f"# Tags: {metadata['tags']}")

        if metadata.get("optional_variables"):
            yaml_lines.append(
                f"# Optional variables: {metadata['optional_variables']}"
            )

        if metadata.get("partial_variables"):
            yaml_lines.append(f"# Partial variables: {metadata['partial_variables']}")

        yaml_lines.append("---")
        return "\n".join(yaml_lines)

    @staticmethod
    def batch_convert_cdex_files(
        source_dir: Path, output_dir: Optional[Path] = None, overwrite: bool = False
    ) -> List[Tuple[Path, Path]]:
        """
        Convert all CDEX (.txt) files in a directory to Jinja2 format.

        Args:
            source_dir: Directory containing CDEX files
            output_dir: Output directory (default: same as source)
            overwrite: Whether to overwrite existing .jinja2 files

        Returns:
            List of tuples (source_path, output_path)
        """
        source_dir = Path(source_dir)
        output_dir = Path(output_dir) if output_dir else source_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        converted_files = []

        for txt_file in source_dir.rglob("*.txt"):
            output_file = output_dir / txt_file.relative_to(source_dir).with_suffix(
                ".jinja2"
            )

            if output_file.exists() and not overwrite:
                continue

            try:
                TemplateConverter.cdex_file_to_jinja2(txt_file, output_file)
                converted_files.append((txt_file, output_file))
            except Exception as e:
                print(f"Error converting {txt_file}: {e}")

        return converted_files

    @staticmethod
    def batch_convert_langchain_files(
        source_dir: Path, output_dir: Optional[Path] = None, overwrite: bool = False
    ) -> List[Tuple[Path, Path, Dict]]:
        """
        Convert all LangChain (.json) files in a directory to Jinja2 format.

        Args:
            source_dir: Directory containing LangChain JSON files
            output_dir: Output directory (default: same as source)
            overwrite: Whether to overwrite existing .jinja2 files

        Returns:
            List of tuples (source_path, output_path, metadata)
        """
        source_dir = Path(source_dir)
        output_dir = Path(output_dir) if output_dir else source_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        converted_files = []

        for json_file in source_dir.rglob("*.json"):
            output_file = output_dir / json_file.relative_to(source_dir).with_suffix(
                ".jinja2"
            )

            if output_file.exists() and not overwrite:
                continue

            try:
                _, output_path, metadata = TemplateConverter.langchain_json_to_jinja2(
                    json_file, output_file
                )
                converted_files.append((json_file, output_path, metadata))
            except Exception as e:
                print(f"Error converting {json_file}: {e}")

        return converted_files

    @staticmethod
    def clean_and_load_library(
        source_root: Path,
        output_root: Optional[Path] = None,
        overwrite: bool = False,
        copy_existing_jinja2: bool = True,
    ) -> Dict:
        """
        Scan a user-provided prompt library, clean everything into Jinja2 files,
        and load all cleaned templates into memory for later use.

        Cleaning rules:
        - .txt (CDEX)      -> converted to .jinja2
        - .json (LangChain)-> converted to .jinja2 (template field only)
        - .jinja2          -> copied as-is (optional)
        - others           -> skipped

        Output hierarchy:
        - Preserves relative hierarchy but removes top-level format buckets
          (cdex/langchain/jinja2) if present.

        Args:
            source_root: Root directory of input prompt library.
            output_root: Root directory for cleaned Jinja2 library.
                        Default: <source_root>_cleaned_jinja2
            overwrite: Overwrite existing output files.
            copy_existing_jinja2: If True, copy existing jinja2 files.

        Returns:
            A dictionary containing:
            - cleaned_root: output directory path (str)
            - stats: counts by operation
            - templates: map of template_key -> template metadata and loaded object
            - errors: list of conversion errors
        """
        source_root = Path(source_root)
        if not source_root.exists() or not source_root.is_dir():
            raise FileNotFoundError(f"Source library root not found: {source_root}")

        if output_root is None:
            output_root = source_root.parent / f"{source_root.name}_cleaned_jinja2"
        output_root = Path(output_root)
        output_root.mkdir(parents=True, exist_ok=True)

        env = Environment(autoescape=False)
        templates: Dict[str, Dict] = {}
        errors: List[Dict[str, str]] = []
        allocated_target_rels: Set[Path] = set()
        stats = {
            "scanned_files": 0,
            "converted_cdex": 0,
            "converted_langchain": 0,
            "copied_jinja2": 0,
            "loaded_templates": 0,
            "compiled_templates": 0,
            "invalid_jinja_templates": 0,
            "key_collisions": 0,
            "skipped_files": 0,
            "error_files": 0,
        }

        for source_file in sorted(source_root.rglob("*")):
            if not source_file.is_file():
                continue

            stats["scanned_files"] += 1
            source_format = TemplateConverter._detect_source_format(source_file)
            if source_format is None:
                stats["skipped_files"] += 1
                continue

            try:
                rel = TemplateConverter._normalized_relative_path(source_root, source_file)
                base_target_rel = rel.with_suffix(".jinja2")
                target_rel = base_target_rel

                if target_rel in allocated_target_rels:
                    stats["key_collisions"] += 1
                    stem = base_target_rel.stem
                    candidate = base_target_rel.with_name(
                        f"{stem}__{source_format}{base_target_rel.suffix}"
                    )
                    suffix_idx = 2
                    while candidate in allocated_target_rels:
                        candidate = base_target_rel.with_name(
                            f"{stem}__{source_format}_{suffix_idx}{base_target_rel.suffix}"
                        )
                        suffix_idx += 1
                    target_rel = candidate

                target_file = output_root / target_rel
                allocated_target_rels.add(target_rel)

                if target_file.exists() and not overwrite:
                    # Load from existing cleaned artifact.
                    content = target_file.read_text(encoding="utf-8")
                else:
                    target_file.parent.mkdir(parents=True, exist_ok=True)

                    if source_format == "cdex":
                        raw = source_file.read_text(encoding="utf-8")
                        content = TemplateConverter.cdex_to_jinja2(raw)
                        target_file.write_text(content, encoding="utf-8")
                        stats["converted_cdex"] += 1
                    elif source_format == "langchain":
                        langchain_data = json.loads(source_file.read_text(encoding="utf-8"))
                        raw = langchain_data.get("template", "")
                        content = TemplateConverter.langchain_to_jinja2(raw)
                        target_file.write_text(content, encoding="utf-8")
                        stats["converted_langchain"] += 1
                    else:
                        if not copy_existing_jinja2:
                            stats["skipped_files"] += 1
                            continue
                        content = source_file.read_text(encoding="utf-8")
                        target_file.write_text(content, encoding="utf-8")
                        stats["copied_jinja2"] += 1

                base_template_key = str(target_rel.with_suffix(""))
                template_key = base_template_key
                if template_key in templates:
                    stats["key_collisions"] += 1
                    template_key = f"{base_template_key}__{source_format}"
                    suffix_idx = 2
                    while template_key in templates:
                        template_key = f"{base_template_key}__{source_format}_{suffix_idx}"
                        suffix_idx += 1

                loaded_template = None
                parse_error = None
                try:
                    loaded_template = env.from_string(content)
                    stats["compiled_templates"] += 1
                except Exception as parse_exc:
                    parse_error = str(parse_exc)
                    stats["invalid_jinja_templates"] += 1

                templates[template_key] = {
                    "template_key": template_key,
                    "base_template_key": base_template_key,
                    "source_path": str(source_file),
                    "cleaned_path": str(target_file),
                    "source_format": source_format,
                    "variables": sorted(TemplateConverter.extract_jinja2_variables(content)),
                    "content": content,
                    "loaded_template": loaded_template,
                    "parse_error": parse_error,
                }
                stats["loaded_templates"] += 1
            except Exception as e:
                stats["error_files"] += 1
                errors.append({"file": str(source_file), "error": str(e)})

        return {
            "cleaned_root": str(output_root),
            "stats": stats,
            "templates": templates,
            "errors": errors,
        }

    @staticmethod
    def build_registry(clean_result: Dict) -> "PromptTemplateRegistry":
        """Build a query/render registry from clean_and_load_library output."""
        return PromptTemplateRegistry.from_clean_result(clean_result)


class PromptTemplateRegistry:
    """Registry for cleaned templates with lookup and render helpers."""

    VERSION_SEGMENT_PATTERN = re.compile(r"^v(\d+(?:\.\d+)*)$")

    def __init__(self, clean_result: Dict):
        if "templates" not in clean_result:
            raise ValueError("clean_result must contain a 'templates' key")
        self.clean_result = clean_result
        self.cleaned_root = clean_result.get("cleaned_root")
        self.stats = clean_result.get("stats", {})
        self.errors = clean_result.get("errors", [])
        self.templates = clean_result["templates"]

    @classmethod
    def from_clean_result(cls, clean_result: Dict) -> "PromptTemplateRegistry":
        return cls(clean_result)

    @staticmethod
    def _template_name_from_key(key: str) -> str:
        name = key.rsplit("/", 1)[-1]
        return name.split("__", 1)[0]

    @classmethod
    def _extract_version_tuple(cls, key: str) -> Tuple[int, ...]:
        for seg in key.split("/"):
            match = cls.VERSION_SEGMENT_PATTERN.match(seg)
            if match:
                return tuple(int(x) for x in match.group(1).split("."))
        return tuple()

    @staticmethod
    def _source_priority(source_format: str) -> int:
        # Prefer native Jinja2 first, then converted LangChain, then converted CDEX.
        priority = {
            "jinja2": 3,
            "langchain": 2,
            "cdex": 1,
        }
        return priority.get(source_format, 0)

    @staticmethod
    def _is_base_key(template_info: Dict) -> int:
        return 1 if template_info.get("template_key") == template_info.get("base_template_key") else 0

    def list_keys(
        self,
        prefix: Optional[str] = None,
        version: Optional[str] = None,
        template_name: Optional[str] = None,
        include_invalid: bool = True,
    ) -> List[str]:
        """List keys with optional prefix/version/name filtering."""
        keys = sorted(self.templates.keys())

        if prefix:
            normalized_prefix = prefix.rstrip("/")
            keys = [k for k in keys if k == normalized_prefix or k.startswith(normalized_prefix + "/")]

        if version:
            version_token = version.strip("/")
            keys = [k for k in keys if version_token in k.split("/")]

        if template_name:
            keys = [k for k in keys if self._template_name_from_key(k) == template_name]

        if not include_invalid:
            keys = [k for k in keys if self.templates[k].get("loaded_template") is not None]

        return keys

    def get(self, key: str) -> Optional[Dict]:
        """Get template info by exact key."""
        return self.templates.get(key)

    def resolve(
        self,
        prefix: str,
        version: Optional[str] = None,
        template_name: Optional[str] = None,
        prefer_valid: bool = True,
    ) -> Optional[str]:
        """
        Resolve the best matching key.

        Ranking priority:
        1. Latest version
        2. Preferred source format (jinja2 > langchain > cdex)
        3. Base key over collision suffix variants
        """
        candidates = self.list_keys(
            prefix=prefix,
            version=version,
            template_name=template_name,
            include_invalid=not prefer_valid,
        )
        if not candidates:
            return None

        ranked = sorted(
            candidates,
            key=lambda k: (
                self._extract_version_tuple(k),
                self._source_priority(self.templates[k].get("source_format", "")),
                self._is_base_key(self.templates[k]),
                k,
            ),
            reverse=True,
        )
        return ranked[0]

    def render(self, key: str, context: Dict) -> str:
        """Render a template by exact key."""
        info = self.get(key)
        if info is None:
            raise KeyError(f"Template key not found: {key}")

        tpl = info.get("loaded_template")
        if tpl is None:
            raise ValueError(
                f"Template '{key}' is not renderable due to parse error: {info.get('parse_error')}"
            )

        return tpl.render(**context)

    def render_resolved(
        self,
        prefix: str,
        context: Dict,
        version: Optional[str] = None,
        template_name: Optional[str] = None,
        prefer_valid: bool = True,
    ) -> Tuple[str, str]:
        """Resolve and render in one call. Returns (resolved_key, rendered_text)."""
        key = self.resolve(
            prefix=prefix,
            version=version,
            template_name=template_name,
            prefer_valid=prefer_valid,
        )
        if key is None:
            raise KeyError(
                "No template matched the provided filters: "
                f"prefix={prefix}, version={version}, template_name={template_name}"
            )
        return key, self.render(key, context)
