import re

_is_num_re = re.compile(r"^\s*[+-]?\d+(\.\d+)?\s*$")
_is_comma_num_re = re.compile(r"^\s*[+-]?\d\d?\d?(?:,\d\d\d)+(\.\d+)?\s*$")


def is_num(s):
    return isinstance(s, (int, float)) or (
        isinstance(s, str) and (_is_num_re.match(s) or _is_comma_num_re.match(s))
    )


def as_num(s):
    if not isinstance(s, str):
        return s
    if "." in s:
        try:
            return float(s.replace(",", ""))
        except ValueError:
            return s
    try:
        return int(s.replace(",", ""))
    except ValueError:
        return s
