import re
import json
import warnings
from enum import Enum
from pathlib import Path
from typing import List, Union

from jinja2 import Environment, FileSystemLoader, Undefined
from langchain_core.prompts import PromptTemplate

from prompt_manager.prompt_util import convert_prompt_to_chat_format

CONSTANT_PREFIX = "_C"


def load_langchain_prompt_template(prompt_file_path: Union[str, Path]) -> PromptTemplate:
    """Load a LangChain PromptTemplate from a legacy JSON/YAML prompt file.

    Replaces ``langchain_core.prompts.load_prompt`` (deprecated in LangChain 1.2.21
    and removed in 2.0.0). The legacy serialization format maps directly onto the
    ``PromptTemplate`` constructor, so we read it and build the template explicitly.
    """
    path = Path(prompt_file_path)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        import yaml  # imported lazily; only needed for YAML prompt files

        data = yaml.safe_load(text)
    else:
        data = json.loads(text)

    prompt_type = data.get("_type", "prompt")
    if prompt_type not in ("prompt", None):
        raise ValueError(f"Unsupported prompt _type: {prompt_type!r}")

    return PromptTemplate(
        template=data["template"],
        input_variables=data.get("input_variables", []),
        template_format=data.get("template_format", "f-string"),
        partial_variables=data.get("partial_variables", {}),
    )


class PromptMode(Enum):
    CHAT = "chat"
    COMPLETION = "completion"


SUPPORTED_PROMPT_TYPES = ["cdex", "langchain", "jinja2"]


