from typing import Any


def assert_response(got: Any, want: Any):
    if isinstance(got, dict) and isinstance(want, dict):
        for k, v in want.items():
            got_attr = got.get(k)
            if isinstance(got_attr, dict):
                assert_response(got_attr, v)
            elif isinstance(got_attr, list):
                for i, item in enumerate(got_attr):
                    assert_response(item, v[i])
            else:
                message = (
                    f"got: {got_attr} ({type(got_attr)}), "
                    f"want: {v} ({type(v)})"
                )
                assert got_attr == v, message
    else:
        message = (
            f"got: {got} ({type(got)}), "
            f"want:{want} ({type(want)})"
        )
        assert got == want, message
