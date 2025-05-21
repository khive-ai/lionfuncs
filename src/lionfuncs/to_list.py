from collections.abc import Iterable, Mapping
from enum import Enum
from typing import Any

from pydantic import BaseModel as PydanticBaseModel
from pydantic_core import PydanticUndefined


__all__ = ("to_list",)

DICT_HASH_FUNC = None


# Pre-calculate skip types tuples once for flattening logic
_DEFAULT_SKIP_FLATTEN_TYPES: tuple[type[Any], ...] = (
    str,
    bytes,
    bytearray,
    Mapping,
    PydanticBaseModel,
)
_NO_TUPLE_SET_FLATTEN_SKIP_TYPES: tuple[type[Any], ...] = (
    _DEFAULT_SKIP_FLATTEN_TYPES + (tuple, set, frozenset)
)


def _initial_conversion_to_list(current_input: Any, use_values_flag: bool) -> list[Any]:
    """Converts various input types to an initial list format."""
    if current_input is None or current_input is PydanticUndefined:
        return []

    if isinstance(current_input, list):
        return list(current_input)  # Return a copy to prevent modifying original input

    if isinstance(current_input, type) and issubclass(current_input, Enum):
        members = list(current_input.__members__.values())
        return [member.value for member in members] if use_values_flag else members

    if isinstance(current_input, (str, bytes, bytearray)):
        return [current_input]  # Treat as single items

    if isinstance(current_input, Mapping):
        return list(current_input.values()) if use_values_flag else [current_input]

    # Pydantic models are single items at this stage
    if isinstance(current_input, PydanticBaseModel):
        return [current_input]

    # Convert other iterables
    if isinstance(current_input, Iterable):
        return list(current_input)
    return [current_input]  # Wrap non-iterable, non-special types


def _recursive_process_list(
    input_list: list[Any],
    flatten_flag: bool,
    dropna_flag: bool,
    skip_flatten_types: tuple[type[Any], ...],
) -> list[Any]:
    """Recursively processes list for flattening and dropping None/Undefined values."""
    processed_list: list[Any] = []
    for item in input_list:
        if dropna_flag and (item is None or item is PydanticUndefined):
            continue

        is_iterable_to_process = isinstance(item, Iterable) and not isinstance(
            item, skip_flatten_types
        )

        if is_iterable_to_process:
            # Materialize generic iterables (like generators) once before recursion
            elements_to_process = list(item)
            if flatten_flag:
                processed_list.extend(
                    _recursive_process_list(
                        input_list=elements_to_process,
                        flatten_flag=True,
                        dropna_flag=dropna_flag,
                        skip_flatten_types=skip_flatten_types,
                    )
                )
            else:
                # Process sub-list (for dropna on its elements) but append as a single (processed) item
                processed_list.append(
                    _recursive_process_list(
                        input_list=elements_to_process,
                        flatten_flag=False,
                        dropna_flag=dropna_flag,
                        skip_flatten_types=skip_flatten_types,
                    )
                )
        else:
            # Item is not an iterable to be further processed, or flattening is off for this level
            processed_list.append(item)
    return processed_list


