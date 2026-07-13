# prompt_manager

A prompt template management system for LLM applications.

## Features

- Supports multiple prompt formats: **CDEX** (`#placeholder#`), **Jinja2** (`{{variable}}`), and **LangChain** (JSON)
- Version management: automatically discovers and selects the latest prompt version from versioned subdirectories
- Chat and completion mode generation
- Variable mapping from data sources to prompt placeholders
- Output key extraction and renaming configuration

## Installation

```bash
pip install -e .
```

## Usage

### Define a prompt class

```python
from pathlib import Path
from prompt_manager import MyPromptBase

class MyPrompt(MyPromptBase):
    DEFAULT_PROMPT_DIR = Path("prompt_lib") / "my_prompts"
    DEFAULT_PROMPT_FILE = "gen_output.jinja2"
    DEFAULT_VERSION = "v1"
    DEFAULT_PROMPT_TYPE = "jinja2"
    KEYS_TO_EXTRACT = ["Output", "Reasoning"]

    def __init__(self, vars_in_data_dict=None, output_key_rename_dict=None, version=DEFAULT_VERSION):
        prompt_path = self.DEFAULT_PROMPT_DIR / version / self.DEFAULT_PROMPT_FILE
        super().__init__(
            description="My custom prompt",
            prompt_path=prompt_path,
            prompt_type=self.DEFAULT_PROMPT_TYPE,
            keys_to_extract=self.KEYS_TO_EXTRACT,
            vars_in_data_dict=vars_in_data_dict,
            output_key_rename_dict=output_key_rename_dict,
            version=version,
        )
```

### Generate prompts from a DataFrame

```python
prompt = MyPrompt(vars_in_data_dict={"InputCol": "DataColumn"})
prompt_list = df.apply(prompt.generate_completion_prompt, axis=1)
```

### Use the low-level generator directly

```python
from prompt_manager import PromptGeneratorLight, PromptMode

gen = PromptGeneratorLight("path/to/prompt.jinja2", prompt_style="jinja2")
result = gen.generate_prompt(data_row, vars_in_data=["ColA"], vars_in_prompt=["VarA"], prompt_mode=PromptMode.CHAT)
```

## Prompt Format Version Structure

Prompts are organized into versioned subdirectories:

```
prompt_lib/
    my_prompts/
        v1/
            gen_output.jinja2
        v2/
            gen_output.jinja2
```

The `get_versions()` and `get_latest_version()` class methods automatically discover and sort versions
(e.g. `v2.0.1 > v0.11 > v0.2.1 > v0.2 > v0.1`).

## Prompt Visualization Plugin

`prompt_visualization` provides a browser-based UI to:

- Navigate prompt hierarchy
- Read and review prompt syntax and undeclared variables
- Edit and save a specific prompt version
- Create a new prompt version by cloning from latest (or a chosen source version)

### Run from CLI

```bash
prompt-visualization /path/to/prompt_lib_cleaned_jinja2 --host 127.0.0.1 --port 8010
```

If you do not install the package, run directly with `python -m`:

```bash
python -m prompt_manager.visualizer.prompt_visualization /path/to/prompt_lib_cleaned_jinja2 --host 127.0.0.1 --port 8010
```

Then open:

```text
http://127.0.0.1:8010/
```

### Run from Python

```python
from pathlib import Path
from prompt_manager import run_prompt_visualization

run_prompt_visualization(Path("prompt_lib_cleaned_jinja2"), host="127.0.0.1", port=8010)
```

### API endpoints

- `GET /api/tree`: list prompt tree
- `GET /api/prompt?path=<relative_jinja2_path>`: read prompt + review
- `GET /api/review?path=<relative_jinja2_path>`: review syntax/variables
- `POST /api/save`: save prompt file
- `POST /api/create_version`: create new version directory by cloning

### How-To: Use Prompt Visualizer

1. Start the visualizer server.

```bash
prompt-visualization /path/to/prompt_lib_cleaned_jinja2 --host 127.0.0.1 --port 8010
```

2. Open your browser and go to `http://127.0.0.1:8010/`.

3. Browse the prompt tree in the left panel and click any `.jinja2` file.
    - The editor loads prompt content.
    - The review panel shows syntax validity, undeclared variables, and file metadata.

4. Edit and save a prompt.
    - Modify content in the editor.
    - Click **Save**.
    - The file is written to disk and review metadata is refreshed.

5. Review a prompt without saving.
    - Click **Review** to re-run syntax and variable checks on current content.

6. Create a new version from an existing family.
    - Fill `family path` (example: `autolabeling/accuracy`).
    - Optional: fill `source version` (example: `v9.1`). If empty, latest version is used.
    - Fill `new version` (example: `v10`).
    - Click **Create Version**.

7. Re-open the tree and verify the new version folder was created.

#### Notes

- Visualizer only edits `.jinja2` files.
- `new version` must follow version naming style like `v1`, `v2.1`, `v3.0.5`.
- Paths are validated to stay inside the configured prompt library root.

#### Security

The visualizer is an **unauthenticated** local tool that can read, write, and
create prompt files within the configured library root. It is intended for use
on your own machine only. Keep the default host (`127.0.0.1`) and do **not** bind
it to a public interface (e.g. `0.0.0.0`) or expose it to untrusted networks.
