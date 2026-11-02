"""The primitive types of the format specification (§4): rationals, UUIDs,
enumerations, and the plain JSON types, each read strictly."""

from enum import Enum, IntEnum, StrEnum
from fractions import Fraction

import pytest
from hypothesis import given
from hypothesis import strategies as st

from openmusickit.errors import OmkJsonError
from openmusickit.graph.edge import EdgeOrigin, EdgeType, TimingAnchor
from openmusickit.io.omk_json.primitives import (
    decode_boolean,
    decode_enum,
    decode_integer,
    decode_rational,
    decode_string,
    decode_uuid,
    encode_enum,
    encode_rational,
    encode_uuid,
)
from openmusickit.systems.wsmn.percussion.percussion_tone import RelativePitch, Stroke
from openmusickit.systems.wsmn.scoring.bar_line_shape import BarLineComponent
from openmusickit.systems.wsmn.scoring.bracket_shape import BracketSymbol, GroupBarLines
from openmusickit.systems.wsmn.scoring.staff_clef import ClefSign
from openmusickit.systems.wsmn.tonal.chords import ChordQuality
from openmusickit.values.scoring.mark import AttachmentMode, MarkType
from openmusickit.values.text.word import LexicalStress

# --- rationals -----------------------------------------------------------------------------


@given(st.fractions())
def test_a_rational_reads_back_as_the_same_number(value):
    data = encode_rational(value)
    assert decode_rational(data) == value
    assert encode_rational(decode_rational(data)) == data


@given(st.integers())
def test_a_whole_number_is_written_as_an_integer_however_it_is_held(n):
    assert encode_rational(n) == n
    assert encode_rational(Fraction(n)) == n
    assert type(decode_rational(n)) is int


@pytest.mark.parametrize(
    "value, data", [(Fraction(1, 2), "1/2"), (Fraction(-7, 3), "-7/3"), (Fraction(6, 4), "3/2")]
)
def test_a_fraction_is_written_n_over_d_in_lowest_terms(value, data):
    assert encode_rational(value) == data


@pytest.mark.parametrize("value", [1.5, 2.0, True, "1/2", None], ids=repr)
def test_only_ints_and_fractions_are_written_as_rationals(value):
    with pytest.raises(TypeError):
        encode_rational(value)


@pytest.mark.parametrize(
    "data",
    [
        "2/4",  # not in lowest terms
        "4/2",
        "3/1",  # a whole number is an integer
        "1/1",
        "-0/1",
        "0/1",
        "1/-2",  # the sign is on the numerator
        "-1/-2",
        "+1/2",
        "01/2",  # no leading zeros
        "1/02",
        " 1/2",
        "1 / 2",
        "1/0",
        "1.5",
        "1",
        1.5,  # never a float
        2.0,
        True,  # a boolean is not an integer
        None,
        [1, 2],
    ],
    ids=repr,
)
def test_a_rational_in_any_other_form_is_refused(data):
    with pytest.raises(OmkJsonError):
        decode_rational(data)


# --- plain types ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "decode, good, bad",
    [
        (decode_integer, [0, -3, 2**70], [True, 1.0, "1", None]),
        (decode_string, ["", "a", "é"], [1, None, ["a"]]),
        (decode_boolean, [True, False], [0, 1, "true", None]),
    ],
)
def test_plain_types_are_read_strictly(decode, good, bad):
    for data in good:
        assert decode(data) == data
    for data in bad:
        with pytest.raises(OmkJsonError):
            decode(data)


# --- UUIDs ---------------------------------------------------------------------------------


@given(st.uuids())
def test_a_uuid_of_any_version_reads_back(value):
    assert decode_uuid(encode_uuid(value)) == value


@pytest.mark.parametrize(
    "data",
    [
        "5D1E7A40-3C2B-4F6E-9A8D-0B1C2D3E4F50",
        "{5d1e7a40-3c2b-4f6e-9a8d-0b1c2d3e4f50}",
        "5d1e7a403c2b4f6e9a8d0b1c2d3e4f50",
        "urn:uuid:5d1e7a40-3c2b-4f6e-9a8d-0b1c2d3e4f50",
        "5d1e7a40-3c2b-4f6e-9a8d-0b1c2d3e4f5",
        None,
        42,
    ],
)
def test_a_uuid_in_any_other_form_is_refused(data):
    with pytest.raises(OmkJsonError):
        decode_uuid(data)


# --- enumerations --------------------------------------------------------------------------

ENUMERATIONS = [
    EdgeType,
    EdgeOrigin,
    TimingAnchor,
    MarkType,
    AttachmentMode,
    LexicalStress,
    ChordQuality,
    ClefSign,
    BarLineComponent,
    BracketSymbol,
    GroupBarLines,
    Stroke,
    RelativePitch,
]


@pytest.mark.parametrize("enum", ENUMERATIONS, ids=lambda e: e.__name__)
def test_every_member_is_written_as_its_lowercase_name_and_read_back(enum):
    for member in enum:
        data = encode_enum(member)
        assert data == member.name.lower()
        assert data.isidentifier() and data == data.lower()
        assert decode_enum(enum, data) is member


def test_a_display_value_that_differs_from_the_name_is_refused():
    assert Stroke.RIM_SHOT.value == "rim shot" and str(RelativePitch.LOW_MID) == "low-mid"
    for enum, data in [(Stroke, "rim shot"), (RelativePitch, "low-mid"), (RelativePitch, 2)]:
        with pytest.raises(OmkJsonError):
            decode_enum(enum, data)


@pytest.mark.parametrize("data", ["NEXT", "Next", "nexts", "", None, 1])
def test_an_enumeration_value_in_any_other_form_is_refused(data):
    with pytest.raises(OmkJsonError, match="is not one of"):
        decode_enum(EdgeType, data)


def test_an_alias_name_is_refused_in_favour_of_the_member_name():
    class Colour(Enum):
        RED = 1
        CRIMSON = 1  # an alias of RED

    assert decode_enum(Colour, "red") is Colour.RED
    with pytest.raises(OmkJsonError):
        decode_enum(Colour, "crimson")
    assert encode_enum(Colour.CRIMSON) == "red"


def test_enumerations_of_any_base_are_named_alike():
    class Size(IntEnum):
        SMALL = 1

    class Shade(StrEnum):
        DARK_GREY = "dark grey"

    assert encode_enum(Size.SMALL) == "small"
    assert encode_enum(Shade.DARK_GREY) == "dark_grey"
