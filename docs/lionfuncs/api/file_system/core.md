---
title: "lionfuncs.file_system.core"
---

# lionfuncs.file_system.core

The `file_system.core` module provides core file system operations, including
reading and writing files, listing directories, and chunking content.

## Functions

### chunk_content

```python
def chunk_content(
    content: str,
    chunk_by: Literal["chars", "tokens"] = "chars",
    tokenizer: Callable[[str], list[str]] = lambda x: x.split(),
    chunk_size: int = 1024,
    overlap_ratio: float = 0.1,
    threshold: int = 100,
    **kwargs: Any,
) -> list[dict[str, Any]]
```

Splits content by characters or tokens with configurable overlap and threshold.

This function is useful for processing large text content in smaller chunks,
with options for overlapping chunks to maintain context across chunk boundaries.

#### Parameters

- **content** (`str`): The text content to chunk.
- **chunk_by** (`Literal["chars", "tokens"]`, optional): Whether to chunk by
  characters or tokens. Defaults to `"chars"`.
- **tokenizer** (`Callable[[str], list[str]]`, optional): Function to tokenize
  the content when `chunk_by="tokens"`. Defaults to `lambda x: x.split()`.
- **chunk_size** (`int`, optional): The size of each chunk in characters or
  tokens. Defaults to `1024`.
- **overlap_ratio** (`float`, optional): The ratio of overlap between adjacent
  chunks. Defaults to `0.1`.
- **threshold** (`int`, optional): Minimum size for the last chunk. If the last
  chunk is smaller than this threshold, it will be merged with the previous
  chunk. Defaults to `100`.
- **\*\*kwargs** (`Any`): Additional keyword arguments to pass to the tokenizer.

#### Returns

- `list[dict[str, Any]]`: A list of dictionaries, each representing a chunk with
  the following keys:
  - `chunk_content`: The text content of the chunk.
  - `chunk_id`: The 1-based index of the chunk.
  - `total_chunks`: The total number of chunks.
  - `chunk_size_chars`: The size of the chunk in characters.

#### Raises

- `LionFileError`: If the content is not a string or if the overlap ratio is
  invalid.

#### Example

```python
from lionfuncs.file_system import chunk_content

# Chunk by characters
text = "This is a long text that needs to be chunked into smaller pieces."
chunks = chunk_content(
    text,
    chunk_by="chars",
    chunk_size=20,
    overlap_ratio=0.1
)
for chunk in chunks:
    print(f"Chunk {chunk['chunk_id']}/{chunk['total_chunks']}: {chunk['chunk_content']}")

# Chunk by tokens (words)
chunks = chunk_content(
    text,
    chunk_by="tokens",
    chunk_size=5,
    overlap_ratio=0.2
)
for chunk in chunks:
    print(f"Chunk {chunk['chunk_id']}/{chunk['total_chunks']}: {chunk['chunk_content']}")

# Using a custom tokenizer
import nltk
nltk.download('punkt')
from nltk.tokenize import word_tokenize

chunks = chunk_content(
    text,
    chunk_by="tokens",
    tokenizer=word_tokenize,
    chunk_size=5,
    overlap_ratio=0.2
)
for chunk in chunks:
    print(f"Chunk {chunk['chunk_id']}/{chunk['total_chunks']}: {chunk['chunk_content']}")
```

### read_file

```python
async def read_file(path: Union[str, Path]) -> str
```

Asynchronously reads the contents of a file.

#### Parameters

- **path** (`Union[str, Path]`): The path to the file to read.

#### Returns

- `str`: The contents of the file.

#### Raises

- `LionFileError`: If the file is not found, permission is denied, or other I/O
  errors occur.

#### Example

```python
import asyncio
from lionfuncs.file_system import read_file

async def main():
    try:
        content = await read_file("example.txt")
        print(f"File content: {content}")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
```

### save_to_file

```python
async def save_to_file(
    text: str,
    directory: Union[str, Path],
    filename: str,
    file_exist_ok: bool = False,
    verbose: bool = False,
) -> Path
```

Asynchronously saves text to a file.

#### Parameters

- **text** (`str`): The text to save.
- **directory** (`Union[str, Path]`): The directory to save the file in.
- **filename** (`str`): The name of the file to save.
- **file_exist_ok** (`bool`, optional): Whether to overwrite the file if it
  already exists. Defaults to `False`.
- **verbose** (`bool`, optional): Whether to log the save operation. Defaults to
  `False`.

#### Returns

- `Path`: The path to the saved file.

#### Raises

- `LionFileError`: If the file already exists and `file_exist_ok` is `False`, or
  if other I/O errors occur.

#### Example

```python
import asyncio
from lionfuncs.file_system import save_to_file

async def main():
    try:
        path = await save_to_file(
            "Hello, world!",
            "output",
            "hello.txt",
            file_exist_ok=True,
            verbose=True
        )
        print(f"Saved to: {path}")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
```

