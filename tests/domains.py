"""Finite domains the exhaustive tests sweep, as plain module-level lists.

These are the values a law is checked against *in full*: every pitch class,
every octave-qualified pitch in a five-octave band, and every `TonalVector`
built from them. Fixtures in `conftest.py` hand the same lists to tests that
want them injected; tests that parametrize import them from here directly.

`distinct` is for the `*_symbols` fixtures, whose modules bind several names
to one object (`quarter is crotchet`): it keeps one name per object so a law
is checked once per value rather than once per spelling.
"""

from collections.abc import Mapping

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