def to_list(
    input_: Any,
    /,
    *,
    flatten: bool = False,
    dropna: bool = False,
    unique: bool = False,
    use_values: bool = False,
    flatten_tuple_set: bool = False,
) -> list[Any]:
    """
    Converts various input types into a list with optional transformations like
    flattening, removing None/undefined values, ensuring uniqueness, extracting
    values from Enums/Mappings, and optionally flattening tuples/sets.

    Args:
        input_: The value to convert to a list.
        flatten: If True, recursively flattens nested iterables, respecting
                 types that should not be flattened (e.g., strings, dicts).
        dropna: If True, removes items that are None or PydanticUndefined.
        unique: If True, removes duplicate items from the list. For this to work
                predictably on nested structures, the list is effectively flattened
                before uniqueness is determined. Requires `flatten=True` if you
                want the initial structure to be flat before uniqueness, otherwise
                an internal flattening pass occurs for the unique logic.
        use_values: If True, for Enum types, their member values are used.
                    For Mapping types, their values are used. Otherwise, the Enum
                    members or the Mapping itself is used.
        flatten_tuple_set: If True and `flatten` is also True, tuples, sets, and
                           frozensets will also be flattened. Otherwise, they are
                           treated as atomic items during flattening.

    Returns:
        A new list, processed according to the specified options.

    Raises:
        ValueError: If `unique=True` is specified with `flatten=False` by the caller,
                    as per original design for predictable uniqueness on nested items.
    """
    if unique and not flatten:
        # This check ensures that if a user explicitly wants uniqueness, they understand
        # it usually implies operating on a flat sequence of items. If flatten=False,
        # uniqueness would apply to the top-level items which might be sub-lists,
        # leading to potentially counter-intuitive results for deep uniqueness.
        raise ValueError(
            "unique=True generally requires flatten=True for predictable element-wise uniqueness "
            "across nested structures. If unique=True, an internal flattening pass will occur "
            "for the uniqueness logic anyway."
        )

    # Determine which types to skip during the flattening process
    current_skip_flatten_types = (
        _NO_TUPLE_SET_FLATTEN_SKIP_TYPES
        if not flatten_tuple_set
        else _DEFAULT_SKIP_FLATTEN_TYPES
    )

    # Stage 1: Convert the initial input to a list format
    intermediate_list = _initial_conversion_to_list(input_, use_values)

    # Stage 2: Apply user-specified flattening and dropna operations
    # This list's structure depends on the `flatten` flag provided by the user.
    processed_list = _recursive_process_list(
        intermediate_list,
        flatten_flag=flatten,  # User's desired flattening for the main output structure
        dropna_flag=dropna,
        skip_flatten_types=current_skip_flatten_types,
    )

    # Stage 3: Apply uniqueness if requested
    if unique:
        # For uniqueness, we need to operate on individual elements.
        # If the `processed_list` is not already flat (because user set flatten=False),
        # we perform an internal flattening pass specifically for the uniqueness logic.
        if not flatten:  # `processed_list` might contain sub-lists
            elements_for_uniqueness = _recursive_process_list(
                list(processed_list),  # Operate on a copy if further processing
                flatten_flag=True,  # Force flatten for unique logic
                dropna_flag=dropna,  # Re-apply dropna on the now flat stream
                skip_flatten_types=current_skip_flatten_types,
            )
        else:  # `processed_list` is already flat as per user's `flatten=True`
            # Ensure dropna has been applied to these flat elements
            if dropna:
                elements_for_uniqueness = [
                    item
                    for item in processed_list
                    if not (item is None or item is PydanticUndefined)
                ]
            else:
                elements_for_uniqueness = processed_list

        final_unique_list: list[Any] = []
        seen_hashes: set[int] = set()

        for item in elements_for_uniqueness:
            item_hash: int
            try:
                # Attempt direct hash first for performance with primitives/hashable objects
                item_hash = hash(item)
            except TypeError:
                if DICT_HASH_FUNC is None:
                    from lionfuncs.hash_utils import hash_dict

                    DICT_HASH_FUNC = hash_dict()

                # Fallback to the robust deterministic hasher for complex/unhashable types
                try:
                    item_hash = DICT_HASH_FUNC(item)  # Using the imported hash_dict
                except TypeError:
                    # Extremely rare case: item is unhashable even by hash_dict.
                    # To avoid O(N^2) comparison, this item will be added, potentially
                    # leading to duplicates if multiple such identical unhashable items exist.
                    # This is a performance trade-off.
                    final_unique_list.append(item)
                    continue  # Skip adding to seen_hashes set

            if item_hash not in seen_hashes:
                seen_hashes.add(item_hash)
                final_unique_list.append(item)
        return final_unique_list

    return processed_list
