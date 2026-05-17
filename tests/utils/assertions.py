"""Assertion helpers for comparing API response payloads against expected values.

The helpers perform a *subset check*: *want* may contain fewer keys than
*got*, so tests only assert the fields they care about.  Extra fields in
*got* are silently ignored.
"""

from typing import Any


def assert_response(got: Any, want: Any) -> None:
    """Recursively assert that *got* contains at least the fields in *want*.

    - **dict vs dict**: every key in *want* must exist in *got* with an equal
      value (compared recursively for nested dicts/lists).
    - **list items**: each element of *got* is compared against the
      corresponding element of *want*.
    - **scalar**: plain ``==`` comparison with an informative failure message.

    Args:
        got:  The actual value returned by the API.
        want: The expected subset of values to assert against.

    Raises:
        AssertionError: On the first mismatch, with a message showing both
            the actual and expected value together with their types.
    """
    if isinstance(got, dict) and isinstance(want, dict):
        for key, expected_value in want.items():
            actual_value = got.get(key)
            if isinstance(actual_value, dict):
                assert_response(actual_value, expected_value)
            elif isinstance(actual_value, list):
                for i, item in enumerate(actual_value):
                    assert_response(item, expected_value[i])
            else:
                message = (
                    f"key={key!r}: "
                    f"got {actual_value!r} ({type(actual_value).__name__}), "
                    f"want {expected_value!r} ({type(expected_value).__name__})"
                )
                assert actual_value == expected_value, message
    else:
        message = (
            f"got {got!r} ({type(got).__name__}), "
            f"want {want!r} ({type(want).__name__})"
        )
        assert got == want, message
