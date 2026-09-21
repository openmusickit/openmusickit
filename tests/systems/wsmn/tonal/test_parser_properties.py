"""The parsers as a fuzz target: any string either parses or raises
`ValueError`, never anything else, and whatever parses re-renders and parses
back to the same value. Known-valid spellings survive random case and
whitespace.

Run with `uv run pytest --hypothesis-profile=thorough` for 2,000 examples per
property.
"""

from hypothesis import given
from hypothesis import strategies as st

from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from tests.strategies import interval_spellings, pitch_spellings, tonal_vectors


@given(st.text(max_size=12))
def test_from_string_only_ever_raises_value_error(s):
    try:
        v = TonalVector.from_string(s)
    except ValueError:
        return
    assert isinstance(v, TonalVector)
    assert TonalVector.from_string(v.pitch.unicode) == v
    assert TonalVector.from_string(v.pitch.ascii) == v
    assert TonalVector.from_string(v.interval.abbr) == v


@given(st.text(max_size=12))
def test_from_ly_only_ever_raises_value_error(s):
    try:
        v = TonalVector.from_ly(s)
    except ValueError:
        return
    assert isinstance(v, TonalVector) and v.has_octave
    assert TonalVector.from_ly(v.pitch.ly_absolute) == v


@given(st.text(max_size=8), tonal_vectors(qualified=True))
def test_from_ly_relative_only_ever_raises_value_error(s, prev):
    try:
        v = TonalVector.from_ly(s, prev_note=prev)
    except ValueError:
        return
    assert v.has_octave
    assert TonalVector.from_ly(v.pitch.ly_relative(prev), prev_note=prev) == v


@given(pitch_spellings())
def test_pitch_spellings_parse_whatever_the_case_and_whitespace(spelling):
    text, expected = spelling
    assert TonalVector.from_string(text) == expected


@given(interval_spellings())
def test_interval_spellings_parse_whatever_the_case_and_whitespace(spelling):
    text, expected = spelling
    assert TonalVector.from_string(text) == expected


@given(tonal_vectors())
def test_every_string_form_of_a_vector_parses_back(v):
    for form in (v.pitch.unicode, v.pitch.ascii, v.pitch.verbose, v.interval.abbr):
        assert TonalVector.from_string(form) == v, form
    if v.has_octave:
        assert TonalVector.from_ly(v.pitch.ly_absolute) == v
    else:
        assert TonalVector.from_string(v.interval.unicode) == v
        assert TonalVector.from_ly(v.pitch.ly) == v.qualify_octave(0)
