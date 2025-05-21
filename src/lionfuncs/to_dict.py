from collections.abc import Callable, Mapping
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel
from pydantic_core import PydanticUndefined

DEFAULT_JSON_PARSER = None


def _internal_xml_to_dict_parser(
    xml_string: str, remove_root: bool = True, **kwargs: Any
) -> dict[str, Any]:
    import xmltodict

    parsed = xmltodict.parse(xml_string, **kwargs)
    if remove_root and isinstance(parsed, dict) and len(parsed) == 1:
        root_key = list(parsed.keys())[0]
        content = parsed[root_key]
        return dict(content) if isinstance(content, Mapping) else {root_key: content}
    return dict(parsed)


def _convert_item_to_dict_element(
    item: Any,
    use_model_dump: bool,
    use_enum_values: bool,
    parse_strings: bool,
    str_type_for_parsing: Literal["json", "xml"] | None,
    fuzzy_parse_strings: bool,
    custom_str_parser: Callable[[str], Any] | None,
    **serializer_kwargs: Any,
) -> Any:
    global DEFAULT_JSON_PARSER
    if DEFAULT_JSON_PARSER is None:
        import orjson

        DEFAULT_JSON_PARSER = orjson.loads

    if item is None or item is PydanticUndefined:
        return item

    if isinstance(item, BaseModel):
        # DEFAULT_JSON_PARSER is already ensured to be initialized at the function start

        potential_result = PydanticUndefined  # Initialize potential_result

        # Construct the ordered list of methods to attempt on the BaseModel instance.
        ordered_methods = []
        if use_model_dump:
            if hasattr(item, "model_dump"):
                ordered_methods.append(("model_dump", serializer_kwargs))
            if hasattr(item, "dict") and (
                not hasattr(item, "model_dump") or item.dict != item.model_dump
            ):
                ordered_methods.append(("dict", {}))
        else:  # use_model_dump is False
            if hasattr(item, "dict"):
                ordered_methods.append(
                    (
                        "dict",
                        serializer_kwargs if hasattr(item.dict, "__call__") else {},
                    )
                )
            if hasattr(item, "model_dump") and (
                not hasattr(item, "dict") or item.model_dump != item.dict
            ):
                ordered_methods.append(("model_dump", {}))

        # Add other common serialization methods if not already covered, including general custom ones
        common_fallbacks = [
            "_asdict",
            "asdict",
            "to_dict",
            "as_list",
            "to_custom_dict",
            "get_config",
        ]  # Added more fallbacks
        for m_name in common_fallbacks:
            is_present_in_ordered = any(
                om_name == m_name for om_name, _ in ordered_methods
            )
            if (
                hasattr(item, m_name)
                and callable(getattr(item, m_name))
                and not is_present_in_ordered
            ):
                is_alias_of_present = False
                for existing_method_name, _ in ordered_methods:
                    if getattr(item, m_name) == getattr(item, existing_method_name):
                        is_alias_of_present = True
                        break
                if not is_alias_of_present:
                    # For these custom/general fallbacks, pass serializer_kwargs if they might accept them.
                    # Heuristic: if 'dict' or 'dump' or 'config' is in the name, or it's a known one like 'to_dict'.
                    # Otherwise, pass empty dict.
                    pass_kwargs = (
                        serializer_kwargs
                        if m_name in ["to_dict", "to_custom_dict", "get_config"]
                        or "dict" in m_name
                        or "dump" in m_name
                        else {}
                    )
                    ordered_methods.append((m_name, pass_kwargs))

        # Attempt methods in the constructed order
        for method_name, m_kwargs in ordered_methods:
            try:
                res = getattr(item, method_name)(**m_kwargs)

                if isinstance(res, Mapping):
                    if use_enum_values:
                        processed_dict = {}
                        for k, v_item in res.items():
                            processed_dict[k] = (
                                v_item.value if isinstance(v_item, Enum) else v_item
                            )
                        return processed_dict
                    return res  # Found a dictionary, return it immediately

                # If 'res' is not a dictionary, process it further
                if isinstance(res, str):
                    try:
                        parsed_res = DEFAULT_JSON_PARSER(res)
                        # Whether parsed_res is a dict or not, it's the outcome of this string method.
                        # If it parsed to a dict, it would have been caught by the isinstance(res, Mapping)
                        # check IF the method returned a dict-like string that DEFAULT_JSON_PARSER made a dict.
                        # More likely, if res is string, we want to see if it parses to something.
                        # If parsed_res is a Mapping, it should be returned above.
                        # If parsed_res is NOT a Mapping (e.g. list, int from JSON string), store it.
                        potential_result = parsed_res
                        if item.__class__.__name__ == "ModelReturnsListAsListMethod":
                            print(
                                f"DEBUG: String parsed to non-Mapping. potential_result set to: {potential_result} (type: {type(potential_result)})"
                            )
                    except Exception:
                        # Parsing failed. The original string 'res' is the outcome.
                        potential_result = res
                else:
                    # 'res' is not a Mapping and not a string (e.g., list, int, None directly from method).
                    potential_result = res

                # Loop continues: a non-dict result is stored in potential_result,
                # but we keep trying other methods in case a later one yields a direct dictionary.
            except Exception:
                continue  # Method call failed, try next

        # After trying all methods:
        if potential_result is not PydanticUndefined:
            # A method was called and returned something that wasn't a direct dictionary
            # (or was a string that didn't parse to a dictionary). Return that result.
            return potential_result

        # All methods failed to produce any result (potential_result is still PydanticUndefined)
        # or all methods that produced results, produced dictionaries (which were returned earlier).
        # This path means no successful non-dictionary result was stored and no dictionary was found.
        return vars(item) if hasattr(item, "__dict__") else item

    if isinstance(item, type) and issubclass(item, Enum):
        enum_members = item.__members__
        return (
            {name: member.value for name, member in enum_members.items()}
            if use_enum_values
            else {name: member for name, member in enum_members.items()}
        )

    if isinstance(item, Enum):
        return item.value if use_enum_values else item

    if isinstance(item, (set, frozenset)):
        try:
            return {v_set: v_set for v_set in item}
        except TypeError:
            return item

    if parse_strings and isinstance(item, str):
        parser_to_use: Callable[[str], Any] | None = None
        parser_args = serializer_kwargs.copy()
        final_parsed_result = item

        if custom_str_parser:

            def custom_parser_wrapper(s):
                return custom_str_parser(s, **parser_args)

            parser_to_use = custom_parser_wrapper
        elif str_type_for_parsing == "json":
            from lionfuncs.parsers import fuzzy_parse_json

            json_parser_func = (
                fuzzy_parse_json if fuzzy_parse_strings else DEFAULT_JSON_PARSER
            )

            def json_parser_wrapper(s):
                return json_parser_func(s, **parser_args)

            parser_to_use = json_parser_wrapper
        elif str_type_for_parsing == "xml":
            xml_args_local = {
                k: parser_args.pop(k)
                for k in ["remove_root", "root_tag"]
                if k in parser_args
            }

            def xml_parser_wrapper(s_xml):
                return _internal_xml_to_dict_parser(
                    s_xml, **xml_args_local, **parser_args
                )

            parser_to_use = xml_parser_wrapper

        if parser_to_use:
            try:
                final_parsed_result = parser_to_use(item)
            except Exception:
                pass  # Keep original string if parsing fails
        return final_parsed_result

    if (
        not isinstance(
            item,
            (
                Mapping,
                list,
                tuple,
                str,
                int,
                float,
                bool,
                bytes,
                bytearray,
                set,
                frozenset,
            ),
        )
        and item is not None
    ):
        methods_to_try_custom = ("to_dict", "_asdict", "asdict")
        for method_name in methods_to_try_custom:
            if hasattr(item, method_name):
                try:
                    return getattr(item, method_name)(**serializer_kwargs)
                except Exception:
                    continue
        if hasattr(item, "dict") and callable(item.dict):
            try:
                return item.dict(**serializer_kwargs)
            except Exception:
                pass
        if hasattr(item, "__dict__"):
            return vars(item)
    return item


