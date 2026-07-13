import re
import warnings
from pathlib import Path
from unittest import TestCase

from prompt_manager import MyPromptBase, PromptMode, PromptGeneratorLight

prompt_base = Path("./tests/test_prompt")


class ConditionalHeadlineEvaluator(MyPromptBase):
    """Prompt that uses Jinja2 IF logic for conditional prompt generation."""
    DEFAULT_PROMPT_DIR = prompt_base / "dynamic_if"
    DEFAULT_PROMPT_FILE = "evaluate_conditional.jinja2"
    DEFAULT_VERSION = "v1"
    DEFAULT_PROMPT_TYPE = "jinja2"
    KEYS_TO_EXTRACT = []
    DESCRIPTION = "Test prompt with IF conditional logic"

    def __init__(self, vars_in_data_dict=None, version=None):
        version = version or self.DEFAULT_VERSION
        prompt_path = self.DEFAULT_PROMPT_DIR / version / self.DEFAULT_PROMPT_FILE

        super().__init__(
            description=self.DESCRIPTION,
            prompt_path=prompt_path,
            prompt_type=self.DEFAULT_PROMPT_TYPE,
            keys_to_extract=self.KEYS_TO_EXTRACT,
            vars_in_data_dict=vars_in_data_dict,
            version=version,
        )


class CategoryEvaluator(MyPromptBase):
    """Prompt that uses Jinja2 FOR logic for iterating over dynamic lists."""
    DEFAULT_PROMPT_DIR = prompt_base / "dynamic_for"
    DEFAULT_PROMPT_FILE = "evaluate_categories.jinja2"
    DEFAULT_VERSION = "v1"
    DEFAULT_PROMPT_TYPE = "jinja2"
    KEYS_TO_EXTRACT = []
    DESCRIPTION = "Test prompt with FOR loop logic"

    def __init__(self, vars_in_data_dict=None, version=None):
        version = version or self.DEFAULT_VERSION
        prompt_path = self.DEFAULT_PROMPT_DIR / version / self.DEFAULT_PROMPT_FILE

        super().__init__(
            description=self.DESCRIPTION,
            prompt_path=prompt_path,
            prompt_type=self.DEFAULT_PROMPT_TYPE,
            keys_to_extract=self.KEYS_TO_EXTRACT,
            vars_in_data_dict=vars_in_data_dict,
            version=version,
        )


