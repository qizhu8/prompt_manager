import re
import warnings
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch

from prompt_manager import MyPromptBase, PromptMode

prompt_base = Path("./tests/test_prompt")


class LangChainPrompt(MyPromptBase):
    DEFAULT_PROMPT_DIR = prompt_base / "prompt_with_known_placeholders"
    DEFAULT_PROMPT_FILE = "test_prompt.json"
    DEFAULT_VERSION = None
    DEFAULT_PROMPT_TYPE = "langchain"
    KEYS_TO_EXTRACT = []
    DESCRIPTION = f"Test prompt"

    def __init__(self, prompt_type: str = DEFAULT_PROMPT_TYPE, vars_in_data_dict: dict = {}, output_key_rename_dict: dict = None, keys_to_extract: list = KEYS_TO_EXTRACT, version: str = DEFAULT_VERSION):
        version = self.__class__.DEFAULT_VERSION if version is None else version
        prompt_path = self.__class__.DEFAULT_PROMPT_DIR / version / self.__class__.DEFAULT_PROMPT_FILE

        super().__init__(
            description=self.__class__.DESCRIPTION,
            prompt_path=prompt_path, prompt_type=prompt_type,
            keys_to_extract=keys_to_extract,
            vars_in_data_dict=vars_in_data_dict,
            output_key_rename_dict=output_key_rename_dict,
            version=version,
        )


class Jinja2Prompt(MyPromptBase):
    DEFAULT_PROMPT_DIR = prompt_base / "prompt_with_known_placeholders"
    DEFAULT_PROMPT_FILE = "test_prompt.jinja2"
    DEFAULT_VERSION = None
    DEFAULT_PROMPT_TYPE = "jinja2"
    KEYS_TO_EXTRACT = []
    DESCRIPTION = f"Test prompt"

    def __init__(self, prompt_type: str = DEFAULT_PROMPT_TYPE, vars_in_data_dict: dict = {}, output_key_rename_dict: dict = None, keys_to_extract: list = KEYS_TO_EXTRACT, version: str = DEFAULT_VERSION):
        version = self.__class__.DEFAULT_VERSION if version is None else version
        prompt_path = self.__class__.DEFAULT_PROMPT_DIR / version / self.__class__.DEFAULT_PROMPT_FILE

        super().__init__(
            description=self.__class__.DESCRIPTION,
            prompt_path=prompt_path, prompt_type=prompt_type,
            keys_to_extract=keys_to_extract,
            vars_in_data_dict=vars_in_data_dict,
            output_key_rename_dict=output_key_rename_dict,
            version=version,
        )


class CDEXPrompt(MyPromptBase):
    DEFAULT_PROMPT_DIR = prompt_base / "prompt_with_known_placeholders"
    DEFAULT_PROMPT_FILE = "test_prompt.txt"
    DEFAULT_VERSION = None
    DEFAULT_PROMPT_TYPE = "cdex"
    KEYS_TO_EXTRACT = []
    DESCRIPTION = f"Test prompt"

    def __init__(self, prompt_type: str = DEFAULT_PROMPT_TYPE, vars_in_data_dict: dict = {}, output_key_rename_dict: dict = None, keys_to_extract: list = KEYS_TO_EXTRACT, version: str = DEFAULT_VERSION):
        version = self.__class__.DEFAULT_VERSION if version is None else version
        prompt_path = self.__class__.DEFAULT_PROMPT_DIR / version / self.__class__.DEFAULT_PROMPT_FILE

        super().__init__(
            description=self.__class__.DESCRIPTION,
            prompt_path=prompt_path, prompt_type=prompt_type,
            keys_to_extract=keys_to_extract,
            vars_in_data_dict=vars_in_data_dict,
            output_key_rename_dict=output_key_rename_dict,
            version=version,
        )


class TestPromptLoader(TestCase):

    def setUp(self) -> None:
        pass

    def test_langchain_prompt_loading(self):
        # Test loading a LangChain prompt
        prompt = LangChainPrompt(vars_in_data_dict={"Data": "Data", "Content": "Content"})
        self.assertEqual(prompt.SUPPORT_VERSIONS, ["v1"])
        self.assertEqual(set(prompt.prompt_vars_in_prompt), {"Data", "Content"})
        completion_prompt_string = prompt.generate_completion_prompt({"Data": "Test Data", "Content": "Test Content"})
        self.assertEqual(completion_prompt_string,
                         "This is a test prompt for the completion API.\n\nInput: \"Test Data\"\n#Crawled Landing Page: \"Test Content\"\n#Result")

    def test_jinja2_prompt_loading(self):
        """Test loading a Jinja2 prompt and checking its functionality."""
        prompt = Jinja2Prompt(vars_in_data_dict={"Data": "Data", "Content": "Content"})
        self.assertEqual(prompt.SUPPORT_VERSIONS, ["v1"])
        self.assertEqual(set(prompt.prompt_vars_in_prompt), {"Data", "Content"})
        completion_prompt_string = prompt.generate_completion_prompt({"Data": "Test Data", "Content": "Test Content"})
        self.assertEqual(completion_prompt_string,
                         "This is a test prompt for the completion API.\n\nInput: \"Test Data\"\n#Crawled Landing Page: \"Test Content\"\n#Result")

    def test_cdex_prompt_loading(self):
        # Test loading a CDEX prompt
        prompt = CDEXPrompt(vars_in_data_dict={"Data": "Data", "Content": "Content"})
        self.assertEqual(prompt.SUPPORT_VERSIONS, ["v1"])
        self.assertEqual(set(prompt.prompt_vars_in_prompt), {"Data", "Content"})
        completion_prompt_string = prompt.generate_completion_prompt({"Data": "Test Data", "Content": "Test Content"})
        self.assertEqual(completion_prompt_string,
                         "This is a test prompt for the completion API.\n\nInput: \"Test Data\"\n#Crawled Landing Page: \"Test Content\"\n#Result")
