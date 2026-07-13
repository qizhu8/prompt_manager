# Template Converter Guide

The `TemplateConverter` class provides utilities to migrate templates between different formats: **CDEX**, **LangChain**, and **Jinja2**.

## Overview

| Format | Syntax | Example | Use Case |
|--------|--------|---------|----------|
| **CDEX** | `#placeholder#` | `Hello #name#` | Legacy format, simple text substitution |
| **LangChain** | `{variable}` | `Hello {name}` | Python f-string style, metadata-rich JSON files |
| **Jinja2** | `{{ variable }}` | `Hello {{ name }}` | Modern, supports control structures (if/for/filters) |

## Quick Start

### CDEX → Jinja2 Conversion

```python
from prompt_manager import TemplateConverter

# Convert a simple string
cdex_text = "Hello #name#, your score is #score#"
jinja2_text = TemplateConverter.cdex_to_jinja2(cdex_text)
# Result: "Hello {{ name }}, your score is {{ score }}"

# Convert a file
TemplateConverter.cdex_file_to_jinja2(
    cdex_file_path="template.txt",
    output_file_path="template.jinja2"
)

# Batch convert all CDEX files in a directory
converted = TemplateConverter.batch_convert_cdex_files(
    source_dir="prompts/",
    overwrite=True
)
```

### LangChain → Jinja2 Conversion

```python
# Convert LangChain template string
langchain_text = "Hello {name}, your score is {score}"
jinja2_text = TemplateConverter.langchain_to_jinja2(langchain_text)
# Result: "Hello {{ name }}, your score is {{ score }}"

# Convert LangChain JSON file with metadata extraction
content, output_path, metadata = TemplateConverter.langchain_json_to_jinja2(
    langchain_json_path="template.json",
    output_file_path="template.jinja2"
)

# Batch convert all LangChain JSON files
converted = TemplateConverter.batch_convert_langchain_files(
    source_dir="langchain_prompts/",
    overwrite=True
)
```

## Variable Extraction

Extract all variables from a template to understand dependencies:

```python
# Extract from CDEX
cdex_vars = TemplateConverter.extract_cdex_variables(
    "User #user_id# has email #email#"
)
# Result: {'user_id', 'email'}

# Extract from LangChain
lc_vars = TemplateConverter.extract_langchain_variables(
    "User {user_id} has email {email}"
)
# Result: {'user_id', 'email'}

# Extract from Jinja2
jinja2_vars = TemplateConverter.extract_jinja2_variables(
    "User {{ user_id }} has email {{ email }}"
)
# Result: {'user_id', 'email'}
```

## LangChain Metadata Handling

When converting LangChain JSON files, the converter preserves and extracts all metadata:

```python
content, output_path, metadata = TemplateConverter.langchain_json_to_jinja2(
    "template.json"
)

# Metadata dictionary contains:
metadata = {
    "input_variables": ["name", "score"],
    "optional_variables": ["comment"],
    "output_parser": None,
    "partial_variables": {},
    "metadata": None,
    "tags": ["nlp", "classification"],
    "name": "feature_extractor",
    "template_format": "f-string"
}

# Generate YAML documentation of metadata
yaml_doc = TemplateConverter.langchain_metadata_to_yaml(metadata)
```

## File Operations

### Single File Conversion

**CDEX to Jinja2:**
```python
content, output_path = TemplateConverter.cdex_file_to_jinja2(
    cdex_file_path="template.txt",
    output_file_path=None  # Auto-generates: template.jinja2
)
```

**LangChain to Jinja2:**
```python
content, output_path, metadata = TemplateConverter.langchain_json_to_jinja2(
    langchain_json_path="template.json",
    output_file_path=None  # Auto-generates: template.jinja2
)
```

### Batch Operations

Convert entire directories recursively:

```python
# CDEX batch conversion
TemplateConverter.batch_convert_cdex_files(
    source_dir="old_prompts/",
    output_dir="new_prompts/",
    overwrite=False  # Skip if .jinja2 already exists
)

# LangChain batch conversion
TemplateConverter.batch_convert_langchain_files(
    source_dir="langchain/",
    output_dir="jinja2/",
    overwrite=True
)
```

Returns list of `(source_path, output_path)` or `(source_path, output_path, metadata)` tuples.

## Real-World Examples

### Example 1: Product Evaluation Template

**Before (CDEX):**
```
Product Evaluation Task:

Product Name: #product_name#
Brand: #brand#
Category: #category#

Evaluation Guidelines:
1. Analyze #product_name# features
2. Compare with #brand# positioning
3. Check if fits #category#

Output format:
Rating: <rating>VALUE</rating>
```

**After (Jinja2):**
```
Product Evaluation Task:

Product Name: {{ product_name }}
Brand: {{ brand }}
Category: {{ category }}

Evaluation Guidelines:
1. Analyze {{ product_name }} features
2. Compare with {{ brand }} positioning
3. Check if fits {{ category }}

Output format:
Rating: <rating>VALUE</rating>
```

Now you can enhance this with Jinja2 features:
```jinja2
Product Evaluation Task:

Product Name: {{ product_name }}
Brand: {{ brand }}
Category: {{ category }}

{% if detail_level == 'full' %}
Comprehensive Evaluation:
1. Analyze {{ product_name }} features in detail
2. Compare with {{ brand }} positioning and market trends
3. Check if fits {{ category }} and alternative categories
{% else %}
Quick Evaluation:
1. Analyze {{ product_name }} features
2. Compare with {{ brand }} positioning
3. Check if fits {{ category }}
{% endif %}

Output format:
Rating: <rating>VALUE</rating>
```