### list_files

```python
def list_files(
    dir_path: Union[str, Path],
    extension: str | None = None,
    recursive: bool = False,
) -> list[Path]
```

Lists files in a directory, optionally filtering by extension and recursively.

#### Parameters

- **dir_path** (`Union[str, Path]`): The path to the directory to list files
  from.
- **extension** (`str | None`, optional): The file extension to filter by (e.g.,
  "txt", "py"). Defaults to `None`.
- **recursive** (`bool`, optional): Whether to list files recursively. Defaults
  to `False`.

#### Returns

- `list[Path]`: A list of Path objects for the files found.

#### Raises

- `LionFileError`: If the path is not a directory.

#### Example

```python
from lionfuncs.file_system import list_files

# List all files in the current directory
files = list_files(".")
print(f"All files: {files}")

# List Python files in the src directory
py_files = list_files("src", extension="py")
print(f"Python files: {py_files}")

# List all files recursively
all_files = list_files(".", recursive=True)
print(f"All files recursively: {all_files}")
```

### concat_files

```python
async def concat_files(
    data_paths: Union[str, Path, list[Union[str, Path]]],
    file_types: list[str],
    output_dir: Union[str, Path, None] = None,
    output_filename: str | None = None,
    file_exist_ok: bool = True,
    recursive: bool = True,
    verbose: bool = False,
    content_threshold: int = 0,
) -> str
```

Asynchronously concatenates multiple files.

#### Parameters

- **data_paths** (`Union[str, Path, list[Union[str, Path]]]`): The path(s) to
  the file(s) or directory(ies) to concatenate.
- **file_types** (`list[str]`): The file extensions to include (e.g., [".txt",
  ".md"]).
- **output_dir** (`Union[str, Path, None]`, optional): The directory to save the
  concatenated file in. Defaults to `None`.
- **output_filename** (`str | None`, optional): The name of the concatenated
  file. Defaults to `None`.
- **file_exist_ok** (`bool`, optional): Whether to overwrite the output file if
  it already exists. Defaults to `True`.
- **recursive** (`bool`, optional): Whether to search for files recursively.
  Defaults to `True`.
- **verbose** (`bool`, optional): Whether to log the operation. Defaults to
  `False`.
- **content_threshold** (`int`, optional): Minimum content size to include a
  file. Defaults to `0`.

#### Returns

- `str`: The concatenated content.

#### Example

```python
import asyncio
from lionfuncs.file_system import concat_files

async def main():
    # Concatenate all markdown files in the docs directory
    content = await concat_files(
        "docs",
        [".md"],
        output_dir="output",
        output_filename="all_docs.md",
        verbose=True
    )
    print(f"Concatenated content length: {len(content)}")

    # Concatenate specific files
    content = await concat_files(
        ["file1.txt", "file2.txt", "file3.txt"],
        [".txt"],
        output_dir="output",
        output_filename="combined.txt"
    )
    print(f"Concatenated content length: {len(content)}")

asyncio.run(main())
```

### dir_to_files

```python
def dir_to_files(
    directory: Union[str, Path],
    file_types: list[str] | None = None,
    ignore_errors: bool = False,
    verbose: bool = False,
    recursive: bool = True,
) -> list[Path]
```

Recursively lists files in a directory, optionally filtering by file types.

#### Parameters

- **directory** (`Union[str, Path]`): The path to the directory to list files
  from.
- **file_types** (`list[str] | None`, optional): The file extensions to include
  (e.g., [".txt", ".md"]). Defaults to `None`.
- **ignore_errors** (`bool`, optional): Whether to ignore permission and other
  errors. Defaults to `False`.
- **verbose** (`bool`, optional): Whether to log the operation. Defaults to
  `False`.
- **recursive** (`bool`, optional): Whether to search for files recursively.
  Defaults to `True`.

#### Returns

- `list[Path]`: A list of Path objects for the files found.

#### Raises

- `LionFileError`: If the path is not a directory or if permission errors occur
  and `ignore_errors` is `False`.

#### Example

```python
from lionfuncs.file_system import dir_to_files

# List all files recursively
all_files = dir_to_files(".")
print(f"All files: {all_files}")

# List Python files recursively
py_files = dir_to_files("src", file_types=[".py"])
print(f"Python files: {py_files}")

# List files with verbose logging
verbose_files = dir_to_files("docs", verbose=True)
print(f"Files in docs: {verbose_files}")
```

## Internal Functions

The following functions are used internally by the module and are not part of
the public API:

- `_create_path(directory, filename, ...)`: Creates a path for a file, handling
  directory creation and file existence checks.
- `_chunk_by_chars_internal(text, chunk_size, slice_overlap, threshold)`:
  Internal function for chunking text by characters.
- `_chunk_by_tokens_internal(tokens, chunk_size, slice_overlap, threshold)`:
  Internal function for chunking text by tokens.
