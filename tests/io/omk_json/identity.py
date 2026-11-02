"""Structural identity: the comparison a round trip must pass.

`==` is too weak for a round trip: a Measurable compares by length (4/4 equals
2/2, a triplet ratio a sextuplet one), a ToneCollection ignores its name, and
an OmkObject ignores its id and meta. `identical` compares the exact type and
every stored field, `compare=False` ones included. It treats as identical only
what the format deliberately does not carry (`docs/spec/omk-json.qmd` §12):
an int and the whole-number Fraction equal to it, and shared versus copied values.
"""

from __future__ import annotations

import dataclasses
from enum import Enum
from fractions import Fraction
from typing import Any

from openmusickit.graph.edge import OmkEdge
from openmusickit.objects.omk_object import OmkObject


def identical(a: Any, b: Any) -> bool:
    """Whether `a` and `b` are the same value, field by field.
    Ids and meta of nodes and edges are not compared here; a round trip checks them itself."""
    return not differences(a, b)


def differences(a: Any, b: Any, path: str = "") -> list[str]:
    """Where `a` and `b` differ, as paths (`.tones[0]`), for a readable assertion message."""
    if _number(a) and _number(b):  # 2 and Fraction(2) are one number
        return [] if a == b else [f"{path}: {a!r} != {b!r}"]
    if type(a) is not type(b):
        return [f"{path}: {type(a).__name__} != {type(b).__name__}"]
    if isinstance(a, Enum) or a is None or isinstance(a, str | bool | float):
        return [] if a == b else [f"{path}: {a!r} != {b!r}"]
    if isinstance(a, set | frozenset):
        return _set_differences(a, b, path)
    if isinstance(a, list | tuple):  # TonalVector and KeySignature are tuples too
        if len(a) != len(b):
            return [f"{path}: {len(a)} items != {len(b)}"]
        found = [
            d
            for i, (x, y) in enumerate(zip(a, b, strict=True))
            for d in differences(x, y, f"{path}[{i}]")
        ]
        if found or not dataclasses.is_dataclass(a):
            return found
    if isinstance(a, dict):
        if set(a) != set(b):
            return [f"{path}: keys {sorted(a)} != {sorted(b)}"]
        return [d for key in a for d in differences(a[key], b[key], f"{path}[{key!r}]")]
    if dataclasses.is_dataclass(a):
        skip = {"_id", "meta"} if isinstance(a, OmkObject | OmkEdge) else set()
        return [
            d
            for field in dataclasses.fields(a)
            if field.name not in skip
            for d in differences(
                getattr(a, field.name), getattr(b, field.name), f"{path}.{field.name}"
            )
        ]
    state_a, state_b = getattr(a, "__dict__", {}), getattr(b, "__dict__", {})
    if state_a or state_b:
        return differences(state_a, state_b, path)
    return []  # a value with no state (ZeroDuration, SilentTone): the type is all there is


def _number(value: Any) -> bool:
    return type(value) is int or type(value) is Fraction


def _set_differences(a: set | frozenset, b: set | frozenset, path: str) -> list[str]:
    unmatched = list(b)
    for item in a:
        match = next((other for other in unmatched if identical(item, other)), None)
        if match is None:
            return [f"{path}: {item!r} has no counterpart"]
        unmatched.remove(match)
    return [f"{path}: {unmatched!r} left over"] if unmatched else []
