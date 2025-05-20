import logging
import math
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Literal, TypeVar, Union

import aiofiles

from ..errors import LionFileError

R = TypeVar("R")

__all__ = [
    "chunk_content",
    "read_file",
    "save_to_file",
    "list_files",
    "concat_files",
    "dir_to_files",
    "create_path",
]


def create_path(
    directory: Path | str,
    filename: str,
    extension: str | None = None,
    timestamp: bool = False,
    dir_exist_ok: bool = True,
    file_exist_ok: bool = False,
    time_prefix: bool = False,
    timestamp_format: str | None = None,
    random_hash_digits: int = 0,
) -> Path:
    """
    Create a file path with optional timestamp and random hash.

    Args:
        directory: Base directory for the file
        filename: Name of the file
        extension: Optional file extension (will override extension in filename if provided)
        timestamp: Whether to add a timestamp to the filename
        dir_exist_ok: Whether to allow the directory to already exist
        file_exist_ok: Whether to allow the file to already exist
        time_prefix: Whether to add timestamp as prefix (True) or suffix (False)
        timestamp_format: Format string for the timestamp
        random_hash_digits: Number of random hash digits to add to filename

    Returns:
        Path object for the created file path

    Raises:
        LionFileError: If directory creation fails or file already exists
    """
    if "/" in filename:
        sub_dirs_in_filename = filename.split("/")[:-1]
        actual_filename = filename.split("/")[-1]
        directory = Path(directory).joinpath(*sub_dirs_in_filename)
        filename = actual_filename
    elif "\\" in filename:
        sub_dirs_in_filename = filename.split("\\")[:-1]
        actual_filename = filename.split("\\")[-1]
        directory = Path(directory).joinpath(*sub_dirs_in_filename)
        filename = actual_filename

    directory = Path(directory)
    name_part, ext_part = os.path.splitext(filename)
    if extension:
        ext_part = f".{extension.lstrip('.')}"
    elif not ext_part and extension is None:
        ext_part = ""

    name = name_part
    if timestamp:
        ts_str = datetime.now().strftime(timestamp_format or "%Y%m%d%H%M%S")
        name = f"{ts_str}_{name}" if time_prefix else f"{name}_{ts_str}"
    if random_hash_digits > 0:
        random_suffix = uuid.uuid4().hex[:random_hash_digits]
        name = f"{name}-{random_suffix}"
    full_path = directory / f"{name}{ext_part}"
    try:
        full_path.parent.mkdir(parents=True, exist_ok=dir_exist_ok)
    except OSError as e:
        raise LionFileError(
            f"Failed to create directory {full_path.parent}: {e}"
        ) from e
    if full_path.exists() and not file_exist_ok:
        raise LionFileError(
            f"File {full_path} already exists and file_exist_ok is False."
        )
    return full_path


def _chunk_by_chars_internal(
    text: str, chunk_size: int, slice_overlap: int, threshold: int
) -> list[str]:
    """
    Split text into chunks by character count with overlap.

    Args:
        text: The text to split
        chunk_size: Maximum size of each chunk
        slice_overlap: Number of characters to overlap between chunks
        threshold: Minimum size for the last chunk before merging with previous

    Returns:
        List of text chunks
    """
    if not text:
        return []
    if chunk_size <= 0:
        return [text]

    text_len = len(text)
    if text_len == 0:
        return []
    n_chunks = math.ceil(text_len / chunk_size) if chunk_size > 0 else 1

    if n_chunks <= 1:
        return [text]

    chunks = []
    if n_chunks == 2:
        chunk1_end = min(chunk_size + slice_overlap, text_len)
        chunks.append(text[0:chunk1_end])

        if (text_len - chunk_size) > threshold:
            start_idx_part2 = max(0, chunk_size - slice_overlap)
            chunks.append(text[start_idx_part2:])
        else:
            chunks = [text]
        return chunks

    chunks.append(text[0 : min(chunk_size + slice_overlap, text_len)])

    for i in range(1, n_chunks - 1):
        nominal_start_current_chunk = i * chunk_size
        start_idx = max(0, nominal_start_current_chunk - slice_overlap)

        nominal_end_current_chunk = (i + 1) * chunk_size
        end_idx = min(text_len, nominal_end_current_chunk + slice_overlap)
        chunks.append(text[start_idx:end_idx])

    nominal_start_of_last_block = (n_chunks - 1) * chunk_size

    if (text_len - nominal_start_of_last_block) >= threshold:
        actual_start_of_last_slice = max(0, nominal_start_of_last_block - slice_overlap)
        chunks.append(text[actual_start_of_last_slice:])
    else:
        if chunks:
            start_append_content_idx = nominal_start_of_last_block + slice_overlap
            if start_append_content_idx < text_len:
                idx_start_of_penultimate = max(
                    0, (n_chunks - 2) * chunk_size - slice_overlap
                )
                chunks[-1] = text[idx_start_of_penultimate:text_len]
            start_of_penultimate_slice = max(
                0, (n_chunks - 2) * chunk_size - slice_overlap
            )
            chunks[-1] = text[start_of_penultimate_slice:text_len]

    return chunks


