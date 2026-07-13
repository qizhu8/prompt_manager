"""
Comprehensive test suite for template conversion from CDEX and LangChain formats to Jinja2.
"""

import json
import tempfile
from pathlib import Path

import pytest
from jinja2 import Environment

from prompt_manager.prompt_converter import TemplateConverter


class TestCDEXToJinja2Conversion:
    """Test conversion from CDEX format to Jinja2."""

    def test_simple_cdex_to_jinja2(self):
        """Test conversion of simple CDEX template."""
        cdex_text = "Hello #name#, your score is #score#"
        expected = "Hello {{ name }}, your score is {{ score }}"
        result = TemplateConverter.cdex_to_jinja2(cdex_text)
        assert result == expected

    def test_cdex_with_multiple_same_variable(self):
        """Test conversion with multiple instances of same variable."""
        cdex_text = "Product: #product#, Reviews: #product# reviews"
        expected = "Product: {{ product }}, Reviews: {{ product }} reviews"
        result = TemplateConverter.cdex_to_jinja2(cdex_text)
        assert result == expected

    def test_cdex_with_newlines(self):
        """Test conversion preserves newlines."""
        cdex_text = "Line 1: #var1#\nLine 2: #var2#"
        expected = "Line 1: {{ var1 }}\nLine 2: {{ var2 }}"
        result = TemplateConverter.cdex_to_jinja2(cdex_text)
        assert result == expected

    def test_cdex_with_special_characters(self):
        """Test conversion with special characters around placeholders."""
        cdex_text = "Email: #email# (required), Phone: #phone# (optional)"
        expected = "Email: {{ email }} (required), Phone: {{ phone }} (optional)"
        result = TemplateConverter.cdex_to_jinja2(cdex_text)
        assert result == expected

    def test_cdex_with_no_placeholders(self):
        """Test conversion of text without placeholders."""
        cdex_text = "This is a static template with no variables."
        result = TemplateConverter.cdex_to_jinja2(cdex_text)
        assert result == cdex_text

    def test_cdex_preserves_literal_double_braces(self):
        """Literal {{...}} blocks should be preserved as raw text in output."""
        cdex_text = 'Example JSON: {{"Label":"diverse"}}\nUser: #name#'
        result = TemplateConverter.cdex_to_jinja2(cdex_text)
        assert result == 'Example JSON: {% raw %}{{"Label":"diverse"}}{% endraw %}\nUser: {{ name }}'
        Environment(autoescape=False).parse(result)

    def test_cdex_extract_variables(self):
        """Test extracting variables from CDEX format."""
        cdex_text = "Hello #name#, your score is #score#. Welcome #name#!"
        variables = TemplateConverter.extract_cdex_variables(cdex_text)
        assert variables == {"name", "score"}

    def test_cdex_extract_variables_underscore(self):
        """Test extracting variables with underscores."""
        cdex_text = "User: #user_id#, Product: #product_name#"
        variables = TemplateConverter.extract_cdex_variables(cdex_text)
        assert variables == {"user_id", "product_name"}

    def test_cdex_file_conversion(self):
        """Test converting a CDEX file to Jinja2."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create a CDEX file
            cdex_file = tmpdir / "template.txt"
            cdex_file.write_text("Hello #name#, your score is #score#")

            # Convert
            content, output_path = TemplateConverter.cdex_file_to_jinja2(cdex_file)

            # Check
            assert output_path.suffix == ".jinja2"
            assert output_path.exists()
            assert content == "Hello {{ name }}, your score is {{ score }}"
            assert output_path.read_text() == content

    def test_cdex_file_conversion_custom_output(self):
        """Test converting a CDEX file with custom output path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create a CDEX file
            cdex_file = tmpdir / "template.txt"
            cdex_file.write_text("Hello #name#")

            # Convert with custom output
            output_file = tmpdir / "custom_jinja2.jinja2"
            content, output_path = TemplateConverter.cdex_file_to_jinja2(
                cdex_file, output_file
            )

            # Check
            assert output_path == output_file
            assert output_path.exists()

    def test_batch_convert_cdex_files(self):
        """Test batch conversion of multiple CDEX files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create multiple CDEX files in subdirectories
            (tmpdir / "subdir1").mkdir()
            (tmpdir / "subdir2").mkdir()

            file1 = tmpdir / "subdir1" / "template1.txt"
            file1.write_text("Hello #name#")

            file2 = tmpdir / "subdir2" / "template2.txt"
            file2.write_text("Goodbye #name#, score: #score#")

            # Batch convert
            converted = TemplateConverter.batch_convert_cdex_files(tmpdir, overwrite=True)

            # Check
            assert len(converted) == 2
            assert (tmpdir / "subdir1" / "template1.jinja2").exists()
            assert (tmpdir / "subdir2" / "template2.jinja2").exists()


class TestLangChainToJinja2Conversion:
    """Test conversion from LangChain format to Jinja2."""

    def test_simple_langchain_to_jinja2(self):
        """Test conversion of simple LangChain template."""
        langchain_text = "Hello {name}, your score is {score}"
        expected = "Hello {{ name }}, your score is {{ score }}"
        result = TemplateConverter.langchain_to_jinja2(langchain_text)
        assert result == expected

    def test_langchain_with_multiple_same_variable(self):
        """Test conversion with multiple instances of same variable."""
        langchain_text = "Product: {product}, Reviews: {product} reviews"
        expected = "Product: {{ product }}, Reviews: {{ product }} reviews"
        result = TemplateConverter.langchain_to_jinja2(langchain_text)
        assert result == expected

    def test_langchain_with_newlines(self):
        """Test conversion preserves newlines."""
        langchain_text = "Line 1: {var1}\nLine 2: {var2}"
        expected = "Line 1: {{ var1 }}\nLine 2: {{ var2 }}"
        result = TemplateConverter.langchain_to_jinja2(langchain_text)
        assert result == expected

    def test_langchain_with_special_characters(self):
        """Test conversion with special characters around placeholders."""
        langchain_text = "Email: {email} (required), Phone: {phone} (optional)"
        expected = "Email: {{ email }} (required), Phone: {{ phone }} (optional)"
        result = TemplateConverter.langchain_to_jinja2(langchain_text)
        assert result == expected

    def test_langchain_with_no_placeholders(self):
        """Test conversion of text without placeholders."""
        langchain_text = "This is a static template with no variables."
        result = TemplateConverter.langchain_to_jinja2(langchain_text)
        assert result == langchain_text

    def test_langchain_preserves_literal_double_braces(self):
        """Literal {{...}} blocks should be preserved as raw text in output."""
        langchain_text = 'History: [{{"Query":"guitar tutorial"}}]\nUser: {name}'
        result = TemplateConverter.langchain_to_jinja2(langchain_text)
        assert result == 'History: [{% raw %}{{"Query":"guitar tutorial"}}{% endraw %}]\nUser: {{ name }}'
        Environment(autoescape=False).parse(result)

    def test_langchain_extract_variables(self):
        """Test extracting variables from LangChain format."""
        langchain_text = "Hello {name}, your score is {score}. Welcome {name}!"
        variables = TemplateConverter.extract_langchain_variables(langchain_text)
        assert variables == {"name", "score"}

    def test_langchain_extract_variables_underscore(self):
        """Test extracting variables with underscores."""
        langchain_text = "User: {user_id}, Product: {product_name}"
        variables = TemplateConverter.extract_langchain_variables(langchain_text)
        assert variables == {"user_id", "product_name"}

    def test_langchain_json_file_conversion(self):
        """Test converting a LangChain JSON file to Jinja2."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create a LangChain JSON file
            langchain_json = {
                "name": "test_prompt",
                "input_variables": ["name", "score"],
                "optional_variables": ["comment"],
                "output_parser": None,
                "partial_variables": {},
                "metadata": None,
                "tags": ["test", "example"],
                "template": "Hello {name}, your score is {score}",
                "template_format": "f-string",
                "validate_template": True,
                "_type": "prompt",
            }

            json_file = tmpdir / "template.json"
            json_file.write_text(json.dumps(langchain_json))

            # Convert
            content, output_path, metadata = TemplateConverter.langchain_json_to_jinja2(
                json_file
            )

            # Check
            assert output_path.suffix == ".jinja2"
            assert output_path.exists()
            assert content == "Hello {{ name }}, your score is {{ score }}"
            assert metadata["input_variables"] == ["name", "score"]
            assert metadata["optional_variables"] == ["comment"]
            assert metadata["tags"] == ["test", "example"]
            assert metadata["name"] == "test_prompt"

    def test_langchain_json_file_conversion_custom_output(self):
        """Test converting LangChain JSON with custom output path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create a LangChain JSON file
            langchain_json = {
                "input_variables": ["name"],
                "template": "Hello {name}",
                "template_format": "f-string",
                "_type": "prompt",
            }

            json_file = tmpdir / "template.json"
            json_file.write_text(json.dumps(langchain_json))

            # Convert with custom output
            output_file = tmpdir / "custom_jinja2.jinja2"
            content, output_path, metadata = TemplateConverter.langchain_json_to_jinja2(
                json_file, output_file
            )

            # Check
            assert output_path == output_file
            assert output_path.exists()

    def test_langchain_metadata_to_yaml(self):
        """Test converting LangChain metadata to YAML."""
        metadata = {
            "name": "feature_extraction",
            "input_variables": ["brand", "product"],
            "optional_variables": ["additional_context"],
            "tags": ["nlp", "extraction"],
            "template_format": "f-string",
        }

        yaml_output = TemplateConverter.langchain_metadata_to_yaml(metadata)

        assert "feature_extraction" in yaml_output
        assert "brand" in yaml_output
        assert "product" in yaml_output
        assert "additional_context" in yaml_output
        assert "nlp" in yaml_output

    def test_batch_convert_langchain_files(self):
        """Test batch conversion of multiple LangChain JSON files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create multiple LangChain JSON files
            (tmpdir / "subdir1").mkdir()
            (tmpdir / "subdir2").mkdir()

            json1 = {
                "input_variables": ["name"],
                "template": "Hello {name}",
                "_type": "prompt",
            }
            json2 = {
                "input_variables": ["name", "score"],
                "template": "Score: {score}, Name: {name}",
                "_type": "prompt",
            }

            file1 = tmpdir / "subdir1" / "template1.json"
            file1.write_text(json.dumps(json1))

            file2 = tmpdir / "subdir2" / "template2.json"
            file2.write_text(json.dumps(json2))

            # Batch convert
            converted = TemplateConverter.batch_convert_langchain_files(
                tmpdir, overwrite=True
            )

            # Check
            assert len(converted) == 2
            assert (tmpdir / "subdir1" / "template1.jinja2").exists()
            assert (tmpdir / "subdir2" / "template2.jinja2").exists()


