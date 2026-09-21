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
from tests.domains import ABSTRACT_VECTORS, ALL_VECTORS, QUALIFIED_VECTORS

# --- pitch.unicode / pitch.ascii / pitch.verbose round-trip through from_string ---
# The display properties and from_string both default to middle C == C4;
# the *_at(mid_c) forms round-trip when from_string is given the same mid_c.


@pytest.mark.parametrize("tv", ALL_VECTORS)
def test_unicode_roundtrip(tv):
    assert TonalVector.from_string(tv.pitch.unicode) == tv


@pytest.mark.parametrize("tv", ALL_VECTORS)
def test_ascii_roundtrip(tv):
    assert TonalVector.from_string(tv.pitch.ascii) == tv


@pytest.mark.parametrize("tv", ALL_VECTORS)
def test_verbose_roundtrip(tv):
    assert TonalVector.from_string(tv.pitch.verbose) == tv


@pytest.mark.parametrize("mid_c", [0, 3])
@pytest.mark.parametrize("tv", ALL_VECTORS)
def test_custom_mid_c_roundtrip(tv, mid_c):
    assert TonalVector.from_string(tv.pitch.unicode_at(mid_c), mid_c=mid_c) == tv
    assert TonalVector.from_string(tv.pitch.ascii_at(mid_c), mid_c=mid_c) == tv
    assert TonalVector.from_string(tv.pitch.verbose_at(mid_c), mid_c=mid_c) == tv


# --- interval.unicode round-trip through from_string ---
# interval.unicode ("major 3", "augmented 4") does not encode an octave at
# all (compound/octave-qualified intervals print the same as their
# unqualified equivalent), so it only round-trips for abstract vectors.


@pytest.mark.parametrize("tv", ABSTRACT_VECTORS)
def test_interval_unicode_roundtrip(tv):
    assert TonalVector.from_string(tv.interval.unicode) == tv


# --- interval.abbr round-trip through from_string ---
# interval.abbr ("maj3", "aug4+1", "per1-2") does encode an octave, as a
# "+N"/"-N" suffix, so it round-trips for both abstract and
# octave-qualified vectors.


@pytest.mark.parametrize("tv", ALL_VECTORS)
def test_interval_abbr_roundtrip(tv):
    assert TonalVector.from_string(tv.interval.abbr) == tv


# --- pitch.ly round-trip through from_ly ---
# pitch.ly never includes an octave designation, so from_ly always returns
# an octave-qualified vector at octave 0. Abstract vectors therefore do NOT
# round-trip to themselves via ly/from_ly -- this is an accepted, documented
# asymmetry (see module docstring).


@pytest.mark.parametrize("tv", ABSTRACT_VECTORS)
def test_ly_roundtrip_abstract_qualifies_at_octave_zero(tv):
    """Known asymmetry: from_ly(tv.pitch.ly) qualifies the octave rather
    than reproducing the original abstract vector."""
    assert TonalVector.from_ly(tv.pitch.ly) == tv.qualify_octave(0)


# --- pitch.ly_absolute round-trip through from_ly ---
# ly_absolute does encode an absolute octave (via ' and , marks), so
# octave-qualified vectors round-trip exactly.


@pytest.mark.parametrize("tv", QUALIFIED_VECTORS)
def test_ly_absolute_roundtrip(tv):
    assert TonalVector.from_ly(tv.pitch.ly_absolute) == tv


# --- pitch.ly_relative round-trip through from_ly, using prev_note ---


@pytest.mark.parametrize("tv", QUALIFIED_VECTORS)
def test_ly_relative_roundtrip(tv):
    prev_note = TonalVector((0, 0, 0))
    ly_str = tv.pitch.ly_relative(prev_note)
    assert TonalVector.from_ly(ly_str, prev_note=prev_note) == tv
