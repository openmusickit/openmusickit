"""Finite domains the exhaustive tests sweep, as plain module-level lists.

These are the values a law is checked against *in full*: every pitch class,
every octave-qualified pitch in a five-octave band, every `TonalVector`
built from them, and every `PercussionTone`. Fixtures in `conftest.py` hand the same lists to tests that
want them injected; tests that parametrize import them from here directly.

`distinct` is for the `*_symbols` fixtures, whose modules bind several names
to one object (`quarter is crotchet`): it keeps one name per object so a law
is checked once per value rather than once per spelling.
"""

from collections.abc import Mapping
from types import ModuleType

from openmusickit.systems.wsmn.percussion.percussion_tone import (
    PercussionTone,
    RelativePitch,
    Stroke,
)
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector

_MAJOR_SCALE = [(0, 0), (1, 2), (2, 4), (3, 5), (4, 7), (5, 9), (6, 11)]

TONAL_TUPLES: list[tuple[int, int]] = [
    (d, (c + m) % 12) for m in [0, 1, 2, -1, -2] for d, c in _MAJOR_SCALE
]
"""All 35 abstract (d, c) pitch classes: naturals, then single and double sharps and flats."""

TONAL_OCT_TUPLES: list[tuple[int, int, int]] = [
    (d, c, o) for o in [0, 1, 2, -1, -2] for d, c in TONAL_TUPLES
]
"""All 175 octave-qualified (d, c, o) tuples: every pitch class at middle C and two octaves either way."""

ABSTRACT_VECTORS: list[TonalVector] = [TonalVector(t) for t in TONAL_TUPLES]
"""The 35 abstract pitch classes as TonalVectors (equally, the 35 simple intervals)."""

QUALIFIED_VECTORS: list[TonalVector] = [TonalVector(t) for t in TONAL_OCT_TUPLES]
"""The 175 octave-qualified TonalVectors."""

ALL_VECTORS: list[TonalVector] = ABSTRACT_VECTORS + QUALIFIED_VECTORS
"""Every TonalVector in the test domain, abstract first."""

TONAL_CLASSES: frozenset[tuple[int, int]] = frozenset(TONAL_TUPLES)
"""The 35 pitch classes as a set, for membership tests on derived values."""

PERCUSSION_TONES: list[PercussionTone] = [
    PercussionTone(relative_pitch=pitch, stroke=stroke)
    for pitch in [None, *RelativePitch]
    for stroke in [None, *Stroke]
]
"""Every PercussionTone: each relative pitch or none, with each stroke or none."""


def in_domain(t: tuple[int, ...]) -> bool:
    """True when the pitch class of a (d, c[, o]) tuple is one of the 35.

    Arithmetic on two domain values can leave the domain: the difference of
    D-sharp and F-double-flat is a third with zero half-steps, a spelling
    beyond any double alteration. Laws about the *size* of such a result
    (`tonal_int`, `abs`) are only asserted where the result is in domain.

    >>> in_domain((1, 3, 0)), in_domain((2, 0, 0))
    (True, False)
    """
    return (t[0], t[1]) in TONAL_CLASSES


def symbols_of[V](module: ModuleType, kind: type[V]) -> dict[str, V]:
    """Every public attribute of `module` whose type is exactly `kind`, by name.

    >>> from openmusickit.systems.wsmn.tonal import symbols
    >>> from openmusickit.systems.wsmn.tonal.key import Key
    >>> list(symbols_of(symbols, Key))
    ['NoKey']
    """
    return {
        name: value
        for name, value in vars(module).items()
        if not name.startswith("_") and type(value) is kind
    }


def distinct[V](symbols: Mapping[str, V]) -> dict[str, V]:
    """One name per object: the first name bound to each distinct object, by identity.

    >>> from openmusickit.systems.wsmn.temporal.symbols import quarter, crotchet, half
    >>> list(distinct({"quarter": quarter, "crotchet": crotchet, "half": half}))
    ['quarter', 'half']
    """
    kept: dict[str, V] = {}
    seen: list[int] = []
    for name, value in symbols.items():
        if id(value) in seen:
            continue
        seen.append(id(value))
        kept[name] = value
    return kept