class TestJinja2VariableExtraction:
    """Test extracting variables from Jinja2 format."""

    def test_extract_jinja2_variables(self):
        """Test extracting variables from Jinja2 format."""
        jinja2_text = "Hello {{ name }}, your score is {{ score }}. Welcome {{ name }}!"
        variables = TemplateConverter.extract_jinja2_variables(jinja2_text)
        assert variables == {"name", "score"}

    def test_extract_jinja2_variables_underscore(self):
        """Test extracting Jinja2 variables with underscores."""
        jinja2_text = "User: {{ user_id }}, Product: {{ product_name }}"
        variables = TemplateConverter.extract_jinja2_variables(jinja2_text)
        assert variables == {"user_id", "product_name"}


class TestRoundTripConversions:
    """Test converting between formats and back."""

    def test_cdex_langchain_to_jinja2_roundtrip(self):
        """Test that CDEX and LangChain conversions produce same Jinja2."""
        # Same semantic content in different formats
        cdex_text = "User: #user_id#, Email: #email#"
        langchain_text = "User: {user_id}, Email: {email}"

        cdex_jinja2 = TemplateConverter.cdex_to_jinja2(cdex_text)
        langchain_jinja2 = TemplateConverter.langchain_to_jinja2(langchain_text)

        assert cdex_jinja2 == langchain_jinja2
        assert cdex_jinja2 == "User: {{ user_id }}, Email: {{ email }}"

    def test_variable_extraction_consistency(self):
        """Test that variable extraction is consistent across formats."""
        variables = {"name", "score", "grade", "comment"}

        cdex_text = "Name: #name#, Score: #score#, Grade: #grade#, Comment: #comment#"
        langchain_text = "Name: {name}, Score: {score}, Grade: {grade}, Comment: {comment}"
        jinja2_text = "Name: {{ name }}, Score: {{ score }}, Grade: {{ grade }}, Comment: {{ comment }}"

        cdex_vars = TemplateConverter.extract_cdex_variables(cdex_text)
        langchain_vars = TemplateConverter.extract_langchain_variables(langchain_text)
        jinja2_vars = TemplateConverter.extract_jinja2_variables(jinja2_text)

        assert cdex_vars == variables
        assert langchain_vars == variables
        assert jinja2_vars == variables


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_cdex_with_numbers_and_underscores(self):
        """Test CDEX with complex variable names."""
        cdex_text = "#var_1# and #_var2# and #VAR_3#"
        jinja2_text = TemplateConverter.cdex_to_jinja2(cdex_text)
        assert "{{ var_1 }}" in jinja2_text
        assert "{{ _var2 }}" in jinja2_text
        assert "{{ VAR_3 }}" in jinja2_text

    def test_langchain_with_numbers_and_underscores(self):
        """Test LangChain with complex variable names."""
        langchain_text = "{var_1} and {_var2} and {VAR_3}"
        jinja2_text = TemplateConverter.langchain_to_jinja2(langchain_text)
        assert "{{ var_1 }}" in jinja2_text
        assert "{{ _var2 }}" in jinja2_text
        assert "{{ VAR_3 }}" in jinja2_text

    def test_cdex_missing_file(self):
        """Test error handling for missing CDEX file."""
        with pytest.raises(FileNotFoundError):
            TemplateConverter.cdex_file_to_jinja2(Path("/nonexistent/file.txt"))

    def test_langchain_missing_file(self):
        """Test error handling for missing LangChain file."""
        with pytest.raises(FileNotFoundError):
            TemplateConverter.langchain_json_to_jinja2(Path("/nonexistent/file.json"))

    def test_empty_cdex_template(self):
        """Test converting empty CDEX template."""
        result = TemplateConverter.cdex_to_jinja2("")
        assert result == ""

    def test_empty_langchain_template(self):
        """Test converting empty LangChain template."""
        result = TemplateConverter.langchain_to_jinja2("")
        assert result == ""

    def test_multiline_complex_template(self):
        """Test conversion of complex multiline template."""
        cdex_template = """
# Task: Evaluate product
Product: #product_name#
Brand: #brand#
Categories: #categories#

Evaluation Guidelines:
1. Consider #product_name# characteristics
2. Check brand #brand# positioning
3. Rate across #categories#

Output:
Rating: <rating>VALUE</rating>
"""

        jinja2_template = TemplateConverter.cdex_to_jinja2(cdex_template)

        # Verify all variables are converted
        variables = TemplateConverter.extract_jinja2_variables(jinja2_template)
        assert variables == {"product_name", "brand", "categories"}

        # Verify newlines are preserved
        assert "\n" in jinja2_template


