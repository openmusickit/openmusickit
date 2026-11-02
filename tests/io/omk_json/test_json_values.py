"""The `omk` and `wsmn` vocabularies' codecs, value by value:
every symbol and every value of a finite domain reads back identical and
writes the same text again; generated values do the same; every stored field
of every class is in its codec (or is named here as deliberately not written);
every concrete class has a codec; and the domains are enforced both ways.
"""

from __future__ import annotations

import dataclasses
import importlib
import inspect
import pkgutil
import sys
from fractions import Fraction
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

import openmusickit
from openmusickit.errors import OmkJsonError, UnexportableError
from openmusickit.graph.edge import Branch, Contains, Next, OmkEdge, Simultaneous, TimedEdge
from openmusickit.io.omk_json import canonical
from openmusickit.io.omk_json.core import CORE
from openmusickit.io.omk_json.vocabulary import Decoder, Encoder, check_template
from openmusickit.io.omk_json.wsmn import WSMN
from openmusickit.objects.context_event import (
    ClefEvent,
    ContextEvent,
    MeterEvent,
    ModalContextEvent,
    TempoEvent,
    TemporalContextEvent,
)
from openmusickit.objects.division_event import DivisionEvent
from openmusickit.objects.omk_object import OmkObject, SequentialEvent, Spanner
from openmusickit.systems.wsmn.percussion.percussion_tone import PercussionTone
from openmusickit.systems.wsmn.temporal.metrical_duration import MetricalDuration, TiedDuration
from openmusickit.systems.wsmn.temporal.symbols import eighth, quarter, triplet
from openmusickit.systems.wsmn.tonal.chords import Chord, ChordType, _ChordBase
from openmusickit.systems.wsmn.tonal.key import Key, KeySignature, ModePattern
from openmusickit.systems.wsmn.tonal.symbols import C, E, G
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from openmusickit.values.scoring.clef import Clef
from openmusickit.values.scoring.division_shape import DivisionShape
from openmusickit.values.scoring.mark import Mark
from openmusickit.values.scoring.stack_group_shape import StackGroupShape
from openmusickit.values.scoring.tempo_term import TempoTerm
from openmusickit.values.text.word import LexicalStress, Word
from openmusickit.values.time.clock_time import ClockDuration, Tempo
from openmusickit.values.time.duration import (
    GraceDuration,
    TemporalElement,
    TemporalRatio,
    TemporalUnit,
)
from openmusickit.values.tone.interval import Interval
from openmusickit.values.tone.modal_context import ModalContext
from openmusickit.values.tone.tone import Tone
from openmusickit.values.tone.tone_collection import ToneCollection
from tests.domains import ALL_VECTORS, PERCUSSION_TONES
from tests.io.omk_json.identity import differences
from tests.strategies import metrical_durations, percussion_tones, tonal_vectors

VOCABULARIES = [CORE, WSMN]
DECLARED = {
    "omk": {"uri": CORE.uri, "version": CORE.version},
    "wsmn": {"uri": WSMN.uri, "version": WSMN.version},
}


def encode(value: Any) -> dict[str, Any]:
    return Encoder(VOCABULARIES).value(value)


def decode(data: Any, kind: str) -> Any:
    return Decoder(VOCABULARIES, DECLARED).value(data, kind)


def assert_round_trip(value: Any) -> None:
    """`value` reads back identical, and writes the same text again."""
    encoder = Encoder(VOCABULARIES)
    data = encoder.value(value)
    kind = sorted(encoder.codec(value)[1].kinds)[0]
    back = decode(data, kind)
    assert not differences(value, back), differences(value, back)
    assert canonical.dumps(encode(back)) == canonical.dumps(data)


# --- every symbol, every finite domain ---------------------------------------------------------

SYMBOL_TABLES = [
    "pitch_symbols",
    "chord_type_symbols",
    "mode_pattern_symbols",
    "key_symbols",
    "duration_symbols",
    "grace_duration_symbols",
    "tuplet_ratio_symbols",
    "time_signature_symbols",
    "mark_symbols",
    "bar_line_symbols",
    "tempo_term_symbols",
    "clef_symbols",
    "percussion_tone_symbols",
    "palette_symbols",
]


@pytest.mark.parametrize("table", SYMBOL_TABLES)
def test_every_symbol_reads_back_identical(table, request):
    for value in request.getfixturevalue(table).values():
        assert_round_trip(value)


def test_every_tonal_vector_and_percussion_tone_reads_back_identical():
    for value in [*ALL_VECTORS, *PERCUSSION_TONES]:
        assert_round_trip(value)


def test_every_chord_type_on_every_pitch_reads_back_identical(pitch_symbols, chord_type_symbols):
    for root in pitch_symbols.values():
        for chord_type in chord_type_symbols.values():
            assert_round_trip(root(chord_type))


