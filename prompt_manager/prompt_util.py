import re
from typing import List, Tuple, Union

chat_part_pat = re.compile(r"<\|im_start\|>(system|user|assistant)([\w\W]*?)<\|im_end\|>")
chat_last_part_pat = re.compile(r"<\|im_start\|>assistant([\w\W]*?)$")


def is_prompt_matches_endpoint_mode(prompt: Tuple[str, List], endpoint_mode: str) -> bool:
    """
    Check if the prompt matches the endpoint mode. E.g., if the endpoint mode is "COMPLETION", the prompt should be a string.
    If the endpoint mode is "CHAT", the prompt should be a list of tuples, where each tuple contains two strings: (role, content).
    """
    if endpoint_mode == "COMPLETION":
        return isinstance(prompt, str)
    if endpoint_mode == "CHAT":
        if isinstance(prompt, list) or isinstance(prompt, tuple):
            for element in prompt:
                if len(element) != 2 or not isinstance(element[0], str) or not isinstance(element[1], str):
                    return False
            return True
        return True


def convert_prompt_to_chat_format(prompt: Union[str, List, Tuple]) -> Tuple[Tuple, bool]:
    """Convert the prompt to a list of messages for chat mode.
        E.g., prompt = "<|im_start|>user\nHello, how are you?\n <|im_end|> <|im_start|>assistant\nI am fine, thank you.\n<|im_end|>
        will be converted to:
        [
            {"role": "user", "content": "Hello, how are you?"},
            {"role": "assistant", "content": "I am fine, thank you."}
        ]

        return:
            messages: str, List of messages in chat format
            fully_covered: bool, Whether the prompt is fully covered by chat parts
        """
    if isinstance(prompt, list) or isinstance(prompt, tuple):
        # if the prompt is already in chat format, return it directly
        return prompt, True

    chat_parts = chat_part_pat.findall(prompt)
    fully_covered = True

    messages = []
    if not chat_parts:
        # the prompt is in completion mode
        messages.append(("user", prompt))
    else:
        prompt_remain = chat_part_pat.sub("", prompt)
        if prompt_remain.strip() != "":
            fully_covered = False

        for rst in chat_parts:
            if len(rst) != 2:
                continue
            role, content = rst
            messages.append((role, content.strip()))
    return tuple(messages), fully_covered
