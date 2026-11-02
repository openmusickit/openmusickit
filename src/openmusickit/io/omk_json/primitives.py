"""The primitive types of the format specification (§4): each as a pair of
functions, one writing a Python value as JSON data and one reading it back.

A reader is strict: a value in any form but the canonical one
(`"2/4"` for a rational, an uppercase UUID, an enumeration's display value)
is outside the specification and is refused with `OmkJsonError`.

>>> from fractions import Fraction
>>> encode_rational(Fraction(-7, 3)), decode_rational("-7/3")
('-7/3', Fraction(-7, 3))
>>> encode_rational(Fraction(4, 2)), decode_rational(2)
(2, 2)
"""

from __future__ import annotations

import re
from enum import Enum
from fractions import Fraction
from typing import Any
from uuid import UUID

from openmusickit.errors import OmkJsonError

_RATIONAL = re.compile(r"-?[1-9][0-9]*/[1-9][0-9]*")
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def encode_rational(value: int | Fraction) -> int | str:
    """A rational as the specification writes it: an int if whole, otherwise `"n/d"`.

    Raises
    ------
    TypeError
        for anything but an int or a Fraction (a float, a bool).
    """
    if type(value) is int:
        return value
    if type(value) is Fraction:
        return (
            value.numerator if value.denominator == 1 else f"{value.numerator}/{value.denominator}"
        )
    raise TypeError(f"A rational is an int or a Fraction, not {value!r}.")


def decode_rational(data: Any) -> int | Fraction:
    """An int for a whole number, otherwise a Fraction.

    >>> decode_rational("2/4")
    Traceback (most recent call last):
    ...
    openmusickit.errors.OmkJsonError: '2/4' is not a rational in lowest terms; write '1/2'.

    Raises
    ------
    OmkJsonError
        for anything but an integer or an `"n/d"` string in lowest terms with `d` > 1.
    """
    if type(data) is int:
        return data
    if type(data) is str and _RATIONAL.fullmatch(data):
        value = Fraction(data)
        if value.denominator == 1:
            raise OmkJsonError(f"{data!r} is a whole number; write {value.numerator}.")
        if f"{value.numerator}/{value.denominator}" != data:
            raise OmkJsonError(
                f"{data!r} is not a rational in lowest terms; "
                f"write '{value.numerator}/{value.denominator}'."
            )
        return value
    raise OmkJsonError(f"{data!r} is not a rational (an integer, or a string 'n/d').")


def decode_integer(data: Any) -> int:
    """A JSON integer. (A boolean is not one, although Python's bool is an int.)

    Raises
    ------
    OmkJsonError
        for anything else.
    """
    if type(data) is not int:
        raise OmkJsonError(f"{data!r} is not an integer.")
    return data


def decode_string(data: Any) -> str:
    """A JSON string.

    Raises
    ------
    OmkJsonError
        for anything else.
    """
    if type(data) is not str:
        raise OmkJsonError(f"{data!r} is not a string.")
    return data


def decode_boolean(data: Any) -> bool:
    """A JSON boolean.

    Raises
    ------
    OmkJsonError
        for anything else.
    """
    if type(data) is not bool:
        raise OmkJsonError(f"{data!r} is not a boolean.")
    return data


def encode_uuid(value: UUID) -> str:
    """A UUID in the hyphenated, lowercase form.

    >>> encode_uuid(UUID("5D1E7A40-3C2B-4F6E-9A8D-0B1C2D3E4F50"))
    '5d1e7a40-3c2b-4f6e-9a8d-0b1c2d3e4f50'
    """
    return str(value)


def decode_uuid(data: Any) -> UUID:
    """A UUID from its hyphenated, lowercase form; any version.

    Raises
    ------
    OmkJsonError
        for anything else (uppercase, braces, no hyphens).
    """
    if type(data) is not str or not _UUID.fullmatch(data):
        raise OmkJsonError(f"{data!r} is not a UUID in lowercase hyphenated form.")
    return UUID(data)


def encode_enum(member: Enum) -> str:
    """An enumeration value: the member's name in lowercase (§4.5),
    whatever the member's own value is.

    >>> from openmusickit.systems.wsmn.percussion.percussion_tone import Stroke
    >>> Stroke.RIM_SHOT.value, encode_enum(Stroke.RIM_SHOT)
    ('rim shot', 'rim_shot')
    """
    return member.name.lower()


def decode_enum[E: Enum](enum: type[E], data: Any) -> E:
    """The member of `enum` whose lowercase name is `data`.

    Raises
    ------
    OmkJsonError
        for a string that names no member (including a member's own value,
        where that differs from its name), or for anything that is not a string.
    """
    if type(data) is str and data == data.lower():
        member = enum.__members__.get(data.upper())
        if member is not None and member.name.lower() == data:
            return member
    names = ", ".join(repr(member.name.lower()) for member in enum)
    raise OmkJsonError(f"{data!r} is not one of {names}.")
