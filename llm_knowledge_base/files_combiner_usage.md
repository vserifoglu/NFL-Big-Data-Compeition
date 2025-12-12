# files_combiner.py Usage Guide

## Purpose

`files_combiner.py` is a utility script designed to combine multiple source code files into a single text file. This is especially useful for large language models (LLMs) or code review tools that need a holistic view of the entire codebase in one place.

## How It Works

The script recursively scans a specified directory, reads all source code files (e.g., `.py`), and merges their contents into a single output file. This output can then be used as a reference for LLMs or other tools.

## How to Run

From the project root, use the following command:

```bash
python llm_knowledge_base/files_combiner.py <input_directory> -o <output_file>
```

- `<input_directory>`: The directory containing the source code you want to combine (e.g., `./src/`)
- `-o <output_file>`: (Optional) The path for the combined output file (e.g., `./llm_knowledge_base/combined_code.txt`). If not provided, a default output file will be used.

### Example

```bash
python llm_knowledge_base/files_combiner.py ./src/ -o ./llm_knowledge_base/combined_code.txt
```

This will combine all scripts in `./src/` and save the result to `./llm_knowledge_base/combined_code.txt`.

---
For further customization, review or edit `files_combiner.py` directly.
