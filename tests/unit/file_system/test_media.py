import asyncio
from pathlib import Path
import pytest
from unittest import mock
import base64
import sys

from lionfuncs.file_system import media as fs_media
from lionfuncs.errors import LionFileError

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
    with pytest.raises(LionFileError, match=f"Image file not found: {non_existent_file}"):
        await fs_media.read_image_to_base64(non_existent_file)

@pytest.mark.asyncio
@mock.patch("aiofiles.open")
async def test_read_image_to_base64_read_error(mock_aio_open, tmp_path: Path):
    mock_file = mock.AsyncMock()
    mock_file.read.side_effect = OSError("Cannot read")
    mock_aio_open.return_value.__aenter__.return_value = mock_file
    
    test_image_file = tmp_path / "read_error.gif"
    # No need to create file as open is mocked to succeed but read to fail
    
    with pytest.raises(LionFileError, match=f"Error reading or encoding image {test_image_file}: Cannot read"):
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

class MockPDFTooBigError(MockPdf2ImageError):
    pass

# Mock PIL Image object if pdf2image returns them
class MockPILImage:
    def __init__(self, filename):
        self.filename = filename

@mock.patch.dict(sys.modules, {"pdf2image": mock.MagicMock()})
def test_pdf_to_images_success(tmp_path: Path):
    # Setup mock for pdf2image.convert_from_path
    mock_pdf2image = sys.modules["pdf2image"]
    
    # Scenario 1: convert_from_path returns list of Path objects
    expected_paths = [tmp_path / "output" / "page_1.jpeg", tmp_path / "output" / "page_2.jpeg"]
    mock_pdf2image.convert_from_path.return_value = expected_paths
    
    pdf_file = tmp_path / "dummy.pdf"
    pdf_file.touch() # Make it exist
    output_dir = tmp_path / "output"

    result_paths = fs_media.pdf_to_images(pdf_file, output_dir, fmt="jpeg", dpi=150)
    mock_pdf2image.convert_from_path.assert_called_once_with(
        pdf_path=pdf_file, dpi=150, fmt="jpeg", output_folder=output_dir
    )
    assert result_paths == expected_paths
    assert output_dir.exists() # Check if output_dir was created by the function

    # Scenario 2: convert_from_path returns list of MockPILImage objects
    mock_pdf2image.convert_from_path.reset_mock()
    pil_image_filenames = [str(p) for p in expected_paths]
    mock_pdf2image.convert_from_path.return_value = [MockPILImage(fn) for fn in pil_image_filenames]
    
    result_paths_pil = fs_media.pdf_to_images(pdf_file, output_dir, fmt="png", dpi=300)
    mock_pdf2image.convert_from_path.assert_called_once_with(
        pdf_path=pdf_file, dpi=300, fmt="png", output_folder=output_dir
    )
    assert result_paths_pil == expected_paths


def test_pdf_to_images_pdf_not_found(tmp_path: Path):
    with pytest.raises(LionFileError, match="PDF file not found"):
        fs_media.pdf_to_images(tmp_path / "non_existent.pdf", tmp_path / "output")

@mock.patch.dict(sys.modules, {"pdf2image": None}) # Simulate pdf2image not installed
def test_pdf_to_images_import_error(tmp_path: Path):
    pdf_file = tmp_path / "dummy.pdf"
    pdf_file.touch()
    with pytest.raises(LionFileError, match="The 'pdf2image' library is required"):
        fs_media.pdf_to_images(pdf_file, tmp_path / "output")

@mock.patch.dict(sys.modules, {"pdf2image": mock.MagicMock()})
@pytest.mark.parametrize(
    "pdf2image_exception, expected_message_part",
    [
        (MockPDFInfoNotInstalledError("poppler not found"), "poppler not found"),
        (MockPDFPageCountError("page count error"), "page count error"),
        (MockPDFSyntaxError("syntax error"), "syntax error"),
        (MockPDFTooBigError("pdf too big"), "pdf too big"),
        (ValueError("Some other pdf2image problem"), "Some other pdf2image problem") # Test generic Exception
    ]
)
def test_pdf_to_images_pdf2image_exceptions(pdf2image_exception, expected_message_part, tmp_path: Path):
    mock_pdf2image = sys.modules["pdf2image"]
    mock_pdf2image.convert_from_path.side_effect = pdf2image_exception
    # Also mock the exception classes themselves if they are checked by type in the main code
    mock_pdf2image.exceptions = mock.MagicMock()
    mock_pdf2image.exceptions.PDFInfoNotInstalledError = MockPDFInfoNotInstalledError
    mock_pdf2image.exceptions.PDFPageCountError = MockPDFPageCountError
    mock_pdf2image.exceptions.PDFSyntaxError = MockPDFSyntaxError
    mock_pdf2image.exceptions.PDFTooBigError = MockPDFTooBigError


    pdf_file = tmp_path / "dummy.pdf"
    pdf_file.touch()
    with pytest.raises(LionFileError) as exc_info:
        fs_media.pdf_to_images(pdf_file, tmp_path / "output")
    assert expected_message_part in str(exc_info.value)
    assert "PDF processing error" in str(exc_info.value) or "Failed to convert PDF" in str(exc_info.value)