"""The `wsmn` vocabulary (`docs/spec/vocabulary-wsmn.qmd`):
the pitch, duration, chord, key, clef, bar line and percussion types
of Western Standard Music Notation.

>>> from openmusickit.io.omk_json.core import CORE
>>> from openmusickit.io.omk_json.vocabulary import Encoder
>>> from openmusickit.systems.wsmn.temporal.symbols import dotted_quarter
>>> Encoder([CORE, WSMN]).value(dotted_quarter)
{'numerator': 1, 'denominator': 4, 'dots': 1, 'ratio': None, '@type': 'wsmn:MetricalDuration'}
"""

from __future__ import annotations

from typing import Any

from openmusickit.io.omk_json.core import (
    CLEF,
    DIVISION_SHAPE,
    DURATION,
    EXACT_TONE_COLLECTION,
    INTERVAL,
    MEASURABLE,
    MODAL_CONTEXT,
    STACK_GROUP_SHAPE,
    TEMPORAL_RATIO,
    TONE,
    TONE_COLLECTION,
)
from openmusickit.io.omk_json.primitives import (
    decode_enum,
    decode_integer,
    decode_rational,
    decode_string,
    encode_enum,
    encode_rational,
)
from openmusickit.io.omk_json.vocabulary import Decoder, Encoder, TypeCodec, Vocabulary
from openmusickit.systems.wsmn.percussion.percussion_tone import (
    PercussionTone,
    RelativePitch,
    Stroke,
)
from openmusickit.systems.wsmn.percussion.wsmn import WSMN_PERCUSSION
from openmusickit.systems.wsmn.scoring.bar_line_shape import BarLineComponent, BarLineShape
from openmusickit.systems.wsmn.scoring.bracket_shape import (
    BracketShape,
    BracketSymbol,
    GroupBarLines,
)
from openmusickit.systems.wsmn.scoring.staff_clef import ClefSign, StaffClef
from openmusickit.systems.wsmn.temporal.metrical_duration import MetricalDuration, TiedDuration
from openmusickit.systems.wsmn.temporal.time_signature import TimeSignature
from openmusickit.systems.wsmn.temporal.wsmn import WSMN_TEMPORAL
from openmusickit.systems.wsmn.tonal.chords import Chord, ChordQuality, ChordType
from openmusickit.systems.wsmn.tonal.key import Key, KeySignature, ModePattern
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from openmusickit.systems.wsmn.tonal.wsmn import WSMN as WSMN_TONAL

# Fields typed by one exact type of this vocabulary.
TONAL_VECTOR = "wsmn:TonalVector"
KEY_SIGNATURE = "wsmn:KeySignature"
MODE_PATTERN = "wsmn:ModePattern"

LETTERS = ("c", "d", "e", "f", "g", "a", "b")
ROOT = TonalVector((0, 0))


def _optional_enum(member: Any) -> str | None:
    return None if member is None else encode_enum(member)


def _optional_decode_enum(enum: type, data: Any) -> Any:
    return None if data is None else decode_enum(enum, data)


def _optional_string(data: Any) -> str | None:
    return None if data is None else decode_string(data)


# --- pitch -----------------------------------------------------------------------------------


def _check_tonal_vector(diatonic: Any, chromatic: Any) -> None:
    if not 0 <= diatonic <= 6 or not 0 <= chromatic <= 11:
        raise ValueError(
            f"A TonalVector's diatonic is 0 to 6 and its chromatic 0 to 11, not ({diatonic}, {chromatic})."
        )


def _encode_tonal_vector(vector: TonalVector, e: Encoder) -> dict[str, Any]:
    if len(vector) not in (2, 3) or any(type(coordinate) is not int for coordinate in vector):
        raise ValueError(f"A TonalVector has two or three integer coordinates, not {vector!r}.")
    _check_tonal_vector(vector[0], vector[1])
    return {
        "diatonic": vector[0],
        "chromatic": vector[1],
        "octave": vector[2] if len(vector) == 3 else None,
    }


def _decode_tonal_vector(f: dict[str, Any], d: Decoder) -> TonalVector:
    diatonic, chromatic = decode_integer(f["diatonic"]), decode_integer(f["chromatic"])
    _check_tonal_vector(diatonic, chromatic)
    if f["octave"] is None:
        return TonalVector((diatonic, chromatic))
    return TonalVector((diatonic, chromatic, decode_integer(f["octave"])))


# --- durations -------------------------------------------------------------------------------


def _encode_metrical_duration(duration: MetricalDuration, e: Encoder) -> dict[str, Any]:
    return {
        "numerator": duration.numerator,
        "denominator": duration.denominator,
        "dots": duration.dots,
        "ratio": e.optional(duration.ratio),
    }


def _decode_metrical_duration(f: dict[str, Any], d: Decoder) -> MetricalDuration:
    written = (
        decode_integer(f["numerator"]),
        decode_integer(f["denominator"]),
        decode_integer(f["dots"]),
    )
    duration = MetricalDuration(*written, ratio=d.optional(f["ratio"], TEMPORAL_RATIO))
    normal = (duration.numerator, duration.denominator, duration.dots)
    if normal != written:
        # The model normalises (2/4 to 1/2, 3/8 to a dotted 1/4); the format admits only the normal form.
        raise ValueError(
            f"A MetricalDuration is written in its normal form: "
            f"{normal[0]}/{normal[1]} with {normal[2]} dots, not {written[0]}/{written[1]} with {written[2]} dots."
        )
    return duration


