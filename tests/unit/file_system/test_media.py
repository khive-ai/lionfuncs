import base64
import sys
from pathlib import Path
from unittest import mock

import pytest

from lionfuncs.errors import LionFileError
from lionfuncs.file_system import media as fs_media


# Helper to create a dummy image file (can be any binary content for testing read)
def create_dummy_image_file(path: Path, content_bytes: bytes = b"dummyimagedata"):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(content_bytes)


@pytest.mark.asyncio
async def test_read_image_to_base64_success(tmp_path: Path):
    image_content = b"test image content"
    test_image_file = tmp_path / "test.png"
    create_dummy_image_file(test_image_file, image_content)

    b64_string = await fs_media.read_image_to_base64(test_image_file)
    assert base64.b64decode(b64_string) == image_content


@pytest.mark.asyncio
async def test_read_image_to_base64_file_not_found(tmp_path: Path):
    non_existent_file = tmp_path / "not_found.jpg"
    with pytest.raises(
        LionFileError, match=f"Image file not found: {non_existent_file}"
    ):
        await fs_media.read_image_to_base64(non_existent_file)


@pytest.mark.asyncio
@mock.patch("aiofiles.open")
async def test_read_image_to_base64_read_error(mock_aio_open, tmp_path: Path):
    mock_file = mock.AsyncMock()
    mock_file.read.side_effect = OSError("Cannot read")
    mock_aio_open.return_value.__aenter__.return_value = mock_file

    test_image_file = tmp_path / "read_error.gif"
    # No need to create file as open is mocked to succeed but read to fail

    with pytest.raises(
        LionFileError,
        match=f"Error reading or encoding image {test_image_file}: Cannot read",
    ):
        await fs_media.read_image_to_base64(test_image_file)


# Mocking pdf2image for pdf_to_images tests
class MockPdf2ImageError(Exception):
    pass


class MockPDFInfoNotInstalledError(MockPdf2ImageError):
    pass


class MockPDFPageCountError(MockPdf2ImageError):
    pass


class MockPDFSyntaxError(MockPdf2ImageError):
    pass


# Mock PIL Image object if pdf2image returns them
class MockPILImage:
    def __init__(self, filename):
        self.filename = filename


@mock.patch("lionfuncs.file_system.media.PDF2IMAGE_AVAILABLE", True)
@mock.patch("lionfuncs.file_system.media.convert_from_path")
def test_pdf_to_images_success(mock_convert_from_path, tmp_path: Path):
    # Scenario 1: convert_from_path returns list of Path objects
    expected_paths = [
        tmp_path / "output" / "page_1.jpeg",
        tmp_path / "output" / "page_2.jpeg",
    ]
    mock_convert_from_path.return_value = expected_paths

    pdf_file = tmp_path / "dummy.pdf"
    pdf_file.touch()
    output_dir = tmp_path / "output"

    result_paths = fs_media.pdf_to_images(pdf_file, output_dir, fmt="jpeg", dpi=150)
    mock_convert_from_path.assert_called_once_with(
        pdf_path=pdf_file, dpi=150, fmt="jpeg", output_folder=output_dir
    )
    assert result_paths == expected_paths
    assert output_dir.exists()

    # Scenario 2: convert_from_path returns list of MockPILImage objects
    mock_convert_from_path.reset_mock()
    pil_image_filenames = [str(p) for p in expected_paths]
    # Create mock PIL Image objects that have a 'filename' attribute
    mock_pil_images = [MockPILImage(fn) for fn in pil_image_filenames]
    mock_convert_from_path.return_value = mock_pil_images

    result_paths_pil = fs_media.pdf_to_images(pdf_file, output_dir, fmt="png", dpi=300)
    mock_convert_from_path.assert_called_once_with(
        pdf_path=pdf_file, dpi=300, fmt="png", output_folder=output_dir
    )
    assert result_paths_pil == expected_paths


def test_pdf_to_images_pdf_not_found(tmp_path: Path):
    with pytest.raises(LionFileError, match="PDF file not found"):
        fs_media.pdf_to_images(tmp_path / "non_existent.pdf", tmp_path / "output")


# Simulate pdf2image not installed at the sys.modules level
@mock.patch.dict(sys.modules, {"pdf2image": None, "pdf2image.exceptions": None})
# Directly ensure PDF2IMAGE_AVAILABLE is False in the media module for this test
@mock.patch("lionfuncs.file_system.media.PDF2IMAGE_AVAILABLE", False, create=True)
def test_pdf_to_images_import_error(tmp_path: Path):
    # The patches are active even if their mock objects are not named in the signature.
    pdf_file = tmp_path / "dummy.pdf"
    pdf_file.touch()
    with pytest.raises(LionFileError, match="The 'pdf2image' library is required"):
        fs_media.pdf_to_images(pdf_file, tmp_path / "output")


# Create a fixture for pdf2image exception testing
@pytest.fixture(
    params=[
        (MockPDFInfoNotInstalledError("poppler not found"), "poppler not found"),
        (MockPDFPageCountError("page count error"), "page count error"),
        (MockPDFSyntaxError("syntax error"), "syntax error"),
        (ValueError("Some other pdf2image problem"), "Some other pdf2image problem"),
    ]
)
def pdf2image_exception_case(request):
    """Fixture that provides exception and expected message part"""
    exception, expected_message_part = request.param
    return exception, expected_message_part


# Simplified test that uses a fixture instead of parametrize with mocks
@mock.patch("lionfuncs.file_system.media.PDF2IMAGE_AVAILABLE", True)
@mock.patch("lionfuncs.file_system.media.convert_from_path")
def test_pdf_to_images_exception_handling(
    mock_convert_from_path,
    pdf2image_exception_case,
    tmp_path: Path,
):
    # Unpack the exception case
    exception_obj, expected_message_part = pdf2image_exception_case

    # Setup mock for pdf2image module and its exceptions
    mock_pdf2image_module = mock.MagicMock(name="mock_pdf2image_module")
    mock_exceptions_module = mock.MagicMock(name="mock_exceptions_module")

    mock_exceptions_module.PDFInfoNotInstalledError = MockPDFInfoNotInstalledError
    mock_exceptions_module.PDFPageCountError = MockPDFPageCountError
    mock_exceptions_module.PDFSyntaxError = MockPDFSyntaxError

    mock_pdf2image_module.exceptions = mock_exceptions_module

    # Apply to sys.modules so imports in media.py pick these up
    original_pdf2image = sys.modules.get("pdf2image")
    original_pdf2image_exceptions = sys.modules.get("pdf2image.exceptions")
    sys.modules["pdf2image"] = mock_pdf2image_module
    sys.modules["pdf2image.exceptions"] = mock_exceptions_module

    # Set the side effect for the convert_from_path mock
    mock_convert_from_path.side_effect = exception_obj

    pdf_file = tmp_path / "dummy.pdf"
    pdf_file.touch()
    try:
        with pytest.raises(LionFileError) as exc_info:
            fs_media.pdf_to_images(pdf_file, tmp_path / "output")

        assert expected_message_part in str(exc_info.value)
    finally:
        # Clean up sys.modules to restore original state
        if original_pdf2image is not None:
            sys.modules["pdf2image"] = original_pdf2image
        else:
            if "pdf2image" in sys.modules:
                del sys.modules["pdf2image"]

        if original_pdf2image_exceptions is not None:
            sys.modules["pdf2image.exceptions"] = original_pdf2image_exceptions
        else:
            if "pdf2image.exceptions" in sys.modules:
                del sys.modules["pdf2image.exceptions"]
