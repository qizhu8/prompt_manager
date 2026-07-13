import re
import warnings
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch

from prompt_manager import MyPromptBase, PromptMode

prompt_base = Path("./tests/test_prompt")


class DummyPrompt(MyPromptBase):
    DEFAULT_PROMPT_DIR = prompt_base / "version_test"
    DEFAULT_PROMPT_FILE = "test_prompt.txt"
    DEFAULT_VERSION = None
    DEFAULT_PROMPT_TYPE = "cdex"
    KEYS_TO_EXTRACT = []
    DESCRIPTION = "Test prompt"

    def __init__(self, prompt_type: str = DEFAULT_PROMPT_TYPE,
                 vars_in_data_dict: dict = dict(),
                 output_key_rename_dict: dict = None,
                 keys_to_extract: list = KEYS_TO_EXTRACT,
                 version: str = DEFAULT_VERSION):
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


class TestPromptVersionCheck(TestCase):

    def setUp(self) -> None:
        self.prompt = DummyPrompt(vars_in_data_dict={"Data": "Data", "Content": "Content"})

    def test_prompt_version_search(self):
        # Check if the prompt version is correctly set
        self.assertEqual(self.prompt.SUPPORT_VERSIONS, ["v2.0.1", "v0.11", "v0.2.1", "v0.2", "v0.1"])

    def test_default_prompt_version(self):
        self.assertEqual(self.prompt.DEFAULT_VERSION, "v2.0.1")