def test_the_values_with_no_symbols_read_back_identical():
    for value in [
        ClockDuration(1_500_000),
        ClockDuration(Fraction(-7, 3)),
        Tempo(120, quarter),
        Tempo(66, eighth, ClockDuration(30_000_000)),
        TemporalRatio(quarter, eighth),
        TemporalUnit(3, eighth),
        TiedDuration([quarter, eighth, MetricalDuration(1, 4, ratio=triplet(quarter))]),
        GraceDuration(eighth, on_beat=True),
        KeySignature(f=Fraction(1, 2), b=-3),
        Word(
            ["Hal", "le", "lu", "jah"],
            stress={2: LexicalStress.PRIMARY, 0: LexicalStress.SECONDARY},
        ),
        Mark(name="dolce"),
        TempoTerm(name="Sostenuto", aliases=("sost.",)),
        ToneCollection([C, E, G], root=C, name="{root:ascii} {{triad}}"),
        ToneCollection([C, E], name="a third"),
        Key(tonic=None, signature=KeySignature(e=-1, a=-1, b=-1)),
    ]:
        assert_round_trip(value)


# --- generated values --------------------------------------------------------------------------


@given(metrical_durations())
def test_a_metrical_duration_reads_back_identical(duration):
    assert_round_trip(duration)
    assert_round_trip(-duration)


@given(st.one_of(tonal_vectors(), percussion_tones()))
def test_a_tone_reads_back_identical(tone):
    assert_round_trip(tone)


@given(st.fractions())
def test_a_clock_duration_reads_back_identical(microseconds):
    assert_round_trip(ClockDuration(microseconds))


@given(st.lists(metrical_durations(), min_size=2, max_size=5))
def test_a_tied_duration_reads_back_identical(members):
    assert_round_trip(TiedDuration(members))


# --- every field written, every class coded ------------------------------------------------

# Python fields the format carries under another name (or names).
RENAMED = {
    ToneCollection: {"name_template": "name"},
    Chord: {"name_template": "name"},
    ChordType: {"name_template": "name"},
    Tempo: {"nominal": ("count", "beat"), "contextual": "clock_time"},
    OmkEdge: {"type": "relation"},
}
# Python fields the format deliberately does not write.
NOT_WRITTEN = {
    # always ZeroDuration (the model refuses any other); the spec gives these types no duration
    **dict.fromkeys(
        [ModalContextEvent, MeterEvent, TempoEvent, ClefEvent, DivisionEvent], {"duration"}
    ),
    # the relation is the kind itself; a Contains is always anchored at the onset
    Next: {"type"},
    Branch: {"type"},
    Simultaneous: {"type"},
    Contains: {"type", "anchor"},
}
# Coded types that are not dataclasses: their fields are tested by the sweeps above.
NOT_DATACLASSES = {"TonalVector", "KeySignature", "ZeroDuration"}


def all_codecs():
    return [codec for vocabulary in VOCABULARIES for codec in vocabulary.codecs]


@pytest.mark.parametrize("codec", all_codecs(), ids=lambda codec: codec.name)
def test_every_stored_field_is_written(codec):
    if not dataclasses.is_dataclass(codec.cls):
        assert codec.name in NOT_DATACLASSES
        return
    written: set[str] = set()
    for field in dataclasses.fields(codec.cls):
        if field.name in {"_id", "meta"} or field.name in NOT_WRITTEN.get(codec.cls, set()):
            continue
        renamed = RENAMED.get(codec.cls, {}).get(field.name, field.name)
        written.update((renamed,) if isinstance(renamed, str) else renamed)
    assert written == set(codec.fields)


# Classes with no meaning of their own in a score: bases and markers, which the spec does not define.
UNCODED = {
    OmkObject,
    SequentialEvent,
    Spanner,
    ContextEvent,
    TemporalContextEvent,
    TimedEdge,
    _ChordBase,
    Clef,
    DivisionShape,
    StackGroupShape,
}


def _concrete_classes() -> set[type]:
    for module in pkgutil.walk_packages(openmusickit.__path__, "openmusickit."):
        importlib.import_module(module.name)
    bases = [OmkObject, OmkEdge, Tone, Interval, TemporalElement, TemporalRatio, ToneCollection]
    bases += [ModalContext, Clef, DivisionShape, StackGroupShape]
    found, pending = set(), list(bases)
    while pending:
        cls = pending.pop()
        pending.extend(cls.__subclasses__())
        # `slots=True` replaces a dataclass, and the old class can linger in `__subclasses__`;
        # only the class its module exports is the real one.
        exported = getattr(sys.modules[cls.__module__], cls.__qualname__, None) is cls
        if cls.__module__.startswith("openmusickit.") and exported and not inspect.isabstract(cls):
            found.add(cls)
    return found


# Coded value types with no base class for `_concrete_classes` to find them by.
STANDALONE = {Mark, TempoTerm, Word, KeySignature, ModePattern}


def test_every_concrete_class_has_a_codec():
    coded = {codec.cls for codec in all_codecs()}
    assert _concrete_classes() - UNCODED == coded - STANDALONE


def test_an_uncoded_class_is_refused_by_name():
    with pytest.raises(UnexportableError, match="No vocabulary defines SequentialEvent"):
        Encoder(VOCABULARIES).tagged(SequentialEvent(), "node")

    class Marcato(Mark):  # a subclass of a defined type is not that type
        pass

    with pytest.raises(UnexportableError, match="No vocabulary defines Marcato"):
        encode(Marcato(name="marcato"))