class TestLibraryCleaningAndLoading:
    """Test scanning, cleaning, and loading a mixed prompt library."""

    def test_clean_and_load_library_mixed_formats(self):
        """Validate mixed CDEX/LangChain/Jinja2 library conversion and loading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            source_root = tmpdir / "prompt_lib"

            # Create CDEX prompt
            cdex_file = source_root / "cdex" / "domain_a" / "v1" / "a_prompt.txt"
            cdex_file.parent.mkdir(parents=True, exist_ok=True)
            cdex_file.write_text("Hello #name#, product=#product#", encoding="utf-8")

            # Create LangChain prompt
            langchain_file = source_root / "langchain" / "domain_b" / "v2" / "b_prompt.json"
            langchain_file.parent.mkdir(parents=True, exist_ok=True)
            langchain_file.write_text(
                json.dumps({
                    "input_variables": ["user", "score"],
                    "template": "User {user} score {score}",
                    "_type": "prompt",
                }),
                encoding="utf-8",
            )

            # Create existing Jinja2 prompt
            jinja2_file = source_root / "jinja2" / "domain_c" / "v3" / "c_prompt.jinja2"
            jinja2_file.parent.mkdir(parents=True, exist_ok=True)
            jinja2_file.write_text("Existing {{ value }}", encoding="utf-8")

            # Non-prompt artifact should be skipped
            noise_file = source_root / "cdex" / "domain_a" / "v1" / "publish_log"
            noise_file.write_text("20251031", encoding="utf-8")

            result = TemplateConverter.clean_and_load_library(source_root=source_root)

            cleaned_root = Path(result["cleaned_root"])
            assert cleaned_root.exists()

            # Clean hierarchy should drop top-level format bucket.
            assert (cleaned_root / "domain_a" / "v1" / "a_prompt.jinja2").exists()
            assert (cleaned_root / "domain_b" / "v2" / "b_prompt.jinja2").exists()
            assert (cleaned_root / "domain_c" / "v3" / "c_prompt.jinja2").exists()

            stats = result["stats"]
            assert stats["converted_cdex"] == 1
            assert stats["converted_langchain"] == 1
            assert stats["copied_jinja2"] == 1
            assert stats["loaded_templates"] == 3
            assert stats["error_files"] == 0
            assert stats["skipped_files"] >= 1

            templates = result["templates"]
            assert "domain_a/v1/a_prompt" in templates
            assert "domain_b/v2/b_prompt" in templates
            assert "domain_c/v3/c_prompt" in templates

            # Verify loaded template is renderable later.
            rendered = templates["domain_a/v1/a_prompt"]["loaded_template"].render(
                name="Alice", product="Laptop"
            )
            assert rendered == "Hello Alice, product=Laptop"

    def test_clean_and_load_library_overwrite_false_reuses_existing(self):
        """Verify existing cleaned files are reused when overwrite=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            source_root = tmpdir / "prompt_lib"
            output_root = tmpdir / "prompt_lib_cleaned"

            src = source_root / "cdex" / "x" / "v1" / "item.txt"
            src.parent.mkdir(parents=True, exist_ok=True)
            src.write_text("v1 #name#", encoding="utf-8")

            first = TemplateConverter.clean_and_load_library(
                source_root=source_root,
                output_root=output_root,
                overwrite=True,
            )
            first_cleaned = Path(first["cleaned_root"]) / "x" / "v1" / "item.jinja2"
            assert first_cleaned.read_text(encoding="utf-8") == "v1 {{ name }}"

            # Change source, run again without overwrite: cleaned output should stay the same.
            src.write_text("v2 #name#", encoding="utf-8")
            second = TemplateConverter.clean_and_load_library(
                source_root=source_root,
                output_root=output_root,
                overwrite=False,
            )
            assert first_cleaned.read_text(encoding="utf-8") == "v1 {{ name }}"

            templates = second["templates"]
            rendered = templates["x/v1/item"]["loaded_template"].render(name="Bob")
            assert rendered == "v1 Bob"

    def test_clean_and_load_library_handles_key_collisions(self):
        """When normalized paths collide, both templates should be preserved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            source_root = tmpdir / "prompt_lib"

            cdex_file = source_root / "cdex" / "same" / "v1" / "prompt.txt"
            cdex_file.parent.mkdir(parents=True, exist_ok=True)
            cdex_file.write_text("Hi #name#", encoding="utf-8")

            langchain_file = source_root / "langchain" / "same" / "v1" / "prompt.json"
            langchain_file.parent.mkdir(parents=True, exist_ok=True)
            langchain_file.write_text(
                json.dumps({"template": "Hello {name}", "_type": "prompt"}),
                encoding="utf-8",
            )

            result = TemplateConverter.clean_and_load_library(source_root=source_root)
            templates = result["templates"]

            assert "same/v1/prompt" in templates
            assert "same/v1/prompt__langchain" in templates
            assert result["stats"]["key_collisions"] >= 1

    def test_clean_and_load_library_keeps_invalid_jinja_with_parse_error(self):
        """Invalid Jinja source should be kept with parse_error and no crash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            source_root = tmpdir / "prompt_lib"

            bad_file = source_root / "jinja2" / "bad" / "v1" / "broken.jinja2"
            bad_file.parent.mkdir(parents=True, exist_ok=True)
            bad_file.write_text("{% block x %}missing end", encoding="utf-8")

            result = TemplateConverter.clean_and_load_library(source_root=source_root)
            tpl = result["templates"]["bad/v1/broken"]

            assert tpl["loaded_template"] is None
            assert tpl["parse_error"] is not None
            assert result["stats"]["invalid_jinja_templates"] == 1
            assert result["stats"]["error_files"] == 0