def _encode_tied_duration(duration: TiedDuration, e: Encoder) -> dict[str, Any]:
    return {"members": e.array(duration.members)}


def _decode_tied_duration(f: dict[str, Any], d: Decoder) -> TiedDuration:
    return TiedDuration(d.array(f["members"], DURATION))


def _encode_time_signature(signature: TimeSignature, e: Encoder) -> dict[str, Any]:
    presentation = signature.presentation
    return {
        "units": e.array(signature.units),
        "presentation": None if presentation is None else list(presentation),
    }


def _decode_time_signature(f: dict[str, Any], d: Decoder) -> TimeSignature:
    presentation = f["presentation"]
    if presentation is not None:
        if type(presentation) is not list or len(presentation) != 2:
            raise ValueError(f"A presentation is two strings, not {presentation!r}.")
        presentation = tuple(decode_string(part) for part in presentation)
    return TimeSignature(d.array(f["units"], MEASURABLE), presentation=presentation)


# --- chords ----------------------------------------------------------------------------------


def _encode_chord_type(chord_type: ChordType, e: Encoder) -> dict[str, Any]:
    return {
        "tones": e.array(chord_type.tones),
        "root": e.value(chord_type.root),
        "name": e.template(chord_type.name_template, chord_type.root),
        "bass": e.value(chord_type.bass),
        "quality": _optional_enum(chord_type.quality),
        "suffix": chord_type.suffix,
    }


def _decode_chord_type(f: dict[str, Any], d: Decoder) -> ChordType:
    root = d.value(f["root"], TONAL_VECTOR)
    if len(root) != 2 or root != ROOT:
        raise ValueError(f"A ChordType's root is (0, 0) with no octave, not {root!r}.")
    if f["name"] is None:
        raise ValueError("A ChordType has a name.")
    return ChordType(
        d.array(f["tones"], TONAL_VECTOR),
        d.template(f["name"], root),
        bass=d.value(f["bass"], TONAL_VECTOR),
        quality=_optional_decode_enum(ChordQuality, f["quality"]),
        suffix=_optional_string(f["suffix"]),
    )


def _encode_chord(chord: Chord, e: Encoder) -> dict[str, Any]:
    return {
        "root": e.value(chord.root),
        "tones": e.array(chord.tones),
        "bass": e.value(chord.bass),
        "name": e.template(chord.name_template, chord.root),
        "suffix": chord.suffix,
    }


def _decode_chord(f: dict[str, Any], d: Decoder) -> Chord:
    root = d.value(f["root"], TONAL_VECTOR)
    return Chord(
        root,
        d.array(f["tones"], TONAL_VECTOR),
        bass=d.value(f["bass"], TONAL_VECTOR),
        name=d.template(f["name"], root),
        suffix=_optional_string(f["suffix"]),
    )


# --- keys ------------------------------------------------------------------------------------


def _encode_key_signature(signature: KeySignature, e: Encoder) -> dict[str, Any]:
    return {
        letter: encode_rational(value) for letter, value in zip(LETTERS, signature, strict=True)
    }


def _decode_key_signature(f: dict[str, Any], d: Decoder) -> KeySignature:
    return KeySignature(**{letter: decode_rational(f[letter]) for letter in LETTERS})


def _encode_mode_pattern(mode: ModePattern, e: Encoder) -> dict[str, Any]:
    return {
        "name": mode.name,
        "tones": e.value(mode.tones),
        "quality": _optional_enum(mode.quality),
    }


def _decode_mode_pattern(f: dict[str, Any], d: Decoder) -> ModePattern:
    return ModePattern(
        name=decode_string(f["name"]),
        tones=d.value(f["tones"], EXACT_TONE_COLLECTION),
        quality=_optional_decode_enum(ChordQuality, f["quality"]),
    )


def _encode_key(key: Key, e: Encoder) -> dict[str, Any]:
    return {
        "tonic": e.optional(key.tonic),
        "signature": e.optional(key.signature),
        "tones": e.value(key.tones),
        "mode": e.optional(key.mode),
        "name": key.name,
    }


def _decode_key(f: dict[str, Any], d: Decoder) -> Key:
    return Key(
        tonic=d.optional(f["tonic"], TONAL_VECTOR),
        signature=d.optional(f["signature"], KEY_SIGNATURE),
        tones=d.value(f["tones"], EXACT_TONE_COLLECTION),
        mode=d.optional(f["mode"], MODE_PATTERN),
        # Always written: the model names a key itself when given none, so null could not be read back.
        name=decode_string(f["name"]),
    )


# --- clefs, bar lines, brackets, percussion --------------------------------------------------


def _encode_staff_clef(clef: StaffClef, e: Encoder) -> dict[str, Any]:
    return {"sign": encode_enum(clef.sign), "line": clef.line, "octave_change": clef.octave_change}


