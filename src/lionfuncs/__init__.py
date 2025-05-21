"""lionfuncs - A collection of general-purpose Python utilities."""

__version__ = "3.1.3"

from lionfuncs.dict_utils import fuzzy_match_keys
from lionfuncs.format_utils import as_readable
from lionfuncs.hash_utils import hash_dict
from lionfuncs.oai_schema_utils import (
    function_to_openai_schema,
    pydantic_model_to_openai_schema,
)
from lionfuncs.parsers import fuzzy_parse_json
from lionfuncs.to_dict import to_dict
from lionfuncs.to_json import to_json
from lionfuncs.to_list import to_list
from lionfuncs.utils import force_async, get_env_bool, get_env_dict, is_coro_func

__all__ = (
    "fuzzy_match_keys",
    "as_readable",
    "fuzzy_parse_json",
    "force_async",
    "get_env_bool",
    "get_env_dict",
    "is_coro_func",
    "to_list",
    "hash_dict",
    "to_dict",
    "to_json",
    "function_to_openai_schema",
    "pydantic_model_to_openai_schema",
)