class TestPromptTemplateRegistry:
    """Test registry lookup and rendering helpers."""

    def test_registry_resolve_latest_version_and_render(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            source_root = tmpdir / "prompt_lib"

            v1 = source_root / "jinja2" / "shop" / "headline" / "v1" / "gen.jinja2"
            v2 = source_root / "jinja2" / "shop" / "headline" / "v2" / "gen.jinja2"
            v1.parent.mkdir(parents=True, exist_ok=True)
            v2.parent.mkdir(parents=True, exist_ok=True)
            v1.write_text("V1 {{ name }}", encoding="utf-8")
            v2.write_text("V2 {{ name }}", encoding="utf-8")

            clean_result = TemplateConverter.clean_and_load_library(source_root=source_root)
            registry = TemplateConverter.build_registry(clean_result)

            resolved = registry.resolve(prefix="shop/headline", template_name="gen")
            assert resolved is not None
            assert "/v2/" in resolved

            key, rendered = registry.render_resolved(
                prefix="shop/headline",
                template_name="gen",
                context={"name": "Alice"},
            )
            assert key == resolved
            assert rendered == "V2 Alice"

    def test_registry_prefers_jinja2_on_collisions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            source_root = tmpdir / "prompt_lib"

            cdex_file = source_root / "cdex" / "same" / "v1" / "prompt.txt"
            langchain_file = source_root / "langchain" / "same" / "v1" / "prompt.json"
            jinja2_file = source_root / "jinja2" / "same" / "v1" / "prompt.jinja2"

            cdex_file.parent.mkdir(parents=True, exist_ok=True)
            langchain_file.parent.mkdir(parents=True, exist_ok=True)
            jinja2_file.parent.mkdir(parents=True, exist_ok=True)

            cdex_file.write_text("CDEX #name#", encoding="utf-8")
            langchain_file.write_text(json.dumps({"template": "LC {name}", "_type": "prompt"}), encoding="utf-8")
            jinja2_file.write_text("J2 {{ name }}", encoding="utf-8")

            clean_result = TemplateConverter.clean_and_load_library(source_root=source_root)
            registry = TemplateConverter.build_registry(clean_result)

            resolved = registry.resolve(prefix="same/v1", template_name="prompt")
            assert resolved is not None
            info = registry.get(resolved)
            assert info is not None
            assert info["source_format"] == "jinja2"

            rendered = registry.render(resolved, {"name": "Bob"})
            assert rendered == "J2 Bob"

    def test_registry_list_keys_excludes_invalid_when_requested(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            source_root = tmpdir / "prompt_lib"

            good = source_root / "jinja2" / "demo" / "v1" / "good.jinja2"
            bad = source_root / "jinja2" / "demo" / "v1" / "bad.jinja2"
            good.parent.mkdir(parents=True, exist_ok=True)
            good.write_text("OK {{ x }}", encoding="utf-8")
            bad.write_text("{% block a %}broken", encoding="utf-8")

            clean_result = TemplateConverter.clean_and_load_library(source_root=source_root)
            registry = TemplateConverter.build_registry(clean_result)

            all_keys = registry.list_keys(prefix="demo/v1", include_invalid=True)
            valid_keys = registry.list_keys(prefix="demo/v1", include_invalid=False)

            assert len(all_keys) == 2
            assert len(valid_keys) == 1
            assert valid_keys[0].endswith("good")
