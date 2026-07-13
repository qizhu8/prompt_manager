"""
This class is the base class for all prompts. It is used to build the prompt from the prompt file and set up the
variables, which will simplify the selection of prompt.
"""
import os
import re
from pathlib import Path
from typing import List, Tuple, Union

from prompt_manager.prompt_generator_light import (SUPPORTED_PROMPT_TYPES,
                                                   PromptGeneratorLight,
                                                   PromptMode)


class MyPromptBase:
    """
    Prompt Base Class is a base prompt template class for each task.
    """
    DEFAULT_PROMPT_DIR = Path("data") / "prompt_lib" / "cdex" / "attractiveness"
    DEFAULT_PROMPT_FILE = "title_attractiveness_eval.txt"
    DEFAULT_PROMPT_TYPE = "cdex"
    DEFAULT_VERSION = None
    SUPPORT_VERSIONS = None

    def __new__(cls, *args, **kwargs):
        assert cls.DEFAULT_PROMPT_DIR.exists(), f"Default prompt path {cls.DEFAULT_PROMPT_DIR} does not exist"
        if not cls.SUPPORT_VERSIONS:
            cls.SUPPORT_VERSIONS = cls.get_versions(cls.DEFAULT_PROMPT_DIR, cls.DEFAULT_PROMPT_FILE)
        if not cls.DEFAULT_VERSION:
            cls.DEFAULT_VERSION = cls.get_latest_version(cls.DEFAULT_PROMPT_DIR, cls.DEFAULT_PROMPT_FILE)
        return super(MyPromptBase, cls).__new__(cls)

    def __init__(self,
                 description: str,
                 prompt_path: Union[str, Path],
                 prompt_type: str = DEFAULT_PROMPT_TYPE,
                 keys_to_extract: Union[List, Tuple] = None,
                 vars_in_data_dict: dict = None,
                 output_key_rename_dict: dict = None,
                 version: str = None,
                 jinja_args: dict = None,
                 ) -> None:
        """
        The base class for all prompts.
        The following will be done by the base class:
        1. Load the prompt from file
        2. figure out template names in the prompt
        3. set up empty variables for keys_to_extract and prepare variable to store prompt_vars_in_data

        For vars_in_data_dict, the key is the variable name in the prompt and the value is the variable name in the data.
        For output_key_rename_dict, the key is the key in the output of the llm model and the value is the new key name.
        """
        self.description = description
        self.prompt_path = Path(prompt_path)
        self.prompt_type = prompt_type
        self.version = version if version else self.get_latest_version(
            self.DEFAULT_PROMPT_DIR, self.DEFAULT_PROMPT_FILE)

        print(f"Using prompt version: {self.version}")
        print(f"Loading prompt from {description}")

        # Input sanity check
        assert self.prompt_type in SUPPORTED_PROMPT_TYPES, f"Prompt type {self.prompt_type} not supported. Supported types: {SUPPORTED_PROMPT_TYPES}"

        # step 0: check if the version is supported
        assert version in self.__class__.SUPPORT_VERSIONS, f"Version {version} not supported. Supported versions: {self.__class__.SUPPORT_VERSIONS}"
        assert self.prompt_path.exists(), f"Prompt file {self.prompt_path} does not exist"

        # step 1: load prompt from file
        self.prompt = PromptGeneratorLight(prompt_path, prompt_type, jinja_args=jinja_args)

        # step 2: extract the template names in the prompt
        self.prompt_vars_in_prompt = self.prompt.placeholder_name_list

        # step 3: set up empty variables for keys_to_extract and prepare variable to store prompt_vars_in_data
        if isinstance(keys_to_extract, str):
            self.keys_to_extract = [keys_to_extract]
            raise UserWarning(
                ("Converting keys_to_extract from string to a single-element tuple. You may forgot to add a comma at"
                 " the end of the string."))
        else:
            self.keys_to_extract = keys_to_extract if keys_to_extract else ()

        self.data_vars = None
        self.keys_to_rename = dict()

        # step 4: if vars_in_data_dict is provided, set the prompt_vars_in_data
        if vars_in_data_dict:
            self.set_data_vars(**vars_in_data_dict)

        # step 5: if output_key_rename_dict is provided, set the keys to rename
        if output_key_rename_dict:
            self.set_keys_to_rename(output_key_rename_dict)

    @classmethod
    def get_versions(cls, prompt_dir: Union[str, Path], prompt_file: str) -> dict:
        """Get the list versions of the prompt, sorted by version number in descending order.
            v1 < v2 < v3
            v1 < v1.1 < v1.2
            v1.1 < v1.11
            v1.1.2 < v1.1.3 < v1.2
        """
        versions = list()
        prompt_dir = Path(prompt_dir)
        for name in os.listdir(prompt_dir):
            if os.path.isdir(prompt_dir / name):
                if os.path.exists(prompt_dir / name / prompt_file):
                    versions.append(name)
                else:
                    continue

        versions.sort(key=lambda x: list(map(int, re.findall(r'\d+', x))), reverse=True)

        return versions

    @classmethod
    def get_latest_version(cls, prompt_dir: Union[str, Path], prompt_file: str) -> str:
        """Get the latest version of the prompt. Since the get_versions method returns a list of versions sorted in descending order,
        the first element in the list is the latest version.
        """
        versions = cls.get_versions(prompt_dir, prompt_file)
        if not versions:
            raise ValueError(f"No versions found for prompt {prompt_file} in {prompt_dir}")

        # Sort the versions in reverse order based on the numeric values
        return versions[0] if versions else None

    def _set_keys_to_extract(self, keys_to_extract):
        """Set which keys to extract from the output of the llm model"""
        self.keys_to_extract = keys_to_extract

    def set_keys_to_rename(self, keys_to_rename: dict):
        """Set which keys to rename from the output of the llm model"""
        # check whether the keys to rename are in the keys to extract
        self.keys_to_rename = {}
        for key in keys_to_rename:
            if key not in self.keys_to_extract:
                raise ValueError(f"Key '{key}' not in keys_to_extract. Keys to extract: {self.keys_to_extract}")
            self.keys_to_rename[key] = keys_to_rename[key]

    def set_data_vars(self, **args):
        """Set the variables that will be used in the prompt
            key: variable name in the prompt
            value: variable name in the data
        """
        self.data_vars = list()
        # check if all the prompt variables are provided
        missing_vars = []
        for prompt_var in self.prompt_vars_in_prompt:
            if prompt_var not in args:
                missing_vars.append(prompt_var)

        if missing_vars:
            raise ValueError(
                f"Prompt variables {missing_vars} not provided. Expected variables: {self.prompt_vars_in_prompt}")

        for prompt_var in self.prompt_vars_in_prompt:
            self.data_vars.append(args[prompt_var])

    def generate_prompt(self, data: dict, prompt_mode: PromptMode) -> str:
        """Generate the prompt string"""
        if not self.data_vars:
            raise ValueError("Data variables not set. Use set_data_vars() to set the data variables")

        return self.prompt.generate_prompt(data, self.data_vars, self.prompt_vars_in_prompt, prompt_mode=prompt_mode)

    def generate_chat_prompt(self, data: dict) -> str:
        """Generate the chat prompt string"""
        return self.generate_prompt(data, prompt_mode=PromptMode.CHAT)

    def generate_completion_prompt(self, data: dict) -> str:
        """Generate the completion prompt string"""
        return self.generate_prompt(data, prompt_mode=PromptMode.COMPLETION)

    def dump_prompt(self, output_json_file: Union[str, Path] = None):
        """Save the prompt to a langchain json file"""
        if not output_json_file:
            if r"/cdex/" in str(self.prompt_path):
                output_json_file = str(self.prompt_path.with_suffix(".json")).replace("/cdex/", "/langchain/")
            else:
                assert False, "Prompt is already in langchain format. Please provide a different output file."

        assert output_json_file.endswith(".json"), "Output file must be a json file"
        self.prompt.save(output_json_file)

    def __str__(self) -> str:
        s = f"Prompt: {self.__class__.__name__}\n"
        s += f"{self.description}\n"
        s += f"Prompt path: {self.prompt_path}\n"
        s += "Prompt Placeholder | Data Variable\n"
        for i in range(len(self.prompt_vars_in_prompt)):
            if self.data_vars and i < len(self.data_vars):
                s += f"\t{i+1}: {self.prompt_vars_in_prompt[i]} | {self.data_vars[i]}\n"
            else:
                s += f"\t{i+1}: {self.prompt_vars_in_prompt[i]} | None\n"

        s += f"Keys to extract: \n"
        for idx, key in enumerate(self.keys_to_extract):
            if key in self.keys_to_rename:
                s += f"\t{idx+1}: {key} -> {self.keys_to_rename[key]}\n"
            else:
                s += f"\t{idx+1}: {key}\n"
        return s