def _chunk_by_tokens_internal(
    tokens: list[str], chunk_size: int, slice_overlap: int, threshold: int
) -> list[list[str]]:
    """
    Split token list into chunks with overlap.

    Args:
        tokens: List of tokens to split
        chunk_size: Maximum number of tokens per chunk
        slice_overlap: Number of tokens to overlap between chunks
        threshold: Minimum size for the last chunk before merging with previous

    Returns:
        List of token chunks
    """
    if not tokens:
        return []
    if chunk_size <= 0:
        return [tokens]

    num_tokens = len(tokens)
    if num_tokens == 0:
        return []
    n_chunks = math.ceil(num_tokens / chunk_size) if chunk_size > 0 else 1

    if n_chunks <= 1:
        return [tokens]

    chunks = []
    if n_chunks == 2:
        chunk1_end = min(chunk_size + slice_overlap, num_tokens)
        chunks.append(tokens[0:chunk1_end])
        if (num_tokens - chunk_size) >= threshold:
            start_idx_part2 = max(0, chunk_size - slice_overlap)
            chunks.append(tokens[start_idx_part2:])
        else:
            chunks = [tokens]
        return chunks

    chunks.append(tokens[0 : min(chunk_size + slice_overlap, num_tokens)])

    for i in range(1, n_chunks - 1):
        nominal_start = i * chunk_size
        start_idx = max(0, nominal_start - slice_overlap)
        nominal_end = (i + 1) * chunk_size
        end_idx = min(num_tokens, nominal_end + slice_overlap)
        chunks.append(tokens[start_idx:end_idx])

    nominal_start_of_last_block = (n_chunks - 1) * chunk_size
    if (num_tokens - nominal_start_of_last_block) >= threshold:
        actual_start_of_last_slice = max(0, nominal_start_of_last_block - slice_overlap)
        chunks.append(tokens[actual_start_of_last_slice:])
    else:
        if chunks:
            start_of_penultimate_slice = max(
                0, (n_chunks - 2) * chunk_size - slice_overlap
            )
            chunks[-1] = tokens[start_of_penultimate_slice:num_tokens]

    return chunks