### Example 2: Marketing Campaign Template

**Before (LangChain):**
```json
{
  "input_variables": ["audience", "product", "budget", "timeline"],
  "template": "Create a {audience} campaign for {product} with budget {budget} by {timeline}."
}
```

**After (Jinja2 with dynamic loops):**
```jinja2
Create a {{ audience }} campaign for {{ product }} with budget {{ budget }} by {{ timeline }}.

{% for channel in channels %}
- {{ channel }}: Allocate budget for this channel
{% endfor %}

Expected metrics:
{% for metric in metrics %}
- {{ metric }}: Track this metric
{% endfor %}
```

## Migration Strategy

### Step 1: Discover Variables
```python
variables = TemplateConverter.extract_cdex_variables(template_text)
print(f"Found {len(variables)} variables: {variables}")
```

### Step 2: Batch Convert
```python
converted_files = TemplateConverter.batch_convert_cdex_files(
    source_dir="templates/",
    overwrite=True
)
print(f"Converted {len(converted_files)} files")
```

### Step 3: Verify Conversion
```python
# Check the converted files manually for any issues
# Update any complex templates to use Jinja2 features
```

### Step 4: Enhance with Jinja2
```jinja2
# Add control structures to templates
{% if condition %}
    ...
{% endif %}

# Add loops
{% for item in items %}
    ...
{% endfor %}

# Use filters
{{ variable | upper }}
{{ variable | length }}
```

## Supported Features

### Patterns Recognized
- ✅ CDEX: `#variable_name#` (underscores and numbers allowed)
- ✅ LangChain: `{variable_name}` (f-string style)
- ✅ Jinja2: `{{ variable_name }}` (with flexible spacing)

### Edge Cases Handled
- ✅ Multiple instances of same variable
- ✅ Newlines and multi-line templates
- ✅ Special characters around placeholders
- ✅ No placeholders (static templates)
- ✅ Complex variable names with underscores and numbers
- ✅ Nested LangChain metadata structures

### Error Handling
- ✅ Missing file detection with `FileNotFoundError`
- ✅ Empty template handling
- ✅ Graceful degradation for invalid files in batch operations
- ✅ Customizable output paths

## API Reference

### String Conversion Functions

```python
# CDEX to Jinja2
TemplateConverter.cdex_to_jinja2(cdex_text: str) -> str

# LangChain to Jinja2
TemplateConverter.langchain_to_jinja2(langchain_text: str) -> str
```

### Variable Extraction Functions

```python
TemplateConverter.extract_cdex_variables(text: str) -> Set[str]
TemplateConverter.extract_langchain_variables(text: str) -> Set[str]
TemplateConverter.extract_jinja2_variables(text: str) -> Set[str]
```

### File Conversion Functions

```python
TemplateConverter.cdex_file_to_jinja2(
    cdex_file_path: Path,
    output_file_path: Optional[Path] = None
) -> Tuple[str, Path]

TemplateConverter.langchain_json_to_jinja2(
    langchain_json_path: Path,
    output_file_path: Optional[Path] = None
) -> Tuple[str, Path, Dict]
```

### Batch Conversion Functions

```python
TemplateConverter.batch_convert_cdex_files(
    source_dir: Path,
    output_dir: Optional[Path] = None,
    overwrite: bool = False
) -> List[Tuple[Path, Path]]

TemplateConverter.batch_convert_langchain_files(
    source_dir: Path,
    output_dir: Optional[Path] = None,
    overwrite: bool = False
) -> List[Tuple[Path, Path, Dict]]
```

### Metadata Handling

```python
TemplateConverter.langchain_metadata_to_yaml(metadata: Dict) -> str
```

## Testing

Comprehensive test suite with 32 test cases covers:

- ✅ Simple format conversions
- ✅ Multiple variable instances
- ✅ Newlines and special characters
- ✅ Variable extraction consistency
- ✅ File operations
- ✅ Batch conversions
- ✅ Error handling
- ✅ Edge cases
- ✅ Round-trip conversions

Run tests:
```bash
pytest tests/test_prompt_converter.py -v
```

## Performance Considerations

- **Regex-based extraction**: O(n) where n is template length
- **String substitution**: O(n) for conversion
- **Batch processing**: Parallel-safe, converts directory recursively
- **Memory**: Negligible, processes one file at a time

## Next Steps

After conversion:
1. Replace all `#placeholder#` with Jinja2 equivalent
2. Replace all `{variable}` with Jinja2 equivalent
3. Enhance templates with Jinja2 features (if/for/filters)
4. Test with `PromptGeneratorLight` using dynamic rendering
5. Update prompt files in version control

Example of enhanced Jinja2 template:
```jinja2
{% if evaluation_type == 'detailed' %}
    # Full Evaluation of {{ product_name }}
    {% for category in categories %}
        ## {{ category }}
        - Analyze {{ product_name }} in context of {{ category }}
    {% endfor %}
{% else %}
    # Quick Summary of {{ product_name }}
{% endif %}
```

See [Dynamic Jinja2 Rendering](../tests/test_dynamic_jinja2_rendering.py) for implementation examples.
