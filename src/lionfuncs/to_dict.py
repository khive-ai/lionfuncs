import copy
import timeit
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
        if use_model_dump and hasattr(item, "model_dump"):
            try:
                return item.model_dump(**serializer_kwargs)
            except Exception:
                pass
        methods_to_try = ("model_dump", "dict", "_asdict", "asdict")
        for method_name in methods_to_try:
            if hasattr(item, method_name):
                try:
                    res = getattr(item, method_name)()
                    if isinstance(res, str):
                        return DEFAULT_JSON_PARSER(res)
                    return res if isinstance(res, Mapping) else vars(item)
                except Exception:
                    continue
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

        if suppress_errors:
            return default_on_error if default_on_error is not None else {}
        raise ValueError(error_message_detail)

    except Exception as e:
        if suppress_errors:
            return default_on_error if default_on_error is not None else {}
        final_err_message = f"Failed during to_dict conversion: {e}"
        if error_message_detail and str(e) not in error_message_detail:
            final_err_message = f"{error_message_detail}. Underlying error: {e}"
        raise ValueError(final_err_message) from e


# --- End of to_dict_lionagi Implementation ---


if __name__ == "__main__":
    # --- Test Data Setup ---
    class MyEnum(Enum):
        KEY_A = "value_alpha"
        KEY_B = 123
        KEY_C = True

    class AnotherEnum(Enum):
        X = "x_val"
        Y = "y_val"

    class DetailModel(BaseModel):
        detail_attr: str
        detail_num: int
        detail_enum_val: MyEnum = MyEnum.KEY_C

        class Config:
            frozen = True  # Make models hashable for sets

    class MainModel(BaseModel):
        id: int
        name: str
        data: dict[str, Any]
        maybe_none: str | None = None
        detail_obj: DetailModel
        list_of_details: list[DetailModel] = []
        enum_val: MyEnum = MyEnum.KEY_A

        class Config:
            frozen = True

    class CustomPlainObject:
        def __init__(self, x, y):
            self.x = x
            self.y = y

        def to_dict(self):
            return {"x_custom": self.x, "y_custom": self.y}

    class CustomWithVars:
        def __init__(self, alpha, beta):
            self.alpha = alpha
            self.beta = beta

    detail1_data = {
        "detail_attr": "Detail 1",
        "detail_num": 101,
        "detail_enum_val": MyEnum.KEY_B,
    }
    detail2_data = {
        "detail_attr": "Detail 2",
        "detail_num": 202,
        "detail_enum_val": MyEnum.KEY_C,
    }
    detail1 = DetailModel(**detail1_data)  # type: ignore
    detail2 = DetailModel(**detail2_data)  # type: ignore

    main_model_data = {
        "id": 1,
        "name": "Main Test",
        "data": {
            "nested_key": "nested_val",
            "num_list": [1, 2, 3],
            "sub_enum": AnotherEnum.X,
        },
        "detail_obj": detail1,  # Pass Pydantic instance directly
        "list_of_details": [detail1, detail2],
        "enum_val": MyEnum.KEY_A,
    }
    main_model_instance = MainModel(**main_model_data)
    main_model_json_string = main_model_instance.model_dump_json()
    fuzzy_json_string = '{\'id\': 2, name: "Fuzzy", "data": null, "list_val": [1,true,\'item\'] // comment}'  # null instead of None
    xml_string_example = "<root><item_id>123</item_id><name>Thingy</name><values><value>A</value><value>B</value></values></root>"
    xml_string_no_root_to_remove = "<data><item_id>1</item_id><name>Solo</name></data>"

    to_dict_test_data = [
        ("plain_dict", {"a": 1, "b": "two"}),
        ("pydantic_model", main_model_instance),
        ("json_str_valid_obj", main_model_json_string),
        ("json_str_fuzzy_obj", fuzzy_json_string),
        ("json_str_array", '[1,2,{"valid":true}]'),
        ("xml_str_root_remove", xml_string_example),
        ("xml_str_no_root_remove", xml_string_no_root_to_remove),
        ("enum_type", MyEnum),
        ("enum_member", MyEnum.KEY_A),
        ("set_simple", {1, "b", True}),
        (
            "set_complex_hashable",
            {detail1, "str_item", True},
        ),  # detail1 is now hashable (frozen)
        ("list_simple", [10, 20, MyEnum.KEY_C]),
        ("custom_obj_to_dict", CustomPlainObject(x=10, y=20)),
        ("custom_obj_vars", CustomWithVars(alpha="A", beta="B")),
        ("none_input", None),
        ("pydantic_undefined", PydanticUndefined),
        ("custom_undefined", PydanticUndefined),
        (
            "nested_dict_complex",
            {
                "L0_model": main_model_instance,
                "L0_list": [
                    100,
                    detail1,
                    MyEnum.KEY_B,
                    fuzzy_json_string,
                    {
                        "L2_key": "L2_val",
                        "L2_model": detail2,
                        "L2_enum_type": AnotherEnum,
                        "L2_set": {MyEnum.KEY_A, "set_val", True},
                    },
                ],  # Set with hashable items
                "L0_str_json_obj": main_model_json_string,
                "L0_set_primitives": {1, 2, 3},
            },
        ),
    ]

    # --- Verification ---
    print("\n--- Verification of to_dict_lionagi ---")
    verification_params = [
        {"name": "Defaults", "params": {}},
        {"name": "Rec", "params": {"recursive": True}},
        {"name": "Rec_EnumVal", "params": {"recursive": True, "use_enum_values": True}},
        {
            "name": "Rec_ParseJSON",
            "params": {
                "recursive": True,
                "parse_strings": True,
                "str_type_for_parsing": "json",
            },
        },
        {
            "name": "Rec_ParseFuzzy",
            "params": {
                "recursive": True,
                "parse_strings": True,
                "str_type_for_parsing": "json",
                "fuzzy_parse_strings": True,
                "use_enum_values": True,
            },
        },
        {
            "name": "Rec_ParseXML",
            "params": {
                "recursive": True,
                "parse_strings": True,
                "str_type_for_parsing": "xml",
                "remove_root": True,
            },
        },
        {
            "name": "TopListSetToDict",
            "params": {"convert_top_level_iterable_to_dict": True},
        },
        {
            "name": "SuppressErr",
            "params": {
                "suppress_errors": True,
                "default_on_error": {"CONV_FAIL": True},
            },
        },
    ]
    verify_data_indices = [0, 1, 2, 3, 4, 5, 7, 9, 11, 14, 17]  # Subset for brevity
    verify_param_indices = [0, 1, 3, 4, 5, 6, 7]

    for i in verify_data_indices:
        data_name, test_input_orig = to_dict_test_data[i]
        print(f"\nInput: {data_name} (Type: {type(test_input_orig).__name__})")
        for p_idx in verify_param_indices:
            param_set = verification_params[p_idx]
            test_input = copy.deepcopy(test_input_orig)
            params_to_use = param_set["params"]

            should_skip = (
                params_to_use.get("str_type_for_parsing") == "xml" and not True
            ) or (params_to_use.get("fuzzy_parse_strings") and not True)
            if should_skip:
                print(f"  Params: {param_set['name']} - SKIPPED (lib missing)")
                continue

            print(f"  Params: {param_set['name']} -> {params_to_use}")
            try:
                result = to_dict(test_input, **params_to_use)
                print(
                    f"    Output: {str(result)[:110]}{'...' if len(str(result)) > 110 else ''}"
                )
                # Basic validation for top-level dict output
                if not isinstance(result, dict) and not params_to_use.get(
                    "suppress_errors"
                ):
                    is_enum_member_ok = (
                        data_name == "enum_member"
                        and isinstance(result, (str, int, bool, Enum))
                        and not params_to_use.get("recursive")
                    )
                    if not is_enum_member_ok:
                        print(
                            f"    WARNING: Expected dict, got {type(result).__name__}"
                        )
            except Exception as e:
                print(f"    ERROR: {type(e).__name__}: {str(e)[:110]}")

    # --- Benchmarking ---
    print("\n--- Benchmarking to_dict_lionagi ---")
    benchmark_scenarios = [
        ("Pydantic(NoRec)", to_dict_test_data[1][1], {}),
        (
            "Pydantic(Rec,Enum,Deep)",
            to_dict_test_data[1][1],
            {"recursive": True, "max_recursive_depth": 3, "use_enum_values": True},
        ),
        ("JSONStr(Valid,Parse)", to_dict_test_data[2][1], {"parse_strings": True}),
        (
            "JSONStr(Fuzzy,Parse)",
            to_dict_test_data[3][1],
            {"parse_strings": True, "fuzzy_parse_strings": True},
        ),
        (
            "JSONStr(Array,Parse,TopListDict)",
            to_dict_test_data[4][1],
            {"parse_strings": True, "convert_top_level_iterable_to_dict": True},
        ),
        (
            "XMLStr(Parse,RmRoot)",
            to_dict_test_data[5][1],
            {"parse_strings": True, "str_type_for_parsing": "xml", "remove_root": True},
        ),
        (
            "SetInput(ToValDict)",
            to_dict_test_data[9][1],
            {"convert_top_level_iterable_to_dict": True},
        ),  # Now includes complex type
        (
            "ListInput(ToIdxDict)",
            to_dict_test_data[11][1],
            {"convert_top_level_iterable_to_dict": True},
        ),
        (
            "ListInput(Fail,Suppress)",
            to_dict_test_data[11][1],
            {"suppress_errors": True, "default_on_error": {"failed": True}},
        ),
        (
            "Nested(FullRecFuzzy)",
            to_dict_test_data[17][1],
            {
                "recursive": True,
                "max_recursive_depth": 5,
                "parse_strings": True,
                "use_enum_values": True,
                "fuzzy_parse_strings": True,
            },
        ),
    ]

    benchmark_results_final = {}
    print("\n--- to_dict_lionagi Benchmark Summary ---")
    col_width = 35
    print(f"| {'Scenario':<{col_width}} | {'Time (µs/call)':<15} |")
    print(f"|:{'-' * (col_width - 1)}:|:{'-' * 14}:|")

    for name, input_orig, params in benchmark_scenarios:
        input_val = copy.deepcopy(input_orig)
        skip_scenario = (params.get("str_type_for_parsing") == "xml" and not True) or (
            params.get("fuzzy_parse_strings") and not True
        )
        if skip_scenario:
            timing_str = "SKIPPED"
        else:
            num_exec = 500
            if "Pydantic(NoRec)" == name or "JSONStr(Valid,Parse)" == name:
                num_exec = 1000
            elif "Nested" in name:
                num_exec = 50
            try:
                to_dict(copy.deepcopy(input_val), **params)  # Warm-up
                actual_time = timeit.timeit(
                    lambda: to_dict(copy.deepcopy(input_val), **params),
                    number=num_exec,
                )
                time_us = (actual_time / num_exec) * 1_000_000
                timing_str = f"{time_us:<15.2f}"
                benchmark_results_final[name] = time_us
            except Exception as e_bench:
                timing_str = f"ERROR: {type(e_bench).__name__}"
                benchmark_results_final[name] = timing_str
        print(f"| {name:<{col_width}} | {timing_str} |")