def _recursive_apply_to_dict(
    current_data: Any,
    current_depth: int,
    max_depth: int,
    stop_types: tuple[type[Any], ...],
    conversion_params: dict[str, Any],
) -> Any:
    processed_node = _convert_item_to_dict_element(current_data, **conversion_params)

    if (
        current_depth >= max_depth
        or isinstance(processed_node, stop_types)
        or processed_node is None
    ):
        return processed_node

    if isinstance(processed_node, Mapping):
        return {
            key: _recursive_apply_to_dict(
                value, current_depth + 1, max_depth, stop_types, conversion_params
            )
            for key, value in processed_node.items()
        }
    elif isinstance(processed_node, (list, tuple)):
        return type(processed_node)(
            [
                _recursive_apply_to_dict(
                    elem, current_depth + 1, max_depth, stop_types, conversion_params
                )
                for elem in processed_node
            ]
        )
    elif isinstance(processed_node, (set, frozenset)):
        recursed_elements = [
            _recursive_apply_to_dict(
                elem, current_depth + 1, max_depth, stop_types, conversion_params
            )
            for elem in processed_node
        ]
        try:
            return type(processed_node)(recursed_elements)
        except TypeError:
            return recursed_elements

    return processed_node


def to_dict(
    input_: Any,
    /,
    *,
    use_model_dump: bool = True,
    use_enum_values: bool = False,
    parse_strings: bool = False,
    str_type_for_parsing: Literal["json", "xml"] | None = "json",
    fuzzy_parse_strings: bool = False,
    custom_str_parser: Callable[[str], Any] | None = None,
    recursive: bool = False,
    max_recursive_depth: int = 5,
    recursive_stop_types: tuple[type[Any], ...] = (
        str,
        int,
        float,
        bool,
        bytes,
        bytearray,
        type(None),
    ),
    suppress_errors: bool = False,
    default_on_error: dict[str, Any] | None = None,
    convert_top_level_iterable_to_dict: bool = False,
    **kwargs: Any,
) -> dict[str, Any]:
    if input_ is None or input_ is PydanticUndefined:
        return (
            default_on_error if suppress_errors and default_on_error is not None else {}
        )

    if not isinstance(max_recursive_depth, int) or max_recursive_depth < 0:
        raise ValueError("max_recursive_depth must be a non-negative integer.")
    effective_max_depth = min(max_recursive_depth, 20) if recursive else 0

    conversion_params = {
        "use_model_dump": use_model_dump,
        "use_enum_values": use_enum_values,
        "parse_strings": parse_strings,
        "str_type_for_parsing": str_type_for_parsing,
        "fuzzy_parse_strings": fuzzy_parse_strings,
        "custom_str_parser": custom_str_parser,
        **kwargs,
    }

    final_result: Any
    error_message_detail = ""
    try:
        final_result = _recursive_apply_to_dict(
            input_,
            current_depth=0,
            max_depth=effective_max_depth,
            stop_types=recursive_stop_types,
            conversion_params=conversion_params,
        )
        # print(f"DEBUG: final_result type: {type(final_result)}, value: {str(final_result)[:200]}") # DEBUG PRINT

        if isinstance(final_result, Mapping):
            return dict(final_result)

        if convert_top_level_iterable_to_dict:
            if isinstance(final_result, (list, tuple)):
                return {str(idx): item_val for idx, item_val in enumerate(final_result)}
            if isinstance(
                final_result, (set, frozenset)
            ):  # Was already converted to dict by _convert_item... if possible
                error_message_detail = f"Top-level set items unhashable or did not form dict. Processed: {str(final_result)[:100]}"

        error_message_detail = (
            error_message_detail
            or f"Top-level input of type '{type(input_).__name__}' processed to type '{type(final_result).__name__}', which is not a dictionary."
        )
        # print(f"DEBUG: About to raise ValueError with message: {error_message_detail}") # DEBUG PRINT
        if suppress_errors:
            return default_on_error if default_on_error is not None else {}
        raise ValueError(error_message_detail)

    except Exception as e:
        # print(f"DEBUG: Caught exception: {type(e).__name__}: {e}") # DEBUG PRINT
        if suppress_errors:
            return default_on_error if default_on_error is not None else {}
        final_err_message = f"Failed during to_dict conversion: {e}"
        if error_message_detail and str(e) not in error_message_detail:
            final_err_message = f"{error_message_detail}. Underlying error: {e}"
        raise ValueError(final_err_message) from e
