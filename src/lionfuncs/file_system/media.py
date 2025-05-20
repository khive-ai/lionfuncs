"""
Media-specific file system utilities for lionfuncs.
"""

import base64
import logging
from pathlib import Path
from typing import Any, Union

import aiofiles

from ..errors import LionFileError

try:
    from pdf2image import convert_from_path
    from pdf2image.exceptions import (
        PDFInfoNotInstalledError,
        PDFPageCountError,
        PDFSyntaxError,
    )

    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

    # Define dummy exceptions if pdf2image is not available, so type hints and
    # except blocks in pdf_to_images don't cause NameErrors.
    class PDFInfoNotInstalledError(Exception):
        pass

    class PDFPageCountError(Exception):
        pass

    class PDFSyntaxError(Exception):
        pass

    # Define a dummy convert_from_path function to avoid AttributeError in tests
    def convert_from_path(*args, **kwargs):
        raise ImportError("pdf2image is not installed")


__all__ = [
    "read_image_to_base64",
    "pdf_to_images",
]


async def read_image_to_base64(image_path: Union[str, Path]) -> str:
    """
    Asynchronously reads an image file and encodes its content to a base64 string.

    Args:
        image_path: The path to the image file.

    Returns:
        A base64 encoded string representation of the image.

    Raises:
        LionFileError: If the file cannot be read or other OS errors occur.
    """
    try:
        async with aiofiles.open(image_path, "rb") as img_file:
            img_bytes = await img_file.read()
        base64_encoded_data = base64.b64encode(img_bytes)
        return base64_encoded_data.decode("utf-8")
    except FileNotFoundError:
        raise LionFileError(f"Image file not found: {image_path}") from None
    except Exception as e:
        raise LionFileError(f"Error reading or encoding image {image_path}: {e}") from e


def pdf_to_images(
    pdf_path: Union[str, Path],
    output_folder: Union[str, Path],
    fmt: str = "jpeg",
    dpi: int = 200,
    **kwargs: Any,
) -> list[Path]:
    """
    Converts pages of a PDF file to images. Requires the 'pdf2image' library
    and its dependencies (like Poppler) to be installed.
    Install with: pip install lionfuncs[media]

    Args:
        pdf_path: Path to the input PDF file.
        output_folder: Directory to save the output images.
        fmt: Output image format (e.g., "jpeg", "png").
        dpi: Dots per inch for the output images.
        **kwargs: Additional keyword arguments to pass to pdf2image.convert_from_path.

    Returns:
        A list of Path objects for the saved images.

    Raises:
        LionFileError: If pdf2image is not installed or conversion fails.
    """
    pdf_p = Path(pdf_path)
    output_p = Path(output_folder)

    if not pdf_p.exists() or not pdf_p.is_file():
        raise LionFileError(f"PDF file not found: {pdf_path}")

    if not PDF2IMAGE_AVAILABLE:
        raise LionFileError(
            "The 'pdf2image' library is required for PDF processing. "
            "Please install it with: pip install lionfuncs[media]"
        )

    output_p.mkdir(parents=True, exist_ok=True)

    try:
        # convert_from_path is only called if PDF2IMAGE_AVAILABLE is True
        images = convert_from_path(
            pdf_path=pdf_p, dpi=dpi, fmt=fmt, output_folder=output_p, **kwargs
        )

        saved_paths: list[Path] = []
        if images and isinstance(images, list):
            for item in images:
                if hasattr(item, "filename"):
                    saved_paths.append(Path(item.filename))
                elif isinstance(item, (str, Path)):
                    saved_paths.append(Path(item))
                else:
                    logging.warning(
                        f"pdf_to_images received an unexpected item type: {type(item)}"
                    )
        return saved_paths

    except (
        PDFInfoNotInstalledError,
        PDFPageCountError,
        PDFSyntaxError,
    ) as e:
        # These exceptions are defined (either real or dummy) due to top-level try-except
        raise LionFileError(
            f"PDF processing error for {pdf_path} using pdf2image: {e}"
        ) from e
    except Exception as e:  # Catch any other unexpected errors during conversion
        raise LionFileError(f"Failed to convert PDF {pdf_path} to images: {e}") from e
