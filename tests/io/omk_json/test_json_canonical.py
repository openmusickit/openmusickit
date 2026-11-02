"""The canonical text of JSON values (format specification §9) and the strict parser.

The float table is RFC 8785's Appendix B sample of IEEE 754 bit patterns;
on 2026-11-02 it, every code point below U+00A0 (through `format_string`),
and 250,142 further doubles (through `format_float`)
were checked against Node 26's `JSON.stringify` with no mismatch.
"""

import json
import math
import struct

import pytest
from hypothesis import given
from hypothesis import strategies as st

from openmusickit.errors import OmkJsonError
from openmusickit.io.omk_json.canonical import dumps, format_float, format_string, loads

RFC_8785_FLOATS = {
    "0000000000000000": "0",
    "8000000000000000": "0",
    "0000000000000001": "5e-324",
    "8000000000000001": "-5e-324",
    "7fefffffffffffff": "1.7976931348623157e+308",
    "ffefffffffffffff": "-1.7976931348623157e+308",
    "4340000000000000": "9007199254740992",
    "c340000000000000": "-9007199254740992",
    "4430000000000000": "295147905179352830000",
    "44b52d02c7e14af5": "9.999999999999997e+22",
    "44b52d02c7e14af6": "1e+23",
    "44b52d02c7e14af7": "1.0000000000000001e+23",
    "444b1ae4d6e2ef4e": "999999999999999700000",
    "444b1ae4d6e2ef4f": "999999999999999900000",
    "444b1ae4d6e2ef50": "1e+21",
    "3eb0c6f7a0b5ed8c": "9.999999999999997e-7",
    "3eb0c6f7a0b5ed8d": "0.000001",
    "41b3de4355555553": "333333333.3333332",
    "41b3de4355555554": "333333333.33333325",
    "41b3de4355555555": "333333333.3333333",
    "41b3de4355555556": "333333333.3333334",
    "41b3de4355555557": "333333333.33333343",
    "becbf647612f3696": "-0.0000033333333333333333",
    "43143ff3c1cb0959": "1424953923781206.2",
}

json_scalars = (
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(allow_nan=False, allow_infinity=False)
    | st.text()
)
json_values = st.recursive(
    json_scalars,
    lambda children: st.lists(children) | st.dictionaries(st.text(), children),
    max_leaves=30,
)
json_values_with_exact_floats = st.recursive(
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(min_value=-(2.0**53), max_value=2.0**53)
    | st.text(),
    lambda children: st.lists(children) | st.dictionaries(st.text(), children),
    max_leaves=30,
)
json_values_without_floats = st.recursive(
    st.none() | st.booleans() | st.integers() | st.text(),
    lambda children: st.lists(children) | st.dictionaries(st.text(), children),
    max_leaves=30,
)


# --- floats and strings ----------------------------------------------------------------


@pytest.mark.parametrize("bits, expected", RFC_8785_FLOATS.items())
def test_floats_are_written_as_rfc_8785_writes_them(bits, expected):
    (number,) = struct.unpack(">d", bytes.fromhex(bits))
    assert format_float(number) == expected


@given(st.floats(allow_nan=False, allow_infinity=False))
def test_a_written_float_reads_back_as_the_same_double(number):
    assert float(format_float(number)) == number


@pytest.mark.parametrize("number", [math.nan, math.inf, -math.inf])
def test_a_float_that_is_not_finite_is_refused(number):
    with pytest.raises(ValueError):
        format_float(number)


def test_every_control_character_is_escaped_and_nothing_else():
    short = {
        '"': '\\"',
        "\\": "\\\\",
        "\b": "\\b",
        "\t": "\\t",
        "\n": "\\n",
        "\f": "\\f",
        "\r": "\\r",
    }
    for code in range(0x80):
        character = chr(code)
        if character in short:
            expected = short[character]
        elif code < 0x20:
            expected = f"\\u{code:04x}"
        else:
            expected = character
        assert format_string(character) == f'"{expected}"', hex(code)
    assert format_string("é \U0001d11e") == '"é \U0001d11e"'


