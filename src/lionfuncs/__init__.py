"""lionfuncs - A collection of general-purpose Python utilities."""

__version__ = "3.1.2"

from lionfuncs.dict_utils import fuzzy_match_keys
from lionfuncs.format_utils import as_readable
from lionfuncs.parsers import fuzzy_parse_json
from lionfuncs.schema_utils import function_to_openai_schema
from lionfuncs.text_utils import string_similarity

# Import key functions for direct access
from lionfuncs.utils import (
    force_async,
    get_env_bool,
    get_env_dict,
    hash_dict,
    is_coro_func,
    to_dict,
    to_list,
)

__all__ = [
    # utils
    "force_async",
    "get_env_bool",
    "get_env_dict",
    "hash_dict",
    "is_coro_func",
    "to_dict",
    "to_list",
    # text_utils
    "string_similarity",
    # parsers
    "fuzzy_parse_json",
    # dict_utils
    "fuzzy_match_keys",
    # format_utils
    "as_readable",
    # schema_utils
    "function_to_openai_schema",
]