def chunk_content(
    content: str,
    chunk_by: Literal["chars", "tokens"] = "chars",
    tokenizer: Callable[[str], list[str]] = lambda x: x.split(),
    chunk_size: int = 1024,
    overlap_ratio: float = 0.1,
    threshold: int = 100,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """
    Split content into chunks with metadata.

    Args:
        content: String content to split into chunks
        chunk_by: Method to use for chunking ('chars' or 'tokens')
        tokenizer: Function to convert string to tokens when chunk_by='tokens'
        chunk_size: Maximum size of each chunk
        overlap_ratio: Ratio of overlap between chunks (0.0 to <1.0)
        threshold: Minimum size for the last chunk before merging with previous
        **kwargs: Additional arguments to pass to the tokenizer

    Returns:
        List of dictionaries containing chunk content and metadata

    Raises:
        LionFileError: If content is not a string or overlap_ratio is invalid
    """
    if not isinstance(content, str):
        raise LionFileError("Content must be a string.")
    if not 0 <= overlap_ratio < 1:
        raise LionFileError("Overlap ratio must be between 0.0 and <1.0")

    slice_overlap = int(chunk_size * overlap_ratio / 2) if chunk_size > 0 else 0

    processed_chunks_list: list[str]
    if chunk_by == "tokens":
        tokens = tokenizer(content, **kwargs)
        raw_token_chunks = _chunk_by_tokens_internal(
            tokens, chunk_size, slice_overlap, threshold
        )
        processed_chunks_list = [
            " ".join(token_list) for token_list in raw_token_chunks
        ]
    elif chunk_by == "chars":
        processed_chunks_list = _chunk_by_chars_internal(
            content, chunk_size, slice_overlap, threshold
        )
    else:
        raise LionFileError(
            f"Invalid chunk_by value: {chunk_by}. Must be 'chars' or 'tokens'."
        )
    output_chunks = []
    for i, chunk_text in enumerate(processed_chunks_list):
        output_chunks.append(
            {
                "chunk_content": chunk_text,
                "chunk_id": i + 1,
                "total_chunks": len(processed_chunks_list),
                "chunk_size_chars": len(chunk_text),
            }
        )
    return output_chunks


async def read_file(path: Union[str, Path]) -> str:
    """
    Asynchronously read the contents of a file.
    """
    try:
        async with aiofiles.open(Path(path), mode="r", encoding="utf-8") as f:
            return await f.read()
    except FileNotFoundError as e:
        raise LionFileError(f"File not found: {path}") from e
    except PermissionError as e:
        raise LionFileError(f"Permission denied when reading file: {path}") from e
    except Exception as e:
        raise LionFileError(f"Error reading file {path}: {e}") from e


async def save_to_file(
    text: str,
    directory: Union[str, Path],
    filename: str,
    file_exist_ok: bool = False,
    verbose: bool = False,
    extension: str | None = None,
    timestamp: bool = False,
    time_prefix: bool = False,
    timestamp_format: str | None = None,
    random_hash_digits: int = 0,
) -> Path:
    """
    Asynchronously save text to a file.
    """
    try:
        file_path = create_path(
            directory=Path(directory),
            filename=filename,
            file_exist_ok=file_exist_ok,
            dir_exist_ok=True,
            extension=extension,
            timestamp=timestamp,
            time_prefix=time_prefix,
            timestamp_format=timestamp_format,
            random_hash_digits=random_hash_digits,
        )
        async with aiofiles.open(file_path, mode="w", encoding="utf-8") as f:
            await f.write(text)
        if verbose:
            logging.info(f"Text saved to: {file_path}")
        return file_path
    except LionFileError:
        raise
    except OSError as e:
        raise LionFileError(
            f"Failed to save file {filename} in {directory}: {e}"
        ) from e
    except Exception as e:
        raise LionFileError(
            f"An unexpected error occurred while saving file: {e}"
        ) from e


def list_files(
    dir_path: Union[str, Path],
    extension: str | None = None,
    recursive: bool = False,
) -> list[Path]:
    """
    List files in a directory with optional filtering by extension.

    Args:
        dir_path: Path to the directory
        extension: Optional file extension to filter by
        recursive: Whether to search subdirectories recursively

    Returns:
        List of Path objects for the found files

    Raises:
        LionFileError: If the path is not a directory
    """
    directory = Path(dir_path)
    if not directory.is_dir():
        raise LionFileError(f"Path is not a directory: {dir_path}")
    paths = []
    if recursive:
        glob_pattern = f"**/*.{extension.lstrip('.')}" if extension else "**/*"
        paths = [p for p in directory.glob(glob_pattern) if p.is_file()]
    else:
        glob_pattern = f"*.{extension.lstrip('.')}" if extension else "*"
        paths = [p for p in directory.glob(glob_pattern) if p.is_file()]
    return paths


def dir_to_files(
    directory: Union[str, Path],
    file_types: list[str] | None = None,
    ignore_errors: bool = False,
    verbose: bool = False,
    recursive: bool = True,
) -> list[Path]:
    """
    Get a list of files in a directory with optional filtering and error handling.

    Args:
        directory: Path to the directory
        file_types: Optional list of file extensions to include
        ignore_errors: Whether to ignore permission and OS errors
        verbose: Whether to log warnings and info messages
        recursive: Whether to search subdirectories recursively

    Returns:
        Sorted list of Path objects for the found files

    Raises:
        LionFileError: If the path is not a directory or errors occur during scanning
    """
    directory_path = Path(directory)
    if not directory_path.is_dir():
        raise LionFileError(f"The provided path is not a valid directory: {directory}")
    found_files: list[Path] = []
    items_to_scan = [directory_path]
    while items_to_scan:
        current_path = items_to_scan.pop(0)
        try:
            for entry in current_path.iterdir():
                if entry.is_dir() and recursive:
                    items_to_scan.append(entry)
                elif entry.is_file():
                    if file_types:
                        if entry.suffix.lower() in [ft.lower() for ft in file_types]:
                            found_files.append(entry)
                    else:
                        found_files.append(entry)
        except PermissionError as e:
            if ignore_errors:
                if verbose:
                    logging.warning(f"Permission error scanning {current_path}: {e}")
            else:
                raise LionFileError(f"Permission error scanning {current_path}") from e
        except OSError as e:
            if ignore_errors:
                if verbose:
                    logging.warning(f"OS error scanning {current_path}: {e}")
            else:
                raise LionFileError(f"OS error scanning {current_path}") from e
    if verbose:
        logging.info(f"Found {len(found_files)} files in {directory}")
    return sorted(list(set(found_files)))


async def concat_files(
    data_paths: Union[str, Path, list[Union[str, Path]]],
    file_types: list[str],
    output_dir: Union[str, Path, None] = None,
    output_filename: str | None = None,
    file_exist_ok: bool = True,
    recursive: bool = True,
    verbose: bool = False,
    content_threshold: int = 0,
) -> str:
    """
    Asynchronously concatenate the contents of multiple files.

    Args:
        data_paths: Path(s) to file(s) or directories to process
        file_types: List of file extensions to include
        output_dir: Optional directory to save the concatenated output
        output_filename: Optional filename for the output file
        file_exist_ok: Whether to overwrite existing output file
        recursive: Whether to search subdirectories recursively
        verbose: Whether to log warnings and info messages
        content_threshold: Minimum content length to include a file

    Returns:
        Concatenated text from all processed files
    """
    if isinstance(data_paths, (str, Path)):
        paths_to_scan = [Path(data_paths)]
    else:
        paths_to_scan = [Path(p) for p in data_paths]

    all_texts: list[str] = []
    processed_file_paths: list[Path] = []

    for path_item in paths_to_scan:
        if path_item.is_dir():
            files_in_dir = dir_to_files(
                path_item,
                file_types=file_types,
                recursive=recursive,
                verbose=False,
                ignore_errors=True,
            )
            processed_file_paths.extend(files_in_dir)
        elif path_item.is_file():
            if file_types:
                if path_item.suffix.lower() in [ft.lower() for ft in file_types]:
                    processed_file_paths.append(path_item)
            else:
                processed_file_paths.append(path_item)
        elif verbose:
            logging.warning(
                f"Path {path_item} is not a valid file or directory, skipping."
            )

    unique_sorted_fps = sorted(list(set(processed_file_paths)))

    for fp in unique_sorted_fps:
        try:
            text = await read_file(fp)
            if len(text) >= content_threshold:
                header = f"\n--- START OF FILE: {fp.resolve()} ---\n"
                footer = f"\n--- END OF FILE: {fp.resolve()} ---\n"
                all_texts.append(header + text + footer)
        except Exception as e:
            if verbose:
                logging.warning(f"Could not read or process file {fp}: {e}, skipping.")

    concatenated_text = "\n".join(all_texts)

    if output_dir and output_filename:
        try:
            await save_to_file(
                concatenated_text,
                directory=output_dir,
                filename=output_filename,
                file_exist_ok=file_exist_ok,
                verbose=verbose,
            )
        except LionFileError as e:
            if verbose:
                logging.error(f"Failed to save concatenated output: {e}")
    elif output_dir and not output_filename:
        if verbose:
            logging.warning(
                "output_dir provided for concat_files, but no output_filename. Output not saved."
            )

    return concatenated_text