def test_a_lone_surrogate_is_refused_both_ways():
    with pytest.raises(ValueError):
        format_string("\ud834")
    with pytest.raises(OmkJsonError):
        loads('"\\ud834"')
    assert loads('"\\ud834\\udd1e"') == "\U0001d11e"  # a pair is one character


# --- layout and order --------------------------------------------------------------------


def test_the_layout_of_a_small_document():
    text = dumps({"b": [1, {"y": True, "x": None}], "@id": "z", "a": {}, "c": []})
    assert text == (
        "{\n"
        '  "@id": "z",\n'
        '  "a": {},\n'
        '  "b": [\n'
        "    1,\n"
        "    {\n"
        '      "x": null,\n'
        '      "y": true\n'
        "    }\n"
        "  ],\n"
        '  "c": []\n'
        "}\n"
    )


def test_keys_are_sorted_by_code_point():
    keys = ["b", "B", "@type", "é", "\U0001d11e", "Ａ", "a1", "a"]
    text = dumps(dict.fromkeys(keys, 0))
    written = [line.split('"')[1] for line in text.splitlines()[1:-1]]
    assert written == sorted(keys, key=lambda key: [ord(c) for c in key])
    assert written[0] == "@type"


@given(json_values_without_floats)
def test_without_floats_the_layout_is_json_dumps_with_sorted_keys(value):
    expected = json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    assert dumps(value) == expected


@given(json_values)
def test_canonical_text_reads_back_and_writes_the_same_text(value):
    text = dumps(value)
    assert dumps(loads(text)) == text


@given(json_values_with_exact_floats)
def test_canonical_text_reads_back_as_an_equal_value(value):
    assert loads(dumps(value)) == value


def test_a_whole_float_reads_back_as_the_integer_its_text_spells():
    """JSON does not tell integers from other numbers (spec §4.9): a float is
    written as its shortest digits, and digits with no point or exponent read
    back as an integer. Below 2**53 that integer equals the float; above it, it
    is the shortest spelling, which need not be the float's exact value."""
    assert dumps(100.0) == dumps(100) == "100\n" and loads("100") == 100.0
    big = 5.125305974515977e16
    assert dumps(big) == "51253059745159770\n"
    assert loads(dumps(big)) == 51253059745159770 != big
    assert dumps(loads(dumps(big))) == dumps(big)


@pytest.mark.parametrize(
    "value", [(1, 2), {1: "a"}, {"a": (1,)}, {1.5}, b"bytes", object()], ids=repr
)
def test_values_that_are_not_json_data_are_refused(value):
    with pytest.raises(TypeError):
        dumps(value)


def test_a_bool_is_not_written_as_an_integer():
    assert dumps([True, 1, False, 0]) == "[\n  true,\n  1,\n  false,\n  0\n]\n"


# --- the parser --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        '{"a": 1, "a": 2}',
        '{"x": {"a": 1, "a": 1}}',
        '[{"a": 1, "b": 2, "a": 3}]',
    ],
)
def test_a_duplicate_key_is_refused_at_any_depth(text):
    with pytest.raises(OmkJsonError, match="Duplicate key"):
        loads(text)


@pytest.mark.parametrize("text", ["NaN", "[Infinity]", '{"a": -Infinity}'])
def test_nan_and_infinity_are_refused(text):
    with pytest.raises(OmkJsonError):
        loads(text)


@pytest.mark.parametrize("text", ["", "{", "[1,]", "{'a': 1}", "01", '"\\x41"'])
def test_text_that_is_not_json_is_refused(text):
    with pytest.raises(OmkJsonError, match="Not JSON"):
        loads(text)


def test_integers_of_any_size_are_kept_exactly():
    big = 2**200 + 1
    assert loads(dumps([big, -big])) == [big, -big]