class TestDynamicJinja2Rendering(TestCase):
    """Test dynamic Jinja2 rendering with control structures (IF, FOR)."""

    def setUp(self) -> None:
        warnings.simplefilter('ignore', category=UserWarning)

    def test_if_condition_high_detail(self):
        """Test IF logic: high detail level generates detailed instructions."""
        prompt = ConditionalHeadlineEvaluator(
            vars_in_data_dict={
                "detail_level": "detail_level",
                "headline": "headline",
                "brand": "brand"
            }
        )

        data = {
            "detail_level": "high",
            "headline": "Buy Now - 50% Off",
            "brand": "TechStore"
        }

        generated = prompt.generate_completion_prompt(data)

        # Verify high-detail version is generated
        self.assertIn("DETAILED evaluation", generated)
        self.assertIn("Include specific metrics and data points", generated)
        self.assertIn("Suggest 2-3 improvements", generated)
        self.assertNotIn("STANDARD evaluation", generated)
        self.assertNotIn("QUICK summary", generated)

    def test_if_condition_medium_detail(self):
        """Test IF logic: medium detail level generates standard instructions."""
        prompt = ConditionalHeadlineEvaluator(
            vars_in_data_dict={
                "detail_level": "detail_level",
                "headline": "headline",
                "brand": "brand"
            }
        )

        data = {
            "detail_level": "medium",
            "headline": "Buy Now - 50% Off",
            "brand": "TechStore"
        }

        generated = prompt.generate_completion_prompt(data)

        # Verify medium-detail version is generated
        self.assertIn("STANDARD evaluation", generated)
        self.assertIn("Key metrics and observations", generated)
        self.assertIn("One improvement suggestion", generated)
        self.assertNotIn("DETAILED evaluation", generated)
        self.assertNotIn("QUICK summary", generated)

    def test_if_condition_low_detail(self):
        """Test IF logic: low detail level generates quick instructions."""
        prompt = ConditionalHeadlineEvaluator(
            vars_in_data_dict={
                "detail_level": "detail_level",
                "headline": "headline",
                "brand": "brand"
            }
        )

        data = {
            "detail_level": "low",
            "headline": "Buy Now - 50% Off",
            "brand": "TechStore"
        }

        generated = prompt.generate_completion_prompt(data)

        # Verify low-detail version is generated
        self.assertIn("QUICK summary", generated)
        self.assertIn("Overall assessment (good/fair/poor)", generated)
        self.assertNotIn("DETAILED evaluation", generated)
        self.assertNotIn("STANDARD evaluation", generated)

    def test_for_loop_different_categories(self):
        """Test FOR logic: different category lists generate different prompts."""
        prompt = CategoryEvaluator(
            vars_in_data_dict={
                "headline": "headline",
                "brand": "brand",
                "categories": "categories"
            }
        )

        # Test with 3 categories
        data_3cats = {
            "headline": "Summer Sale",
            "brand": "Fashion Co",
            "categories": ["Relevance", "Appeal", "Clarity"]
        }

        generated_3cats = prompt.generate_completion_prompt(data_3cats)

        # Verify all 3 categories are in the prompt
        self.assertIn("Relevance", generated_3cats)
        self.assertIn("Appeal", generated_3cats)
        self.assertIn("Clarity", generated_3cats)
        # Verify loop generated output sections for each
        self.assertIn("[Relevance]", generated_3cats)
        self.assertIn("[Appeal]", generated_3cats)
        self.assertIn("[Clarity]", generated_3cats)

    def test_for_loop_different_category_count(self):
        """Test FOR logic: different number of categories produce different output lengths."""
        prompt = CategoryEvaluator(
            vars_in_data_dict={
                "headline": "headline",
                "brand": "brand",
                "categories": "categories"
            }
        )

        # Generate with 2 categories
        data_2cats = {
            "headline": "Flash Deal",
            "brand": "Electronics",
            "categories": ["Technical", "Emotional"]
        }
        generated_2cats = prompt.generate_completion_prompt(data_2cats)

        # Generate with 5 categories
        data_5cats = {
            "headline": "Flash Deal",
            "brand": "Electronics",
            "categories": ["Technical", "Emotional", "Visual", "Clarity", "Urgency"]
        }
        generated_5cats = prompt.generate_completion_prompt(data_5cats)

        # Verify 2-category version is shorter
        self.assertLess(len(generated_2cats), len(generated_5cats))

        # Verify all categories appear
        self.assertIn("Technical", generated_2cats)
        self.assertIn("Emotional", generated_2cats)
        self.assertNotIn("Urgency", generated_2cats)

        self.assertIn("Technical", generated_5cats)
        self.assertIn("Urgency", generated_5cats)

    def test_nested_if_and_for_logic_combination(self):
        """Test that Jinja2 properly evaluates both IF and FOR in same template."""
        # Create a prompt that combines IF and FOR logic
        combined_template = """{% if include_categories %}
Evaluate these categories:
{% for cat in categories %}
  - {{ cat }}
{% endfor %}
{% else %}
Provide general evaluation
{% endif %}

Headline: {{ headline }}"""

        # Use PromptGeneratorLight directly for this ad-hoc test
        from tempfile import NamedTemporaryFile
        import os

        # Write template to temp file
        with NamedTemporaryFile(mode='w', suffix='.jinja2', delete=False, dir='/tmp') as f:
            f.write(combined_template)
            temp_path = f.name

        try:
            gen = PromptGeneratorLight(temp_path, prompt_style='jinja2')

            # Test with categories included
            result_with = gen.generate_prompt(
                data={"headline": "Test", "include_categories": True, "categories": ["A", "B"]},
                vars_in_data=["headline", "include_categories", "categories"],
                vars_in_prompt=["headline", "include_categories", "categories"],
                prompt_mode=PromptMode.COMPLETION
            )
            self.assertIn("Evaluate these categories:", result_with)
            self.assertIn("- A", result_with)
            self.assertIn("- B", result_with)

            # Test without categories
            result_without = gen.generate_prompt(
                data={"headline": "Test", "include_categories": False, "categories": []},
                vars_in_data=["headline", "include_categories", "categories"],
                vars_in_prompt=["headline", "include_categories", "categories"],
                prompt_mode=PromptMode.COMPLETION
            )
            self.assertIn("Provide general evaluation", result_without)
            self.assertNotIn("Evaluate these categories:", result_without)

        finally:
            os.unlink(temp_path)

    def test_if_condition_shows_headline_only_in_low_detail(self):
        """Test that variable presence differs based on IF condition."""
        prompt = ConditionalHeadlineEvaluator(
            vars_in_data_dict={
                "detail_level": "detail_level",
                "headline": "headline"
            }
        )

        data = {
            "detail_level": "high",
            "headline": "Buy Now - 50% Off"
        }

        high_detail_prompt = prompt.generate_completion_prompt(data)

        # High detail includes detailed instructions
        self.assertIn("DETAILED evaluation", high_detail_prompt)
        self.assertIn("Buy Now - 50% Off", high_detail_prompt)

        # Low detail version
        data["detail_level"] = "low"
        low_detail_prompt = prompt.generate_completion_prompt(data)

        # Low detail generates different content
        self.assertIn("QUICK summary", low_detail_prompt)
        self.assertIn("Buy Now - 50% Off", low_detail_prompt)
        
        # Verify the content is different
        self.assertNotEqual(high_detail_prompt, low_detail_prompt)
