import re
import warnings
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch

from prompt_manager import MyPromptBase, PromptMode

prompt_base = Path("./tests/test_prompt")


class ChatJinja(MyPromptBase):
    DEFAULT_PROMPT_DIR = prompt_base / "chat"
    DEFAULT_PROMPT_FILE = "test_prompt.jinja2"
    DEFAULT_VERSION = "v1"
    DEFAULT_PROMPT_TYPE = "jinja2"
    KEYS_TO_EXTRACT = []
    DESCRIPTION = f"Test prompt in jinja2 for chat completion"

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


class CompletionJinja(MyPromptBase):
    DEFAULT_PROMPT_DIR = prompt_base / "completion"
    DEFAULT_PROMPT_FILE = "test_prompt.jinja2"
    DEFAULT_VERSION = "v1"
    DEFAULT_PROMPT_TYPE = "jinja2"
    KEYS_TO_EXTRACT = []
    DESCRIPTION = f"Test prompt in jinja2 for completion"

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


class TestPromptModeSelector(TestCase):

    def setUp(self) -> None:
        # Initialize the test case with valid and invalid assets
        self.completion_jinja = CompletionJinja(vars_in_data_dict={"Data": "Data", "Content": "Content"}, version="v1")
        warnings.simplefilter('ignore', category=UserWarning)

    def test_populate_constant_value(self):
        """Allow constant value in the prompt template following format "_C<Const Value>".
        During the value population process, there is no need to provide a specific field name in the data dict.
        """
        self.chat_jinja = ChatJinja(vars_in_data_dict={"Data": "Data", "Content": "_CConst Value"}, version="v1")
        prompt_string = self.chat_jinja.generate_prompt(
            data={"Data": "test_data"}, prompt_mode=PromptMode.CHAT)
        expected_prompt = (
            ('system', 'This is a test prompt for the completion API.'),
            ('user', 'Input: "test_data"\n#Crawled Landing Page: "Const Value"\n#Result'),
            ('assistant', 'Dummy assistant response')
        )

        self.assertEqual(prompt_string, expected_prompt)
