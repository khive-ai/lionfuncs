from collections.abc import Mapping, Sequence
from functools import partial
from typing import Any, Callable, Literal

from pydantic_core import PydanticUndefined


def fuzzy_match_keys(
    data_dict: dict[str, Any],
    reference_keys: Sequence[str] | dict[str, Any],
    *,
    threshold: float = 0.8,
    default_method: Literal["levenshtein", "jaro_winkler", "wratio"] = "wratio",
    jaro_winkler_prefix_weight: float = 0.1,
    case_sensitive: bool = False,
    handle_unmatched: Literal["ignore", "raise", "remove", "fill", "force"] = "ignore",
    fill_value: Any = PydanticUndefined,
    fill_mapping: dict[str, Any] | None = None,
    strict: bool = False,
) -> dict[str, Any]:
    """
    Matches dictionary keys fuzzily against reference keys, returning a new dictionary.
    Leverages `rapidfuzz` for efficient similarity calculations and matching.

    Args:
        data_dict: The dictionary whose keys need validation/correction.
        reference_keys: A sequence (list, tuple) of expected key names, or a
                        dictionary from which expected keys will be extracted.
        threshold: Minimum similarity score (0.0 to 1.0) for a fuzzy match.
        default_method: String similarity algorithm for fuzzy matching via `rapidfuzz`.
                        Options: "levenshtein" (ratio), "jaro_winkler", "wratio" (default).
        jaro_winkler_prefix_weight: The prefix weight for Jaro-Winkler similarity (default 0.1).
                                   Only used if `default_method` is "jaro_winkler".
        case_sensitive: If False (default), comparisons are case-insensitive.
        handle_unmatched: Strategy for keys in `data_dict` that don't match any
                          reference key. ("ignore", "raise", "remove", "fill", "force")
        fill_value: Value for reference keys not found in `data_dict` if `handle_unmatched`
                    is "fill" or "force". Defaults to a PydanticUndefined sentinel.
        fill_mapping: Dictionary mapping specific reference keys to custom fill values.
        strict: If True, raise ValueError if any `reference_key` is not present
                in the final corrected dictionary.

    Returns:
        A new dictionary with keys mapped to reference_keys where possible.

    Raises:
        TypeError: If input types are invalid.
        ValueError: For invalid parameters or if an unmatched key is found
                    when `handle_unmatched="raise"`, or if `strict=True` and
                    a reference key is missing.
        ImportError: If `rapidfuzz` is required for fuzzy matching but not installed
                     (unless placeholders are active, which they shouldn't be in prod).
    """
    if not isinstance(data_dict, dict):
        raise TypeError("data_dict must be a dictionary.")
    if not isinstance(reference_keys, (Sequence, Mapping)):
        raise TypeError(
            "reference_keys must be a sequence (list/tuple) or a mapping (dict)."
        )
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0.0 and 1.0.")
    if not (
        isinstance(default_method, str)
        and default_method.lower() in ["levenshtein", "jaro_winkler", "wratio"]
    ):
        raise ValueError(
            "default_method must be one of 'levenshtein', 'jaro_winkler', 'wratio'."
        )
    if (
        not 0.0 <= jaro_winkler_prefix_weight <= 0.25
    ):  # As per rapidfuzz doc for jaro_winkler
        raise ValueError("jaro_winkler_prefix_weight must be between 0.0 and 0.25.")

    expected_keys_list: list[str]
    if isinstance(reference_keys, Mapping):
        expected_keys_list = list(reference_keys.keys())
    else:
        if not all(
            isinstance(k, str) for k in reference_keys
        ):  # Ensure all elements are strings
            raise TypeError(
                "If reference_keys is a sequence, all its elements must be strings."
            )
        expected_keys_list = list(reference_keys)

    if not expected_keys_list:
        if handle_unmatched in ("remove", "force"):
            return {}
        if handle_unmatched == "raise" and data_dict:
            raise ValueError(
                f"Unmatched input keys: {list(data_dict.keys())} (no reference keys provided)."
            )
        return data_dict.copy()

    # Map of {comparison_form_of_expected_key: original_expected_key}
    expected_keys_map: dict[str, str] = {
        (key if case_sensitive else key.lower()): key for key in expected_keys_list
    }
    # List of unique comparison forms of expected keys for rapidfuzz.process.extractOne choices
    expected_comparison_forms_for_choices = list(expected_keys_map.keys())

    corrected_out: dict[str, Any] = {}
    mapped_input_keys: set[str] = set()  # Original input keys that were mapped
    mapped_expected_keys_orig_case: set[str] = (
        set()
    )  # Original reference keys that were matched

    # Pass 1: Exact Matches
    for input_key, input_value in data_dict.items():
        compare_input_key = input_key if case_sensitive else input_key.lower()
        if compare_input_key in expected_keys_map:
            original_expected_key = expected_keys_map[compare_input_key]
            # Ensure an expected key is only taken by one exact match (first one wins)
            if original_expected_key not in mapped_expected_keys_orig_case:
                corrected_out[original_expected_key] = input_value
                mapped_input_keys.add(input_key)
                mapped_expected_keys_orig_case.add(original_expected_key)

    # Pass 2: Fuzzy Matches
    # Only proceed if rapidfuzz is available and there are keys left to match
    if any(ik not in mapped_input_keys for ik in data_dict.keys()):
        remaining_input_for_fuzz = [
            ik for ik in data_dict.keys() if ik not in mapped_input_keys
        ]

        # Choices for extractOne: expected keys (comparison form) that are not yet mapped
        available_expected_comp_forms = [
            ek_comp
            for ek_comp in expected_comparison_forms_for_choices
            if expected_keys_map[ek_comp] not in mapped_expected_keys_orig_case
        ]

        if (
            remaining_input_for_fuzz and available_expected_comp_forms
        ):  # Only if there's work to do
            import rapidfuzz

            rf_scorer: Callable[..., float]
            method_name_lower = default_method.lower()

            if method_name_lower == "levenshtein":
                rf_scorer = rapidfuzz.fuzz.ratio
            elif method_name_lower == "wratio":
                rf_scorer = rapidfuzz.fuzz.WRatio
            elif method_name_lower == "jaro_winkler":
                rf_scorer = partial(
                    rapidfuzz.distance.JaroWinkler.similarity,
                    prefix_weight=jaro_winkler_prefix_weight,
                )

            # rapidfuzz's processor handles case transformation for query and choices
            processor_func = None if case_sensitive else str.lower

            for input_key in remaining_input_for_fuzz:
                if not available_expected_comp_forms:
                    break  # All expected keys have been matched

                match_result = rapidfuzz.process.extractOne(
                    query=input_key,  # Original input key
                    choices=available_expected_comp_forms,  # Comparison forms of available expected keys
                    scorer=rf_scorer,
                    score_cutoff=threshold,
                    processor=processor_func,  # Applies to query and choices before scoring
                )

                if match_result:
                    # choice is a key from available_expected_comp_forms (already in comparison form)
                    matched_expected_comp_form, score_rf, _ = (
                        match_result  # score_rf is 0-100
                    )
                    original_expected_key = expected_keys_map[
                        matched_expected_comp_form
                    ]

                    # Crucial: ensure this expected key hasn't been used by another fuzzy match
                    # and that this input key is still available.
                    if (
                        original_expected_key not in mapped_expected_keys_orig_case
                        and input_key not in mapped_input_keys
                    ):
                        corrected_out[original_expected_key] = data_dict[input_key]
                        mapped_input_keys.add(input_key)
                        mapped_expected_keys_orig_case.add(original_expected_key)
                        available_expected_comp_forms.remove(matched_expected_comp_form)
    elif any(ik not in mapped_input_keys for ik in data_dict.keys()):
        print(
            f"Warning: rapidfuzz not available, fuzzy matching pass skipped for unmapped input keys. Input keys: {list(data_dict.keys())}, Mapped: {mapped_input_keys}"
        )

    # Pass 3: Handle Unmatched Input Keys and Fill Missing Expected Keys
    final_unmatched_input_keys = [
        ik for ik in data_dict.keys() if ik not in mapped_input_keys
    ]
    # Expected keys (original case) that were not matched from reference_keys_list
    missing_expected_keys_orig_case = [
        ek_orig
        for ek_orig in expected_keys_list
        if ek_orig not in mapped_expected_keys_orig_case
    ]

    if handle_unmatched == "raise" and final_unmatched_input_keys:
        raise ValueError(f"Unmatched input keys found: {final_unmatched_input_keys}")

    if handle_unmatched == "ignore":
        for key_in in final_unmatched_input_keys:
            if key_in not in corrected_out:  # Should be true, as these are unmatched
                corrected_out[key_in] = data_dict[key_in]

    if handle_unmatched == "fill" or handle_unmatched == "force":
        for expected_k_orig in missing_expected_keys_orig_case:
            # Only add if not already present (e.g. via an exact match that used a different case of input key)
            if expected_k_orig not in corrected_out:
                if fill_mapping and expected_k_orig in fill_mapping:
                    corrected_out[expected_k_orig] = fill_mapping[expected_k_orig]
                elif fill_value is not PydanticUndefined:  # Check against sentinel
                    corrected_out[expected_k_orig] = fill_value
                # If fill_value is PydanticUndefined (default) & not in fill_mapping, key is NOT added

        if (
            handle_unmatched == "fill"
        ):  # "fill" mode also keeps original unmatched inputs
            for key_in in final_unmatched_input_keys:
                if key_in not in corrected_out:
                    corrected_out[key_in] = data_dict[key_in]

    # Pass 4: Strict Mode Check (all original reference keys must be in output)
    if strict:
        # Re-check based on the final state of corrected_out keys
        current_output_keys = set(corrected_out.keys())
        strictly_missing_expected_keys = [
            ek_orig
            for ek_orig in expected_keys_list
            if ek_orig not in current_output_keys
        ]
        if strictly_missing_expected_keys:
            raise ValueError(
                f"Strict mode: Missing required reference keys in output: {strictly_missing_expected_keys}"
            )

    return corrected_out