# --- domains, both ways ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        TonalVector((7, 0)),
        TonalVector((0, 12)),
        TonalVector((-1, 0, 0)),
        TonalVector((0, 0, 0, 0)),
        ToneCollection([C], root=None, name="{root} chord"),
        ToneCollection([C], root=C, name="{root!r}"),
        ToneCollection([C], root=C, name="{root:nonsense}"),
        ToneCollection([C], root=C, name="{tonic}"),
        ToneCollection([C], root=C, name="}"),
        ToneCollection([PercussionTone()], root=PercussionTone(), name="{root:ascii}"),
    ],
    ids=repr,
)
def test_a_value_outside_its_domain_is_not_written(value):
    with pytest.raises(ValueError):
        encode(value)


def tv(diatonic, chromatic, octave=None):
    return {
        "@type": "wsmn:TonalVector",
        "diatonic": diatonic,
        "chromatic": chromatic,
        "octave": octave,
    }


def md(numerator, denominator, dots=0, ratio=None):
    return {
        "@type": "wsmn:MetricalDuration",
        "numerator": numerator,
        "denominator": denominator,
        "dots": dots,
        "ratio": ratio,
    }


def collection(name, root=None):
    return {"@type": "ToneCollection", "tones": [tv(0, 0)], "root": root, "name": name}


@pytest.mark.parametrize(
    "data, kind",
    [
        (tv(7, 0), "Tone"),
        (tv(0, 12), "Tone"),
        (tv(0, 0, 1.0), "Tone"),
        (tv(True, 0), "Tone"),
        (md(2, 4), "Duration"),  # 1/2
        (md(3, 8), "Duration"),  # 1/4 dotted
        (md(6, 1), "Duration"),  # 4/1 dotted
        (md(1, 3), "Duration"),
        (md(0, 4), "Duration"),
        (md(1, 4, dots=-1), "Duration"),
        ({"@type": "ClockDuration", "microseconds": 1.5}, "Duration"),
        ({"@type": "ClockDuration", "microseconds": "3/1"}, "Duration"),
        ({**tv(0, 0), "extra": 1}, "Tone"),  # a key the type does not have
        ({"@type": "wsmn:TonalVector", "diatonic": 0, "chromatic": 0}, "Tone"),  # one missing
        ({**tv(0, 0), "@id": "x"}, "Tone"),  # a value has no id
        (tv(0, 0), "Duration"),  # a type outside the field's kind
        ({"@type": "wsmn:Nonsense"}, "Tone"),
        ({"@type": "gregorian:Neume"}, "Tone"),  # an undeclared prefix
        ({"@type": "omk:SilentTone"}, "Tone"),  # the core is written bare
        ({"@type": "NoteEvent", "duration": None, "tones": []}, "Tone"),  # a node is not a value
        ({"tonic": None}, "ModalContext"),  # no @type
        (collection("{root}"), "ToneCollection"),
        (collection("{root!r}", tv(0, 0)), "ToneCollection"),
        (collection("{root:nonsense}", tv(0, 0)), "ToneCollection"),
        (
            {
                "@type": "wsmn:ChordType",
                "tones": [tv(0, 0)],
                "root": tv(1, 2),
                "name": "x",
                "bass": tv(0, 0),
                "quality": None,
                "suffix": None,
            },
            "ToneCollection",
        ),
        (
            {"@type": "wsmn:TimeSignature", "units": [], "presentation": ["4", "4", "4"]},
            "Measurable",
        ),
        (
            {
                "@type": "wsmn:Key",
                "tonic": None,
                "signature": None,
                "tones": {"@type": "ToneCollection", "tones": [], "root": None, "name": None},
                "mode": None,
                "name": None,
            },
            "ModalContext",
        ),
        ({"@type": "Word", "syllables": ["a", "b"], "stress": [None]}, "Word"),
        ({"@type": "Word", "syllables": [], "stress": []}, "Word"),
        ({"@type": "Word", "syllables": ["a"], "stress": ["PRIMARY"]}, "Word"),
        ({"@type": "TemporalUnit", "count": -1, "base": md(1, 4)}, "Measurable"),
    ],
    ids=repr,
)
def test_a_value_outside_its_domain_is_rejected_on_read(data, kind):
    with pytest.raises(OmkJsonError):
        decode(data, kind)


def test_a_rejection_names_the_type_and_the_normal_form():
    with pytest.raises(OmkJsonError, match=r"wsmn:MetricalDuration.*1/2 with 0 dots, not 2/4"):
        decode(md(2, 4), "Duration")


def test_the_template_grammar():
    forms = frozenset({"ascii", "unicode"})
    for good in ["", "major", "{root}", "{root:ascii}maj7", "{{root}}", "{{{root}}}"]:
        check_template(good, forms)
    for bad in ["{", "}", "{root", "{root:}", "{root!s}", "{ root }", "{0}", "{}"]:
        with pytest.raises(ValueError):
            check_template(bad, forms)
    check_template("{{root}} is literal", None)
    with pytest.raises(ValueError, match="no root"):
        check_template("{root}", None)
