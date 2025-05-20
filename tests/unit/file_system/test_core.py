from pathlib import Path
from unittest import mock

import pytest

from lionfuncs.errors import LionFileError
from lionfuncs.file_system import core as fs_core


# Helper to create dummy files for testing
def create_dummy_file(path: Path, content: str = "dummy content"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# Tests for _create_path (internal helper, but crucial)
def test_create_path_basic(tmp_path: Path):
    dir_path = tmp_path / "test_dir"
    file_path = fs_core.create_path(dir_path, "testfile.txt")
    assert file_path == dir_path / "testfile.txt"
    assert dir_path.exists()


def test_create_path_with_extension_arg(tmp_path: Path):
    file_path = fs_core.create_path(tmp_path, "testfile", extension="log")
    assert file_path == tmp_path / "testfile.log"


def test_create_path_filename_has_extension(tmp_path: Path):
    file_path = fs_core.create_path(tmp_path, "testfile.md")
    assert file_path == tmp_path / "testfile.md"


def test_create_path_filename_has_extension_and_arg_overrides(tmp_path: Path):
    file_path = fs_core.create_path(tmp_path, "testfile.md", extension="txt")
    assert file_path == tmp_path / "testfile.txt"


def test_create_path_timestamp(tmp_path: Path):
    file_path = fs_core.create_path(tmp_path, "ts_file.txt", timestamp=True)
    assert "_" in file_path.stem  # Check if timestamp was added
    assert file_path.name.endswith("_ts_file.txt") or file_path.stem.startswith(
        "ts_file_"
    )


def test_create_path_random_hash(tmp_path: Path):
    file_path = fs_core.create_path(tmp_path, "hash_file.txt", random_hash_digits=6)
    assert len(file_path.stem.split("-")[-1]) == 6  # Check for hash


def test_create_path_file_exists_ok(tmp_path: Path):
    file_path1 = fs_core.create_path(tmp_path, "exists.txt", file_exist_ok=False)
    file_path1.touch()
    file_path2 = fs_core.create_path(tmp_path, "exists.txt", file_exist_ok=True)
    assert file_path1 == file_path2


def test_create_path_file_exists_not_ok(tmp_path: Path):
    file_path = fs_core.create_path(tmp_path, "exists_not_ok.txt")
    file_path.touch()
    with pytest.raises(
        LionFileError, match="already exists and file_exist_ok is False"
    ):
        fs_core.create_path(tmp_path, "exists_not_ok.txt", file_exist_ok=False)


def test_create_path_with_subdirs_in_filename(tmp_path: Path):
    dir_path = tmp_path / "main_dir"
    file_path = fs_core.create_path(dir_path, "sub1/sub2/testfile.txt")
    expected_path = dir_path / "sub1" / "sub2" / "testfile.txt"
    assert file_path == expected_path
    assert file_path.parent.exists()


# Tests for chunk_content (synchronous)
@pytest.mark.parametrize(
    "content, chunk_by, chunk_size, overlap_ratio, threshold, expected_num_chunks, expected_first_chunk_content_approx",
    [
        ("abcdefghijklmno", "chars", 5, 0.2, 2, 3, "abcde"),  # overlap = 1
        ("token1 token2 token3 token4 token5", "tokens", 2, 0.0, 1, 3, "token1 token2"),
        ("short", "chars", 10, 0.1, 1, 1, "short"),
        ("", "chars", 10, 0.1, 1, 0, ""),
        ("a b c d e f g", "tokens", 3, 1 / 3, 1, 3, "a b c"),  # overlap = 1 token
    ],
)
def test_chunk_content(
    content,
    chunk_by,
    chunk_size,
    overlap_ratio,
    threshold,
    expected_num_chunks,
    expected_first_chunk_content_approx,
):
    chunks = fs_core.chunk_content(
        content,
        chunk_by=chunk_by,
        chunk_size=chunk_size,
        overlap_ratio=overlap_ratio,
        threshold=threshold,
    )
    assert len(chunks) == expected_num_chunks
    if expected_num_chunks > 0:
        assert expected_first_chunk_content_approx in chunks[0]["chunk_content"]
        for chunk in chunks:
            assert "chunk_content" in chunk
            assert "chunk_id" in chunk
            assert "total_chunks" in chunk
            assert chunk["total_chunks"] == expected_num_chunks


def test_chunk_content_invalid_chunk_by():
    with pytest.raises(LionFileError, match="Invalid chunk_by value"):
        fs_core.chunk_content("test", chunk_by="invalid")  # type: ignore


def test_chunk_content_invalid_overlap_ratio():
    with pytest.raises(
        LionFileError, match="Overlap ratio must be between 0.0 and <1.0"
    ):
        fs_core.chunk_content("test", overlap_ratio=1.0)
    with pytest.raises(
        LionFileError, match="Overlap ratio must be between 0.0 and <1.0"
    ):
        fs_core.chunk_content("test", overlap_ratio=-0.1)


# Tests for read_file (asynchronous)
@pytest.mark.asyncio
async def test_read_file_success(tmp_path: Path):
    file_content = "Hello, lionfuncs!"
    test_file = tmp_path / "test_read.txt"
    create_dummy_file(test_file, file_content)

    content = await fs_core.read_file(test_file)
    assert content == file_content


@pytest.mark.asyncio
async def test_read_file_not_found(tmp_path: Path):
    non_existent_file = tmp_path / "not_found.txt"
    with pytest.raises(LionFileError, match=f"File not found: {non_existent_file}"):
        await fs_core.read_file(non_existent_file)


@pytest.mark.asyncio
@mock.patch("aiofiles.open")
async def test_read_file_permission_error(mock_aio_open, tmp_path: Path):
    mock_aio_open.side_effect = PermissionError("Permission denied")
    test_file = tmp_path / "perm_denied.txt"
    # No need to create the file if open itself is mocked to fail
    with pytest.raises(
        LionFileError, match=f"Permission denied when reading file: {test_file}"
    ):
        await fs_core.read_file(test_file)


# Tests for save_to_file (asynchronous)
@pytest.mark.asyncio
async def test_save_to_file_success(tmp_path: Path):
    file_content = "Saving this to a file."
    dir_path = tmp_path / "save_dir"
    filename = "test_save.txt"

    saved_path = await fs_core.save_to_file(file_content, dir_path, filename)
    assert saved_path == dir_path / filename
    assert saved_path.exists()
    assert saved_path.read_text(encoding="utf-8") == file_content


@pytest.mark.asyncio
async def test_save_to_file_overwrite_disallowed(tmp_path: Path):
    dir_path = tmp_path / "save_overwrite"
    filename = "overwrite.txt"
    create_dummy_file(dir_path / filename, "initial content")

    with pytest.raises(
        LionFileError, match="already exists and file_exist_ok is False"
    ):
        await fs_core.save_to_file(
            "new content", dir_path, filename, file_exist_ok=False
        )


@pytest.mark.asyncio
async def test_save_to_file_overwrite_allowed(tmp_path: Path):
    dir_path = tmp_path / "save_overwrite_allow"
    filename = "overwrite_allow.txt"
    create_dummy_file(dir_path / filename, "initial content")

    new_content = "this is new content"
    saved_path = await fs_core.save_to_file(
        new_content, dir_path, filename, file_exist_ok=True
    )
    assert saved_path.read_text(encoding="utf-8") == new_content


@pytest.mark.asyncio
@mock.patch("aiofiles.open")
async def test_save_to_file_os_error_on_write(mock_aio_open, tmp_path: Path):
    mock_file = mock.AsyncMock()
    mock_file.write.side_effect = OSError("Disk full")
    mock_aio_open.return_value.__aenter__.return_value = mock_file

    dir_path = tmp_path / "save_os_error"
    filename = "os_error.txt"
    with pytest.raises(
        LionFileError, match=f"Failed to save file {filename} in {dir_path}: Disk full"
    ):
        await fs_core.save_to_file("content", dir_path, filename)


# Tests for list_files (synchronous)
def test_list_files_simple(tmp_path: Path):
    create_dummy_file(tmp_path / "file1.txt")
    create_dummy_file(tmp_path / "file2.log")
    (tmp_path / "subdir").mkdir()
    create_dummy_file(tmp_path / "subdir" / "file3.txt")

    files = fs_core.list_files(tmp_path)
    assert sorted([p.name for p in files]) == sorted(
        ["file1.txt", "file2.log"]
    )  # Non-recursive

    txt_files = fs_core.list_files(tmp_path, extension="txt")
    assert sorted([p.name for p in txt_files]) == ["file1.txt"]


def test_list_files_recursive(tmp_path: Path):
    create_dummy_file(tmp_path / "file1.txt")
    (tmp_path / "subdir1").mkdir()
    create_dummy_file(tmp_path / "subdir1" / "file2.txt")
    (tmp_path / "subdir1" / "subdir2").mkdir()
    create_dummy_file(tmp_path / "subdir1" / "subdir2" / "file3.log")

    all_files = fs_core.list_files(tmp_path, recursive=True)
    assert len(all_files) == 3
    expected_names = {"file1.txt", "file2.txt", "file3.log"}
    assert {p.name for p in all_files} == expected_names

    txt_files_recursive = fs_core.list_files(tmp_path, extension="txt", recursive=True)
    assert len(txt_files_recursive) == 2
    assert {p.name for p in txt_files_recursive} == {"file1.txt", "file2.txt"}


def test_list_files_not_a_directory(tmp_path: Path):
    file_path = tmp_path / "not_a_dir.txt"
    create_dummy_file(file_path)
    with pytest.raises(LionFileError, match="Path is not a directory"):
        fs_core.list_files(file_path)


# Tests for dir_to_files (synchronous)
def test_dir_to_files_basic(tmp_path: Path):
    create_dummy_file(tmp_path / "a.txt")
    (tmp_path / "sub").mkdir()
    create_dummy_file(tmp_path / "sub" / "b.md")
    create_dummy_file(tmp_path / "sub" / "c.txt")

    # Recursive by default
    files = fs_core.dir_to_files(tmp_path)
    assert len(files) == 3

    txt_files = fs_core.dir_to_files(tmp_path, file_types=[".txt"])
    assert len(txt_files) == 2
    assert {p.name for p in txt_files} == {"a.txt", "c.txt"}


def test_dir_to_files_non_recursive(tmp_path: Path):
    create_dummy_file(tmp_path / "a.txt")
    (tmp_path / "sub").mkdir()
    create_dummy_file(tmp_path / "sub" / "b.txt")

    files = fs_core.dir_to_files(tmp_path, recursive=False)
    assert len(files) == 1
    assert files[0].name == "a.txt"


def test_dir_to_files_not_a_dir_error(tmp_path: Path):
    file_path = tmp_path / "test.txt"
    file_path.touch()
    with pytest.raises(
        LionFileError, match="The provided path is not a valid directory"
    ):
        fs_core.dir_to_files(file_path)


# Tests for concat_files (asynchronous)
@pytest.mark.asyncio
async def test_concat_files_simple(tmp_path: Path):
    create_dummy_file(tmp_path / "f1.txt", "content1")
    create_dummy_file(tmp_path / "f2.txt", "content2")
    create_dummy_file(tmp_path / "f3.log", "content3_log")  # Should be ignored

    result = await fs_core.concat_files(tmp_path, file_types=[".txt"])
    assert "START OF FILE" in result
    assert "content1" in result
    assert "content2" in result
    assert "content3_log" not in result
    assert str(tmp_path / "f1.txt") in result  # Check for headers
    assert str(tmp_path / "f2.txt") in result


@pytest.mark.asyncio
async def test_concat_files_list_of_paths(tmp_path: Path):
    path1 = tmp_path / "dir1"
    path2 = tmp_path / "file_direct.txt"
    path1.mkdir()
    create_dummy_file(path1 / "f1.txt", "content_f1")
    create_dummy_file(path2, "content_direct")

    result = await fs_core.concat_files([path1, path2], file_types=[".txt"])
    assert "content_f1" in result
    assert "content_direct" in result


@pytest.mark.asyncio
async def test_concat_files_with_output(tmp_path: Path):
    create_dummy_file(tmp_path / "in1.txt", "hello")
    output_dir = tmp_path / "output"
    output_filename = "concatenated.out"

    await fs_core.concat_files(
        tmp_path,
        file_types=[".txt"],
        output_dir=output_dir,
        output_filename=output_filename,
    )

    output_file = output_dir / output_filename
    assert output_file.exists()
    content = output_file.read_text()
    assert "hello" in content
    assert str(tmp_path / "in1.txt") in content


@pytest.mark.asyncio
async def test_concat_files_content_threshold(tmp_path: Path):
    create_dummy_file(tmp_path / "short.txt", "short")
    create_dummy_file(tmp_path / "long.txt", "this is long enough")

    result = await fs_core.concat_files(
        tmp_path, file_types=[".txt"], content_threshold=10
    )
    assert "short" not in result
    assert "this is long enough" in result
