---
title: "File System Utilities Guide"
---

# File System Utilities Guide

This guide covers how to use the `lionfuncs.file_system` module for file
operations, including reading, writing, listing, and processing files, as well
as media-specific operations.

## Introduction

The `lionfuncs.file_system` module provides a set of utilities for working with
files and directories. It includes both synchronous and asynchronous functions
for common file operations, as well as specialized utilities for media files
like images and PDFs.

## Core File Operations

### Reading Files

The `read_file` function provides an asynchronous way to read file contents:

```python
import asyncio
from lionfuncs.file_system import read_file

async def main():
    # Read a text file
    content = await read_file("example.txt")
    print(f"File content: {content}")

asyncio.run(main())
```

### Writing Files

The `save_to_file` function allows you to asynchronously write content to a
file:

```python
import asyncio
from lionfuncs.file_system import save_to_file

async def main():
    # Create some content
    content = "Hello, world!"

    # Save to a file
    file_path = await save_to_file(
        content,
        directory="output",
        filename="example.txt",
        file_exist_ok=False,  # Will raise an error if file exists
        verbose=True,         # Log when file is saved
    )

    print(f"File saved to: {file_path}")

asyncio.run(main())
```

The `save_to_file` function automatically creates the directory if it doesn't
exist, and can handle various file naming options:

```python
import asyncio
from lionfuncs.file_system import save_to_file

async def main():
    content = "Example content"

    # Save with timestamp in filename
    file_path = await save_to_file(
        content,
        directory="logs",
        filename="log.txt",
        timestamp=True,           # Add timestamp to filename
        timestamp_format="%Y%m%d_%H%M%S",  # Custom timestamp format
        time_prefix=True,         # Put timestamp before filename
        file_exist_ok=True,       # Overwrite if file exists
    )

    print(f"Log saved to: {file_path}")  # e.g., logs/20250519_123045_log.txt

asyncio.run(main())
```

### Listing Files

The `list_files` function provides a way to list files in a directory:

```python
from lionfuncs.file_system import list_files

# List all files in a directory
files = list_files("data")
print(f"Found {len(files)} files")

# List only Python files
python_files = list_files("src", extension="py")
print(f"Found {len(python_files)} Python files")

# List files recursively
all_files = list_files("project", recursive=True)
print(f"Found {len(all_files)} files in all subdirectories")
```

The `dir_to_files` function provides more advanced directory scanning:

```python
from lionfuncs.file_system import dir_to_files

# List specific file types
image_files = dir_to_files(
    "images",
    file_types=[".jpg", ".png", ".gif"],
    recursive=True,
    ignore_errors=True,  # Skip directories with permission errors
    verbose=True,        # Log scanning progress
)

print(f"Found {len(image_files)} image files")
```

## Content Processing

### Chunking Content

The `chunk_content` function allows you to split large text content into
manageable chunks:

```python
from lionfuncs.file_system import chunk_content, read_file
import asyncio

async def main():
    # Read a large file
    content = await read_file("large_document.txt")

    # Split by characters
    chunks = chunk_content(
        content,
        chunk_by="chars",     # Split by characters
        chunk_size=1000,      # 1000 characters per chunk
        overlap_ratio=0.1,    # 10% overlap between chunks
        threshold=100,        # Minimum size for the last chunk
    )

    print(f"Split into {len(chunks)} chunks")
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i+1}/{len(chunks)}: {len(chunk['chunk_content'])} characters")

    # Split by tokens (words)
    token_chunks = chunk_content(
        content,
        chunk_by="tokens",    # Split by tokens (words)
        chunk_size=200,       # 200 tokens per chunk
        overlap_ratio=0.1,    # 10% overlap
        threshold=50,         # Minimum size for last chunk
    )

    print(f"Split into {len(token_chunks)} token chunks")

asyncio.run(main())
```

### Concatenating Files

The `concat_files` function allows you to combine multiple files into a single
text:

```python
import asyncio
from lionfuncs.file_system import concat_files

async def main():
    # Concatenate all text files in a directory
    combined_text = await concat_files(
        "documents",          # Directory to scan
        file_types=[".txt"],  # Only include .txt files
        recursive=True,       # Include subdirectories
        output_dir="output",  # Save output here
        output_filename="combined.txt",  # Output filename
        file_exist_ok=True,   # Overwrite if exists
        verbose=True,         # Log progress
        content_threshold=10, # Skip files with less than 10 characters
    )

    print(f"Combined text length: {len(combined_text)} characters")

asyncio.run(main())
```

## Media Operations

The `lionfuncs.file_system.media` module provides utilities for working with
media files like images and PDFs.

### Working with Images

The `read_image_to_base64` function allows you to read an image file and convert
it to a base64 string:

```python
import asyncio
from lionfuncs.file_system.media import read_image_to_base64

async def main():
    # Read an image and convert to base64
    base64_data = await read_image_to_base64("image.jpg")

    # Use in HTML
    html = f'<img src="data:image/jpeg;base64,{base64_data}" alt="Image">'

    # Save the HTML
    with open("image.html", "w") as f:
        f.write(html)

    print(f"HTML with embedded image saved to image.html")

asyncio.run(main())
```

### Working with PDFs

The `pdf_to_images` function converts PDF pages to images:

```python
from lionfuncs.file_system.media import pdf_to_images

# Convert PDF to images
image_paths = pdf_to_images(
    pdf_path="document.pdf",
    output_folder="pdf_images",
    fmt="jpeg",              # Output format
    dpi=300,                 # Resolution
)

print(f"Converted PDF to {len(image_paths)} images")
for path in image_paths:
    print(f"  - {path}")
```

Note: To use the `pdf_to_images` function, you need to install the media extras:

```bash
pip install lionfuncs[media]
```

## Combining with Other lionfuncs Modules

### With async_utils

```python
import asyncio
from lionfuncs.file_system import read_file, save_to_file
from lionfuncs.async_utils import alcall
from pathlib import Path

async def process_file(file_path):
    # Read the file
    content = await read_file(file_path)

    # Process the content (e.g., convert to uppercase)
    processed_content = content.upper()

    # Save the processed content
    output_path = await save_to_file(
        processed_content,
        "output",
        f"processed_{Path(file_path).name}",
        file_exist_ok=True,
    )

    return output_path

async def main():
    # List of files to process
    files = ["file1.txt", "file2.txt", "file3.txt"]

    # Process all files concurrently with a max concurrency of 2
    output_paths = await alcall(
        files,
        process_file,
        max_concurrent=2,
    )

    print(f"Processed files: {output_paths}")

asyncio.run(main())
```

### With network module

```python
import asyncio
from lionfuncs.file_system import save_to_file
from lionfuncs.network import AsyncAPIClient

async def download_file(url, filename):
    async with AsyncAPIClient() as client:
        # Download the file
        response = await client.request("GET", url)

        # Save the response content
        file_path = await save_to_file(
            response,
            "downloads",
            filename,
            file_exist_ok=True,
        )

        return file_path

async def main():
    # Download a file
    file_path = await download_file(
        "https://example.com/sample.txt",
        "sample.txt"
    )

    print(f"Downloaded file to: {file_path}")

asyncio.run(main())
```

## Best Practices

1. **Use Async Functions**: Prefer the asynchronous functions (`read_file`,
   `save_to_file`) for I/O operations to avoid blocking the event loop.

2. **Handle Errors**: Always handle potential errors like `LionFileError` when
   working with files.

3. **Create Directories**: The file system functions automatically create
   directories as needed, but be explicit about where files are saved.

4. **Manage Concurrency**: When processing multiple files, use `alcall` from
   `lionfuncs.async_utils` to control concurrency.

5. **Chunk Large Files**: Use `chunk_content` for processing large files to
   avoid memory issues.

6. **Media Handling**: Install the media extras (`pip install lionfuncs[media]`)
   when working with images and PDFs.

## Conclusion

The `lionfuncs.file_system` module provides a comprehensive set of utilities for
working with files and directories. By combining these utilities with other
`lionfuncs` modules, you can build robust and efficient file processing
workflows.
