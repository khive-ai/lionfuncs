---
title: "lionfuncs.file_system.media"
---

# lionfuncs.file_system.media

The `file_system.media` module provides utilities for working with media files,
such as images and PDFs.

## Installation

The media utilities require additional dependencies. Install them with:

```bash
pip install lionfuncs[media]
```

This will install the required dependencies, including `pdf2image` for PDF
processing.

## Functions

### read_image_to_base64

```python
async def read_image_to_base64(image_path: Union[str, Path]) -> str
```

Asynchronously reads an image file and encodes its content to a base64 string.

This function is useful for preparing images for embedding in HTML, JSON, or
sending over APIs that accept base64-encoded images.

#### Parameters

- **image_path** (`Union[str, Path]`): The path to the image file.

#### Returns

- `str`: A base64 encoded string representation of the image.

#### Raises

- `LionFileError`: If the file cannot be read or other OS errors occur.

#### Example

```python
import asyncio
from lionfuncs.file_system import read_image_to_base64

async def main():
    try:
        # Read an image and encode it to base64
        base64_data = await read_image_to_base64("image.jpg")

        # Print the first 50 characters of the base64 string
        print(f"Base64 data (first 50 chars): {base64_data[:50]}...")

        # Use the base64 data in an HTML img tag
        html = f'<img src="data:image/jpeg;base64,{base64_data}" alt="Image" />'
        print(f"HTML img tag created")

        # Save the HTML to a file
        with open("image.html", "w") as f:
            f.write(html)
        print("HTML file saved")

    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
```

### pdf_to_images

```python
def pdf_to_images(
    pdf_path: Union[str, Path],
    output_folder: Union[str, Path],
    fmt: str = "jpeg",
    dpi: int = 200,
    **kwargs: Any,
) -> list[Path]
```

Converts pages of a PDF file to images. Requires the 'pdf2image' library and its
dependencies (like Poppler) to be installed.

This function is useful for visualizing PDF content, extracting images from
PDFs, or preparing PDFs for OCR processing.

#### Parameters

- **pdf_path** (`Union[str, Path]`): Path to the input PDF file.
- **output_folder** (`Union[str, Path]`): Directory to save the output images.
- **fmt** (`str`, optional): Output image format (e.g., "jpeg", "png"). Defaults
  to `"jpeg"`.
- **dpi** (`int`, optional): Dots per inch for the output images. Defaults to
  `200`.
- **\*\*kwargs** (`Any`): Additional keyword arguments to pass to
  pdf2image.convert_from_path.

#### Returns

- `list[Path]`: A list of Path objects for the saved images.

#### Raises

- `LionFileError`: If pdf2image is not installed, the PDF file is not found, or
  conversion fails.

#### Additional kwargs

The function accepts all keyword arguments supported by
`pdf2image.convert_from_path()`, including:

- **first_page** (`int`): First page to convert (1-based).
- **last_page** (`int`): Last page to convert (1-based).
- **thread_count** (`int`): Number of threads to use for conversion.
- **userpw** (`str`): User password for encrypted PDFs.
- **ownerpw** (`str`): Owner password for encrypted PDFs.
- **use_cropbox** (`bool`): Use cropbox instead of mediabox.
- **strict** (`bool`): Raise exceptions on PDF syntax errors.

See the [pdf2image documentation](https://github.com/Belval/pdf2image) for more
details.

#### Example

```python
from lionfuncs.file_system import pdf_to_images
import os

# Convert all pages of a PDF to JPEG images
try:
    image_paths = pdf_to_images(
        "document.pdf",
        "output_images",
        fmt="jpeg",
        dpi=300
    )
    print(f"Generated {len(image_paths)} images:")
    for path in image_paths:
        print(f"  - {path}")

    # Convert only the first 3 pages to PNG images with higher DPI
    image_paths = pdf_to_images(
        "document.pdf",
        "output_images_png",
        fmt="png",
        dpi=600,
        first_page=1,
        last_page=3
    )
    print(f"Generated {len(image_paths)} PNG images")

except Exception as e:
    print(f"Error: {e}")
```

## Error Handling

The media functions raise `LionFileError` (from `lionfuncs.errors`) for
file-related errors:

```python
import asyncio
from lionfuncs.file_system import read_image_to_base64, pdf_to_images
from lionfuncs.errors import LionFileError

async def main():
    try:
        # Try to read a non-existent image
        await read_image_to_base64("nonexistent.jpg")
    except LionFileError as e:
        print(f"Image error: {e}")

    try:
        # Try to convert a non-existent PDF
        pdf_to_images("nonexistent.pdf", "output")
    except LionFileError as e:
        print(f"PDF error: {e}")

asyncio.run(main())
```

## Dependencies

The `pdf_to_images` function requires the `pdf2image` library, which in turn
requires Poppler to be installed on your system:

- **Linux**: `apt-get install poppler-utils`
- **macOS**: `brew install poppler`
- **Windows**: Download and install from
  [poppler-windows](https://github.com/oschwartz10612/poppler-windows)

If `pdf2image` is not installed, the function will raise a `LionFileError` with
a message indicating that the library is required.

## Implementation Details

The module checks for the availability of the `pdf2image` library at import time
and sets a flag `PDF2IMAGE_AVAILABLE`. If the library is not available, dummy
exception classes are defined to prevent `NameError` exceptions when the
`pdf_to_images` function is called.