class PromptGeneratorLight:
    """
    PromptGeneratorLight is a light-weight prompt generator that generates prompts based on a template file.
    It can load prompt templates in langchain style or CDEX style, and can also dump the prompt template to a json file
    in langchain style. Currently, we don't plan to support the CDEX style prompt template dump.

    Once loaded, the prompt generator can generate prompts based on the template and the data provided by calling the
    `generate_prompt` method with `vars_in_data` and `vars_in_prompt` arguments.
    - vars_in_data: a list of  variable names in the data table
    - vars_in_prompt: a list of variable names that match the order in the vars_in_data in the prompt template
    """

    def __init__(self, prompt_file_path: str, prompt_style: str = "langchain", jinja_args: dict = None) -> None:
        prompt_style = prompt_style.lower().strip()
        assert prompt_style in SUPPORTED_PROMPT_TYPES

        self.prompt_style = prompt_style
        self.placeholder_name_list = []
        self.warning_shown = False
        self.jinja2_env = None
        self.jinja2_template = None
        self.jinja2_args = jinja_args or {}

        if prompt_style == "langchain":
            # directly load the prompt template from file
            # Convert Path to string for the loader
            self.prompt_template = load_langchain_prompt_template(prompt_file_path)
            self.placeholder_name_list = self.prompt_template.input_variables
            print("load langchain prompt")
        elif prompt_style == "cdex":
            # load the prompt template from file and convert it to langchain style
            self.prompt_template = self.load_cdex_prompt(prompt_file_path)
            print("load CDEX prompt")
        elif prompt_style == "jinja2":
            self.load_jinja2_prompt(prompt_file_path, jinja_args)
            print("load jinja2 prompt")

        print("Vars in prompt:", self.placeholder_name_list)

    def load_cdex_prompt(self, prompt_file_path: str) -> str:
        """
        Load a CDEX style prompt template from file and convert it to langchain style.
        CDEX style prompt is a string with placeholders in the format of "#placeholder_name#".
        """
        def get_placeholder_name_from_str(prompt_str):
            # extract placeholder names from prompt of format "#placeholder_name#"
            pat = r"#(\w+)#"
            return re.findall(pat, prompt_str)

        def replace_CDEX_style_placeholder_to_langchain_style(prompt_str):
            # replace CDEX style placeholder (#placeholder#) to langchain style placeholder ({placeholder})
            prompt_str = prompt_str.replace("{", "{{").replace("}", "}}")  # escape { and }
            return re.sub(r"#(\w+)#", r"{\1}", prompt_str)

        with open(prompt_file_path, 'r', encoding="utf-8") as f:
            prompt_string = f.read()

        placeholder_name_list = list(set(get_placeholder_name_from_str(prompt_string)))

        langchain_style_prompt_str = replace_CDEX_style_placeholder_to_langchain_style(prompt_string)

        template = PromptTemplate(
            input_variables=placeholder_name_list,
            template=langchain_style_prompt_str,
            validate_template=True
        )

        self.placeholder_name_list = placeholder_name_list

        return template

    def load_jinja2_prompt(self, prompt_file_path: str, jinja_args: dict = None) -> None:
        """ Load a Jinja2 style prompt template from file for dynamic rendering.
        Jinja2 style prompt is a template file with placeholders in the format of "{{placeholder_name}}".
        It can also contain Jinja2 control structures (if/for) that will be evaluated at generation time.
        It can also contain additional Jinja2 arguments by passing a dictionary to the `jinja_args` parameter.
        """
        def get_placeholder_name_from_str(prompt_file_path: Path) -> List[str]:
            # extract placeholder names from prompt of format "{{xxxx}}" (excluding Jinja2 control structures)
            def create_collector():
                # all undefined variables will be collected in this set
                collected_variables = set()

                class CollectUndefined(Undefined):
                    def __init__(self, name, parent=None):
                        self.name = name
                        self.parent = parent
                        collected_variables.add(str(self))

                    def __str__(self):
                        if self.parent is not None:
                            return f"{self.parent}.{self.name}"
                        return self.name

                    def __getattr__(self, name: str):
                        return CollectUndefined(name, parent=self)

                return collected_variables, CollectUndefined
            
            variables, undefined_cls = create_collector()
            tmp_env = Environment(loader=FileSystemLoader(prompt_file_path.parent), undefined=undefined_cls)
            template = tmp_env.get_template(prompt_file_path.name)
            template.render({})  # empty so all variables are undefined
            return list(variables)

        prompt_file_path = Path(prompt_file_path)
        
        # Store the Jinja2 environment and template for dynamic rendering
        self.jinja2_env = Environment(
            loader=FileSystemLoader(prompt_file_path.parent),
            autoescape=False  # Don't escape since we're dealing with prompts
        )
        self.jinja2_template = self.jinja2_env.get_template(prompt_file_path.name)
        
        # Extract placeholder names for compatibility
        self.placeholder_name_list = get_placeholder_name_from_str(prompt_file_path)

    def convert_prompt_to_chat(self, prompt: str) -> List:
        """Convert the prompt to a list of messages for chat mode.
        E.g., prompt = "<|im_start|>user\nHello, how are you?\n <|im_end|> <|im_start|>assistant\nI am fine, thank you.\n<|im_end|>
        will be converted to:
        [
            {"role": "user", "content": "Hello, how are you?"},
            {"role": "assistant", "content": "I am fine, thank you."}
        ]
        """
        messages, fully_covered = convert_prompt_to_chat_format(prompt)
        if not fully_covered and not self.warning_shown:
            warnings.warn(
                "The prompt is not fully covered by chat parts. "
                "This may lead to unexpected behavior in chat mode. "
                "Please check the prompt format.",
                UserWarning
            )
            self.warning_shown = True
        return messages

    def generate_prompt(self, data: dict, vars_in_data: List, vars_in_prompt: List, prompt_mode: Union[PromptMode, str] = PromptMode.COMPLETION) -> Union[str, List]:
        """
        Generate the prompt based on the template and the data provided.
        For Jinja2 templates, this renders them dynamically with the actual data, preserving control structures.
        For other template types, uses LangChain PromptTemplate.format().
        """
        if isinstance(vars_in_data, str):
            vars_in_data = [vars_in_data]
        if isinstance(vars_in_prompt, str):
            vars_in_prompt = [vars_in_prompt]
        assert len(vars_in_data) == len(vars_in_prompt), "vars_in_data and vars_in_prompt should have the same length"

        var_mapping = {}
        for var_in_data, var_in_prompt in zip(vars_in_data, vars_in_prompt):
            if var_in_data.startswith(CONSTANT_PREFIX):
                var_mapping[var_in_prompt] = var_in_data[2:]
            elif var_in_data in data:
                var_mapping[var_in_prompt] = data[var_in_data]
            else:
                raise ValueError(f"Variable {var_in_data} not found in data")

        # Handle Jinja2 templates specially for dynamic rendering
        if self.prompt_style == "jinja2":
            # Merge var_mapping with jinja2_args for rendering
            render_context = {**self.jinja2_args, **var_mapping}
            raw_prompt = self.jinja2_template.render(**render_context)
        else:
            # For LangChain and CDEX formats, use the PromptTemplate
            raw_prompt = self.prompt_template.format(**var_mapping)
        
        if prompt_mode == PromptMode.COMPLETION.name or prompt_mode == PromptMode.COMPLETION:
            return raw_prompt
        elif prompt_mode == PromptMode.CHAT.name or prompt_mode == PromptMode.CHAT:
            # for chat mode, we need to add the system message
            return self.convert_prompt_to_chat(raw_prompt)
        else:
            raise ValueError(f"Unsupported prompt mode: {prompt_mode}")

    def save(self, path: str):
        """Save the prompt template. For LangChain format, saves to JSON. For Jinja2, writes the template."""
        if self.prompt_style == "jinja2":
            # For Jinja2, we can't convert it to LangChain format with control structures preserved
            raise NotImplementedError(
                "Saving Jinja2 templates with control structures is not supported. "
                "Jinja2 templates must be saved directly as .jinja2 files."
            )
        else:
            # For LangChain and CDEX formats
            self.prompt_template.save(path)
