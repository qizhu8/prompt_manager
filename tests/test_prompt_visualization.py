import tempfile
from pathlib import Path

import pytest

from prompt_manager.visualizer.prompt_visualization import PromptVisualizationService


class TestPromptVisualizationService:
    def test_tree_and_read_prompt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "prompt_lib"
            file_path = root / "family" / "v1" / "gen_output.jinja2"
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text("Hello {{ name }}", encoding="utf-8")

            # Non-jinja prompt should be hidden from tree.
            hidden_path = root / "family" / "v1" / "legacy.txt"
            hidden_path.write_text("#name#", encoding="utf-8")

            svc = PromptVisualizationService(root)
            tree = svc.build_tree()

            assert tree["type"] == "dir"
            serialized = str(tree)
            assert "gen_output.jinja2" in serialized
            assert "legacy.txt" not in serialized

            data = svc.read_prompt("family/v1/gen_output.jinja2")
            assert data["path"] == "family/v1/gen_output.jinja2"
            assert data["content"] == "Hello {{ name }}"
            assert data["review"]["syntax_valid"] is True
            assert data["review"]["variables"] == ["name"]

    def test_save_prompt_and_review(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "prompt_lib"
            file_path = root / "family" / "v1" / "gen_output.jinja2"
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text("A {{ x }}", encoding="utf-8")

            svc = PromptVisualizationService(root)
            save = svc.save_prompt("family/v1/gen_output.jinja2", "B {{ y }}")

            assert save["path"] == "family/v1/gen_output.jinja2"
            assert save["review"]["syntax_valid"] is True
            assert save["review"]["variables"] == ["y"]
            assert file_path.read_text(encoding="utf-8") == "B {{ y }}"

    def test_create_new_version_latest_auto(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "prompt_lib"

            v1 = root / "family" / "v1" / "gen_output.jinja2"
            v2 = root / "family" / "v2" / "gen_output.jinja2"
            v1.parent.mkdir(parents=True, exist_ok=True)
            v2.parent.mkdir(parents=True, exist_ok=True)
            v1.write_text("V1 {{ name }}", encoding="utf-8")
            v2.write_text("V2 {{ name }}", encoding="utf-8")

            svc = PromptVisualizationService(root)
            result = svc.create_new_version("family", new_version="v3")

            assert result["source_version"] == "v2"
            assert result["new_version"] == "v3"

            v3_file = root / "family" / "v3" / "gen_output.jinja2"
            assert v3_file.exists()
            assert v3_file.read_text(encoding="utf-8") == "V2 {{ name }}"

    def test_create_new_version_explicit_source(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "prompt_lib"

            v1 = root / "family" / "v1" / "gen_output.jinja2"
            v2 = root / "family" / "v2" / "gen_output.jinja2"
            v1.parent.mkdir(parents=True, exist_ok=True)
            v2.parent.mkdir(parents=True, exist_ok=True)
            v1.write_text("V1", encoding="utf-8")
            v2.write_text("V2", encoding="utf-8")

            svc = PromptVisualizationService(root)
            svc.create_new_version("family", source_version="v1", new_version="v1.1")

            out = root / "family" / "v1.1" / "gen_output.jinja2"
            assert out.exists()
            assert out.read_text(encoding="utf-8") == "V1"

    def test_security_path_escape_blocked(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "prompt_lib"
            target = root / "family" / "v1" / "gen_output.jinja2"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("ok", encoding="utf-8")

            svc = PromptVisualizationService(root)

            with pytest.raises(ValueError):
                svc.read_prompt("../../etc/passwd")

    def test_invalid_syntax_review(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "prompt_lib"
            target = root / "family" / "v1" / "broken.jinja2"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("{% block x %}oops", encoding="utf-8")

            svc = PromptVisualizationService(root)
            data = svc.read_prompt("family/v1/broken.jinja2")
            assert data["review"]["syntax_valid"] is False
            assert data["review"]["syntax_error"] is not None

    def test_render_full_prompt_with_extends(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "prompt_lib"

            base_file = root / "common" / "base.jinja2"
            child_file = root / "family" / "v1" / "child.jinja2"
            base_file.parent.mkdir(parents=True, exist_ok=True)
            child_file.parent.mkdir(parents=True, exist_ok=True)

            base_file.write_text(
                "Header\n{% block body %}BASE BODY{% endblock %}\nFooter",
                encoding="utf-8",
            )
            child_file.write_text(
                "{% extends 'common/base.jinja2' %}{% block body %}Body: {{ value }}{% endblock %}",
                encoding="utf-8",
            )

            svc = PromptVisualizationService(root)
            result = svc.render_full_prompt("family/v1/child.jinja2", {"value": "X"})

            assert result["path"] == "family/v1/child.jinja2"
            assert "Header" in result["rendered_prompt"]
            assert "Body: X" in result["rendered_prompt"]
            assert "Footer" in result["rendered_prompt"]

    def test_render_full_prompt_context_type_validation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "prompt_lib"
            target = root / "family" / "v1" / "gen_output.jinja2"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("Hello {{ name }}", encoding="utf-8")

            svc = PromptVisualizationService(root)
            with pytest.raises(ValueError):
                svc.render_full_prompt("family/v1/gen_output.jinja2", context=["bad"])

    def test_render_full_prompt_include_uses_library_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "prompt_lib"
            root_header = root / "header.jinja2"
            nested_header = root / "family" / "v1" / "header.jinja2"
            target = root / "family" / "v1" / "main.jinja2"

            target.parent.mkdir(parents=True, exist_ok=True)
            root_header.write_text("ROOT_HEADER", encoding="utf-8")
            nested_header.write_text("NESTED_HEADER", encoding="utf-8")
            target.write_text("{% include 'header.jinja2' %}", encoding="utf-8")

            svc = PromptVisualizationService(root)
            rendered = svc.render_full_prompt("family/v1/main.jinja2")

            assert rendered["rendered_prompt"] == "ROOT_HEADER"

    def test_upsert_and_read_metadata_comments(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "prompt_lib"
            target = root / "family" / "v1" / "gen_output.jinja2"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("Body {{ value }}", encoding="utf-8")

            svc = PromptVisualizationService(root)
            svc.upsert_prompt_metadata(
                "family/v1/gen_output.jinja2",
                title="One line title",
                note="First line\nSecond line",
            )

            data = svc.read_prompt("family/v1/gen_output.jinja2")
            assert data["metadata"]["title"] == "One line title"
            assert data["metadata"]["note"] == "First line\nSecond line"
            assert data["content"].startswith("{# PROMPT_METADATA")

    def test_annotate_all_prompts_adds_missing_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "prompt_lib"
            p1 = root / "family" / "v1" / "a.jinja2"
            p2 = root / "family" / "v1" / "b.jinja2"
            p1.parent.mkdir(parents=True, exist_ok=True)
            p1.write_text("A", encoding="utf-8")
            p2.write_text("{# PROMPT_METADATA\ntitle: Existing\nnote:\nX\n#}\nB", encoding="utf-8")

            svc = PromptVisualizationService(root)
            result = svc.annotate_all_prompts(default_title_prefix="AUTO", default_note="N")

            assert result["updated"] == 1
            assert result["skipped"] == 1
            assert p1.read_text(encoding="utf-8").startswith("{# PROMPT_METADATA")

    def test_version_prompt_summary_and_diff(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "prompt_lib"
            v1 = root / "family" / "v1" / "gen_output.jinja2"
            v2 = root / "family" / "v2" / "gen_output.jinja2"
            v1.parent.mkdir(parents=True, exist_ok=True)
            v2.parent.mkdir(parents=True, exist_ok=True)
            v1.write_text("{# PROMPT_METADATA\ntitle: V1\nnote:\nOld\n#}\nLineA\nLineB", encoding="utf-8")
            v2.write_text("{# PROMPT_METADATA\ntitle: V2\nnote:\nNew\n#}\nLineA\nLineC", encoding="utf-8")

            svc = PromptVisualizationService(root)
            summary = svc.get_version_prompt_summary("family", "gen_output.jinja2")
            assert len(summary["versions"]) == 2
            assert summary["versions"][0]["version"] == "v2"

            diff = svc.diff_prompt_versions("family", "gen_output.jinja2", "v1", "v2")
            assert any(d["type"] == "add" and d["text"] == "title: V2" for d in diff["diff_lines"])
            assert any(d["type"] == "del" and d["text"] == "title: V1" for d in diff["diff_lines"])
