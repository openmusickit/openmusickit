"""The canonical text of a JSON value, and a strict parser,
as the format specification's §9 and §4.1–4.9 define them.

`dumps` is written from the specification rather than borrowed from `json.dumps`,
which differs in two places that byte-identical round trips depend on:
it writes floats as Python's `repr` does (`1e+16`, where ECMAScript writes
`10000000000000000`), and it accepts NaN and lone surrogates.
`loads` is `json.loads` with the checks the specification adds:
no duplicate keys, no NaN or Infinity, no lone surrogates.

>>> print(dumps({"b": [1, "2/3"], "@id": None, "a": {}}), end="")
{
  "@id": null,
  "a": {},
  "b": [
    1,
    "2/3"
  ]
}
>>> loads('{"a": 1, "a": 2}')
Traceback (most recent call last):
...
openmusickit.errors.OmkJsonError: Duplicate key 'a' in an object.
"""

from __future__ import annotations

import json
import math
from decimal import Decimal
from typing import Any

from openmusickit.errors import OmkJsonError

_SHORT_ESCAPES = {
    '"': '\\"',
    "\\": "\\\\",
    "\b": "\\b",
    "\t": "\\t",
    "\n": "\\n",
    "\f": "\\f",
    "\r": "\\r",
}


def dumps(value: Any) -> str:
    """The canonical text of a JSON value (dicts with string keys, lists,
    strings, ints, finite floats, booleans and None), ending in a newline.

    >>> dumps([])
    '[]\\n'

    Raises
    ------
    TypeError
        for a value of any other type (a tuple, a Fraction, a non-string key).
    ValueError
        for a float that is not finite, or a string holding a lone surrogate.
    """
    parts: list[str] = []
    _write(value, 0, parts)
    parts.append("\n")
    return "".join(parts)


def _write(value: Any, depth: int, parts: list[str]) -> None:
    if value is None:
        parts.append("null")
    elif value is True:
        parts.append("true")
    elif value is False:
        parts.append("false")
    elif type(value) is int:
        parts.append(str(value))
    elif type(value) is float:
        parts.append(format_float(value))
    elif type(value) is str:
        parts.append(format_string(value))
    elif type(value) is list:
        _write_items([(None, item) for item in value], "[", "]", depth, parts)
    elif type(value) is dict:
        for key in value:
            if type(key) is not str:
                raise TypeError(f"An object key must be a string, not {key!r}.")
        items = sorted(value.items())  # str order is code point order, as §9.4 requires
        _write_items(items, "{", "}", depth, parts)
    else:
        raise TypeError(f"{value!r} is not JSON data (a {type(value).__name__}).")


def _write_items(
    items: list[tuple[str | None, Any]], opening: str, closing: str, depth: int, parts: list[str]
) -> None:
    if not items:
        parts.append(opening + closing)
        return
    indent = "  " * (depth + 1)
    parts.append(opening + "\n")
    for index, (key, item) in enumerate(items):
        parts.append(indent)
        if key is not None:
            parts.append(format_string(key) + ": ")
        _write(item, depth + 1, parts)
        parts.append(",\n" if index < len(items) - 1 else "\n")
    parts.append("  " * depth + closing)


def format_string(text: str) -> str:
    """A string as RFC 8785 writes it: only `"`, `\\` and control characters escaped.

    >>> print(format_string('say "é"\\t\\x01'))
    "say \\"é\\"\\t\\u0001"

    Raises
    ------
    ValueError
        if `text` holds a lone surrogate.
    """
    _check_surrogates(text)
    out = ['"']
    for character in text:
        if character in _SHORT_ESCAPES:
            out.append(_SHORT_ESCAPES[character])
        elif character < " ":
            out.append(f"\\u{ord(character):04x}")
        else:
            out.append(character)
    out.append('"')
    return "".join(out)


def format_float(number: float) -> str:
    """A finite float as ECMAScript's `Number.prototype.toString` writes it:
    the shortest digits that read back as the same double,
    in positional notation from 1e-6 up to (not including) 1e21,
    and in exponent notation outside that range.

    >>> [format_float(x) for x in (1.5, 100.0, 1e16, 1e21, 1e-7, -0.0, 0.000001)]
    ['1.5', '100', '10000000000000000', '1e+21', '1e-7', '0', '0.000001']

    Raises
    ------
    ValueError
        if `number` is NaN or infinite.
    """
    if not math.isfinite(number):
        raise ValueError(f"JSON has no {number!r}.")
    if number == 0:
        return "0"
    if number < 0:
        return "-" + format_float(-number)
    # repr gives the shortest round-tripping digits; ECMAScript's choice of digits is the same.
    sign, digit_tuple, exponent = Decimal(repr(number)).normalize().as_tuple()
    digits = "".join(map(str, digit_tuple))
    k = len(digits)
    n = exponent + k  # the value is 0.digits × 10^n
    if k <= n <= 21:
        return digits + "0" * (n - k)
    if 0 < n <= 21:
        return digits[:n] + "." + digits[n:]
    if -6 < n <= 0:
        return "0." + "0" * -n + digits
    exponent_text = f"e{'+' if n - 1 >= 0 else '-'}{abs(n - 1)}"
    if k == 1:
        return digits + exponent_text
    return digits[0] + "." + digits[1:] + exponent_text


def loads(text: str) -> Any:
    """Parses JSON text, refusing what the specification refuses:
    a duplicate key in an object, NaN or Infinity, a lone surrogate.

    >>> loads('{"x": [1, 2.5, "a", null]}')
    {'x': [1, 2.5, 'a', None]}

    Raises
    ------
    OmkJsonError
        if `text` is not JSON, or is JSON the specification refuses.
    """
    try:
        value = json.loads(text, object_pairs_hook=_no_duplicates, parse_constant=_no_constant)
    except json.JSONDecodeError as error:
        raise OmkJsonError(f"Not JSON: {error}.") from error
    _check_strings(value)
    return value


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise OmkJsonError(f"Duplicate key {key!r} in an object.")
        result[key] = value
    return result


def _no_constant(name: str) -> Any:
    raise OmkJsonError(f"JSON has no {name}.")


def _check_strings(value: Any) -> None:
    if type(value) is str:
        try:
            _check_surrogates(value)
        except ValueError as error:
            raise OmkJsonError(str(error)) from error
    elif type(value) is list:
        for item in value:
            _check_strings(item)
    elif type(value) is dict:
        for key, item in value.items():
            _check_strings(key)
            _check_strings(item)


def _check_surrogates(text: str) -> None:
    try:
        text.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ValueError(f"A string cannot hold a lone surrogate: {text!r}.") from error
