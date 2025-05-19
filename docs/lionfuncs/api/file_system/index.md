---
title: "lionfuncs.file_system"
---

# lionfuncs.file_system

The `file_system` module provides utilities for file system operations,
including reading and writing files, listing directories, chunking content, and
working with media files.

## Submodules

- [**core**](core.md): Core file system operations.
- [**media**](media.md): Media-specific file operations (images, PDFs).

## Functions

The `file_system` module re-exports all functions from its submodules, so you
can import them directly from `lionfuncs.file_system`:

### From core

- [`chunk_content(content, chunk_by="chars", ...)`](core.md#chunk_content):
  Split content by chars or tokens.
- [`read_file(path)`](core.md#read_file): Read file content asynchronously.
- [`save_to_file(text, directory, filename, ...)`](core.md#save_to_file): Save
  text to a file asynchronously.
- [`list_files(dir_path, extension=None, recursive=False)`](core.md#list_files):
  List files in a directory.
- [`concat_files(data_path, file_types, ...)`](core.md#concat_files):
  Concatenate multiple files asynchronously.
- [`dir_to_files(directory, file_types=None, ...)`](core.md#dir_to_files):
  Recursively list files in a directory.

### From media

- [`read_image_to_base64(image_path)`](media.md#read_image_to_base64): Read an
  image and encode to base64 asynchronously.
- [`pdf_to_images(pdf_path, output_folder, ...)`](media.md#pdf_to_images):
  Convert PDF pages to images.

## Installation

The core file system functions are included in the base `lionfuncs` package:

```bash
pip install lionfuncs
```

For media-specific functions (e.g., `pdf_to_images`), you need to install the
`media` extra:

```bash
pip install lionfuncs[media]
```

## Usage Examples

### Reading and Writing Files

```python
import asyncio
from lionfuncs.file_system import read_file, save_to_file

async def main():
    # Read a file
    content = await read_file("example.txt")
    print(f"File content: {content}")

    # Process the content
    processed_content = content.upper()

    # Save the processed content
    output_path = await save_to_file(
        processed_content,
        "output",
        "example_processed.txt",
        verbose=True
    )
    print(f"Saved to: {output_path}")

asyncio.run(main())
```

### Listing Files

```python
from lionfuncs.file_system import list_files, dir_to_files

# List files in a directory (non-recursive)
files = list_files("docs", extension="md")
print(f"Markdown files in docs: {files}")

# List files recursively
all_files = dir_to_files("src", file_types=[".py"], recursive=True)
print(f"Python files in src: {all_files}")
```

### Chunking Content

```python
import asyncio
from lionfuncs.file_system import read_file, chunk_content

async def main():
    # Read a large file
    content = await read_file("large_document.txt")

    # Chunk by characters
    chunks_by_chars = chunk_content(
        content,
        chunk_by="chars",
        chunk_size=1000,
        overlap_ratio=0.1
    )
    print(f"Number of character chunks: {len(chunks_by_chars)}")

    # Chunk by tokens (words)
    chunks_by_tokens = chunk_content(
        content,
        chunk_by="tokens",
        chunk_size=200,
        overlap_ratio=0.1
    )
    print(f"Number of token chunks: {len(chunks_by_tokens)}")

asyncio.run(main())
```

### Working with Media Files

```python
import asyncio
from lionfuncs.file_system import read_image_to_base64, pdf_to_images

async def main():
    # Read an image to base64
    base64_data = await read_image_to_base64("image.jpg")
    print(f"Base64 data length: {len(base64_data)}")

    # Convert PDF to images
    image_paths = pdf_to_images(
        "document.pdf",
        "output_images",
        fmt="jpeg",
        dpi=300
    )
    print(f"Generated images: {image_paths}")

asyncio.run(main())
```

## Error Handling

The file system functions raise `LionFileError` (from `lionfuncs.errors`) for
file-related errors:

```python
import asyncio
from lionfuncs.file_system import read_file
from lionfuncs.errors import LionFileError

async def main():
    try:
        await read_file("nonexistent.txt")
    except LionFileError as e:
        print(f"File error: {e}")

asyncio.run(main())
# Output: File error: File not found: nonexistent.txt
```
