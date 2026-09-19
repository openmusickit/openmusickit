"""Round-trip symmetry tests between TonalVector's string-producing
properties (pitch.*, interval.*) and its string-parsing classmethods
(from_string, from_ly).

For a TonalVector tv and a to_string transform f, we expect:

    TonalVector.from_string(f(tv)) == tv   (or from_ly, for Lilypond forms)

with one known, accepted exception: Lilypond has no notion of an abstract
(octave-less) pitch, so from_ly always returns an octave-qualified
TonalVector, even when parsing the ly-string of an abstract TonalVector.
That specific asymmetry is documented and tested for explicitly below,
rather than silently ignored.
"""

import pytest

from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector


def _abstract_tuples():
    """All 35 abstract (d, c) pitch classes: naturals, single/double
    sharps and flats."""
    MS = [(0, 0), (1, 2), (2, 4), (3, 5), (4, 7), (5, 9), (6, 11)]
    return [(d, (c + m) % 12) for m in [0, 1, 2, -1, -2] for d, c in MS]


def _octave_qualified_tuples():
    """All abstract tuples, qualified at several octaves."""
    return [(d, c, o) for o in [0, 1, -1, 2, -2] for d, c in _abstract_tuples()]


ABSTRACT_VECTORS = [TonalVector(t) for t in _abstract_tuples()]
QUALIFIED_VECTORS = [TonalVector(t) for t in _octave_qualified_tuples()]
ALL_VECTORS = ABSTRACT_VECTORS + QUALIFIED_VECTORS


### pitch.unicode / pitch.ascii round-trip through from_string ###
# These properties default to mid_c=0 (i.e. their own octave numbers align
# with from_string's default mid_c=4 only if we pass a matching mid_c).
# unicode/ascii render octave numbers with middle C == 0, so round-tripping
# through from_string requires mid_c=0.


@pytest.mark.parametrize("tv", ALL_VECTORS)
def test_unicode_roundtrip(tv):
    assert TonalVector.from_string(tv.pitch.unicode, mid_c=0) == tv


@pytest.mark.parametrize("tv", ALL_VECTORS)
def test_ascii_roundtrip(tv):
    assert TonalVector.from_string(tv.pitch.ascii, mid_c=0) == tv


### pitch.unicode_C4 / pitch.ascii_C4 round-trip through from_string ###
# These render octave numbers with middle C == 4, matching from_string's
# default mid_c=4.


@pytest.mark.parametrize("tv", ALL_VECTORS)
def test_unicode_c4_roundtrip(tv):
    assert TonalVector.from_string(tv.pitch.unicode_C4) == tv


@pytest.mark.parametrize("tv", ALL_VECTORS)
def test_ascii_c4_roundtrip(tv):
    assert TonalVector.from_string(tv.pitch.ascii_C4) == tv


### pitch.verbose round-trip through from_string ###
# verbose renders the raw internal octave number with no mid_c offset at
# all, so it round-trips with mid_c=0.


@pytest.mark.parametrize("tv", ALL_VECTORS)
def test_verbose_roundtrip(tv):
    assert TonalVector.from_string(tv.pitch.verbose, mid_c=0) == tv


### interval.unicode round-trip through from_string ###
# interval.unicode ("major 3", "augmented 4") does not encode an octave at
# all (compound/octave-qualified intervals print the same as their
# unqualified equivalent), so it only round-trips for abstract vectors.


@pytest.mark.parametrize("tv", ABSTRACT_VECTORS)
def test_interval_unicode_roundtrip(tv):
    assert TonalVector.from_string(tv.interval.unicode) == tv


### interval.abbr round-trip through from_string ###
# interval.abbr ("maj3", "aug4+1", "per1-2") does encode an octave, as a
# "+N"/"-N" suffix, so it round-trips for both abstract and
# octave-qualified vectors.


@pytest.mark.parametrize("tv", ALL_VECTORS)
def test_interval_abbr_roundtrip(tv):
    assert TonalVector.from_string(tv.interval.abbr) == tv


### pitch.ly round-trip through from_ly ###
# pitch.ly never includes an octave designation, so from_ly always returns
# an octave-qualified vector at octave 0. Abstract vectors therefore do NOT
# round-trip to themselves via ly/from_ly -- this is an accepted, documented
# asymmetry (see module docstring).


@pytest.mark.parametrize("tv", ABSTRACT_VECTORS)
def test_ly_roundtrip_abstract_qualifies_at_octave_zero(tv):
    """Known asymmetry: from_ly(tv.pitch.ly) qualifies the octave rather
    than reproducing the original abstract vector."""
    assert TonalVector.from_ly(tv.pitch.ly) == tv.qualify_octave(0)


### pitch.ly_abs8ve round-trip through from_ly ###
# ly_abs8ve does encode an absolute octave (via ' and , marks), so
# octave-qualified vectors round-trip exactly.


@pytest.mark.parametrize("tv", QUALIFIED_VECTORS)
def test_ly_abs8ve_roundtrip(tv):
    assert TonalVector.from_ly(tv.pitch.ly_abs8ve) == tv


### pitch.ly_rel8ve round-trip through from_ly, using prev_note ###


@pytest.mark.parametrize("tv", QUALIFIED_VECTORS)
def test_ly_rel8ve_roundtrip(tv):
    prev_note = TonalVector((0, 0, 0))
    ly_str = tv.pitch.ly_rel8ve(prev_note)
    assert TonalVector.from_ly(ly_str, prev_note=prev_note) == tv