def _decode_staff_clef(f: dict[str, Any], d: Decoder) -> StaffClef:
    return StaffClef(
        decode_enum(ClefSign, f["sign"]),
        None if f["line"] is None else decode_integer(f["line"]),
        octave_change=decode_integer(f["octave_change"]),
    )


def _encode_bar_line_shape(shape: BarLineShape, e: Encoder) -> dict[str, Any]:
    return {"components": [encode_enum(component) for component in shape.components]}


def _decode_bar_line_shape(f: dict[str, Any], d: Decoder) -> BarLineShape:
    components = f["components"]
    if type(components) is not list:
        raise ValueError(f"Expected an array of bar line components, found {components!r}.")
    return BarLineShape(*(decode_enum(BarLineComponent, component) for component in components))


def _encode_bracket_shape(shape: BracketShape, e: Encoder) -> dict[str, Any]:
    return {"symbol": _optional_enum(shape.symbol), "bar_lines": encode_enum(shape.bar_lines)}


def _decode_bracket_shape(f: dict[str, Any], d: Decoder) -> BracketShape:
    return BracketShape(
        symbol=_optional_decode_enum(BracketSymbol, f["symbol"]),
        bar_lines=decode_enum(GroupBarLines, f["bar_lines"]),
    )


def _encode_percussion_tone(tone: PercussionTone, e: Encoder) -> dict[str, Any]:
    return {
        "relative_pitch": _optional_enum(tone.relative_pitch),
        "stroke": _optional_enum(tone.stroke),
    }


def _decode_percussion_tone(f: dict[str, Any], d: Decoder) -> PercussionTone:
    return PercussionTone(
        relative_pitch=_optional_decode_enum(RelativePitch, f["relative_pitch"]),
        stroke=_optional_decode_enum(Stroke, f["stroke"]),
    )


def _value(name, cls, fields, encode, decode, kinds=(), display_forms=()) -> TypeCodec:
    return TypeCodec(
        name, cls, "value", fields, encode, decode, frozenset(kinds), frozenset(display_forms)
    )


WSMN = Vocabulary(
    prefix="wsmn",
    uri="https://openmusickit.org/spec/wsmn",
    version="0.1",
    codecs=(
        _value(
            "TonalVector",
            TonalVector,
            ("diatonic", "chromatic", "octave"),
            _encode_tonal_vector,
            _decode_tonal_vector,
            (TONE, INTERVAL, TONAL_VECTOR),
            ("unicode", "ascii", "letter", "verbose", "ly", "ly_absolute"),
        ),
        _value(
            "MetricalDuration",
            MetricalDuration,
            ("numerator", "denominator", "dots", "ratio"),
            _encode_metrical_duration,
            _decode_metrical_duration,
            (DURATION, MEASURABLE),
        ),
        _value(
            "TiedDuration",
            TiedDuration,
            ("members",),
            _encode_tied_duration,
            _decode_tied_duration,
            (DURATION, MEASURABLE),
        ),
        _value(
            "TimeSignature",
            TimeSignature,
            ("units", "presentation"),
            _encode_time_signature,
            _decode_time_signature,
            (MEASURABLE,),
        ),
        _value(
            "ChordType",
            ChordType,
            ("tones", "root", "name", "bass", "quality", "suffix"),
            _encode_chord_type,
            _decode_chord_type,
            (TONE_COLLECTION,),
        ),
        _value(
            "Chord",
            Chord,
            ("root", "tones", "bass", "name", "suffix"),
            _encode_chord,
            _decode_chord,
            (TONE_COLLECTION,),
        ),
        _value(
            "KeySignature",
            KeySignature,
            LETTERS,
            _encode_key_signature,
            _decode_key_signature,
            (KEY_SIGNATURE,),
        ),
        _value(
            "ModePattern",
            ModePattern,
            ("name", "tones", "quality"),
            _encode_mode_pattern,
            _decode_mode_pattern,
            (MODE_PATTERN,),
        ),
        _value(
            "Key",
            Key,
            ("tonic", "signature", "tones", "mode", "name"),
            _encode_key,
            _decode_key,
            (MODAL_CONTEXT,),
        ),
        _value(
            "StaffClef",
            StaffClef,
            ("sign", "line", "octave_change"),
            _encode_staff_clef,
            _decode_staff_clef,
            (CLEF,),
        ),
        _value(
            "BarLineShape",
            BarLineShape,
            ("components",),
            _encode_bar_line_shape,
            _decode_bar_line_shape,
            (DIVISION_SHAPE,),
        ),
        _value(
            "BracketShape",
            BracketShape,
            ("symbol", "bar_lines"),
            _encode_bracket_shape,
            _decode_bracket_shape,
            (STACK_GROUP_SHAPE,),
        ),
        _value(
            "PercussionTone",
            PercussionTone,
            ("relative_pitch", "stroke"),
            _encode_percussion_tone,
            _decode_percussion_tone,
            (TONE,),
        ),
    ),
    temporal_systems={"metrical": WSMN_TEMPORAL},
    tonal_systems={"tonal": WSMN_TONAL, "percussion": WSMN_PERCUSSION},
)
