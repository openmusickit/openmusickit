"""The `omk` vocabulary (`docs/spec/vocabulary-omk.qmd`): every node type,
every edge kind, the values that belong to no musical system, and the kinds.

>>> from openmusickit.io.omk_json.vocabulary import Encoder
>>> from openmusickit.values.time.clock_time import ClockDuration
>>> Encoder([CORE]).value(ClockDuration(1_500_000))
{'microseconds': 1500000, '@type': 'ClockDuration'}
"""

from __future__ import annotations

from typing import Any

from openmusickit.graph.edge import (
    Branch,
    Contains,
    EdgeOrigin,
    EdgeType,
    Next,
    OmkEdge,
    Simultaneous,
    TimingAnchor,
)
from openmusickit.io.omk_json.primitives import (
    decode_boolean,
    decode_enum,
    decode_integer,
    decode_rational,
    decode_string,
    encode_enum,
    encode_rational,
)
from openmusickit.io.omk_json.vocabulary import Decoder, Encoder, TypeCodec, Vocabulary
from openmusickit.objects.chord_event import ChordEvent
from openmusickit.objects.context_event import (
    ClefEvent,
    MeterEvent,
    ModalContextEvent,
    TempoEvent,
)
from openmusickit.objects.division_event import DivisionEvent
from openmusickit.objects.lyrics import LyricSection, LyricSyllable
from openmusickit.objects.marking import Marking, MarkSpanner
from openmusickit.objects.note_event import NoteEvent
from openmusickit.objects.part import LineGroup, Part, PercussionPart, StackGroup, Stint
from openmusickit.objects.score import Score
from openmusickit.objects.sync_line import SyncLine, SyncPoint
from openmusickit.values.scoring.mark import AttachmentMode, Mark, MarkType
from openmusickit.values.scoring.tempo_term import TempoTerm
from openmusickit.values.text.word import LexicalStress, Word
from openmusickit.values.time.clock_time import CLOCK_TIME, ClockDuration, Tempo
from openmusickit.values.time.duration import (
    ANY_TEMPORAL_SYSTEM,
    CompoundTemporalUnit,
    GraceDuration,
    TemporalRatio,
    TemporalUnit,
    ZeroDuration,
)
from openmusickit.values.tone.silent_tone import SilentTone
from openmusickit.values.tone.tone import ANY_TONAL_SYSTEM
from openmusickit.values.tone.tone_collection import ToneCollection

# The kinds (§7.3). Another vocabulary adds its own types to these by naming them in its codecs.
DURATION = "Duration"
MEASURABLE = "Measurable"
TEMPORAL_RATIO = "TemporalRatio"
TONE = "Tone"
INTERVAL = "Interval"
TONE_COLLECTION = "ToneCollection"
MODAL_CONTEXT = "ModalContext"
CLEF = "Clef"
DIVISION_SHAPE = "DivisionShape"
STACK_GROUP_SHAPE = "StackGroupShape"

# A field typed by one exact type, not a kind, is checked with the type's own name as its kind.
MARK = "Mark"
TEMPO_TERM = "TempoTerm"
WORD = "Word"
CLOCK_DURATION = "ClockDuration"
EXACT_TONE_COLLECTION = "omk:ToneCollection"


def _optional_string(data: Any) -> str | None:
    return None if data is None else decode_string(data)


def _optional_integer(data: Any) -> int | None:
    return None if data is None else decode_integer(data)


def _optional_enum(member: Any) -> str | None:
    return None if member is None else encode_enum(member)


# --- nodes: events -----------------------------------------------------------------------------


def _encode_note_event(note: NoteEvent, e: Encoder) -> dict[str, Any]:
    return {"duration": e.optional(note.duration), "tones": e.set(note.tones)}


def _decode_note_event(f: dict[str, Any], d: Decoder) -> NoteEvent:
    return NoteEvent(duration=d.optional(f["duration"], DURATION), tones=d.set(f["tones"], TONE))


def _encode_chord_event(event: ChordEvent, e: Encoder) -> dict[str, Any]:
    return {"duration": e.optional(event.duration), "chord": e.value(event.chord)}


def _decode_chord_event(f: dict[str, Any], d: Decoder) -> ChordEvent:
    return ChordEvent(
        duration=d.optional(f["duration"], DURATION), chord=d.value(f["chord"], TONE_COLLECTION)
    )


def _encode_lyric_syllable(syllable: LyricSyllable, e: Encoder) -> dict[str, Any]:
    return {
        "duration": e.optional(syllable.duration),
        "word": e.value(syllable.word),
        "index": syllable.index,
    }


def _decode_lyric_syllable(f: dict[str, Any], d: Decoder) -> LyricSyllable:
    return LyricSyllable(
        duration=d.optional(f["duration"], DURATION),
        word=d.value(f["word"], WORD),
        index=decode_integer(f["index"]),
    )


def _encode_division_event(division: DivisionEvent, e: Encoder) -> dict[str, Any]:
    return {"shape": e.optional(division.shape)}


def _decode_division_event(f: dict[str, Any], d: Decoder) -> DivisionEvent:
    return DivisionEvent(shape=d.optional(f["shape"], DIVISION_SHAPE))


# --- nodes: context events ---------------------------------------------------------------------


def _encode_modal_context_event(event: ModalContextEvent, e: Encoder) -> dict[str, Any]:
    return {"modal_context": e.optional(event.modal_context)}


def _decode_modal_context_event(f: dict[str, Any], d: Decoder) -> ModalContextEvent:
    return ModalContextEvent(modal_context=d.optional(f["modal_context"], MODAL_CONTEXT))


def _encode_meter_event(event: MeterEvent, e: Encoder) -> dict[str, Any]:
    return {"meter": e.optional(event.meter)}


def _decode_meter_event(f: dict[str, Any], d: Decoder) -> MeterEvent:
    return MeterEvent(meter=d.optional(f["meter"], MEASURABLE))


def _encode_tempo_event(event: TempoEvent, e: Encoder) -> dict[str, Any]:
    return {"tempo": e.optional(event.tempo), "term": e.optional(event.term)}


def _decode_tempo_event(f: dict[str, Any], d: Decoder) -> TempoEvent:
    return TempoEvent(
        tempo=d.optional(f["tempo"], TEMPORAL_RATIO), term=d.optional(f["term"], TEMPO_TERM)
    )


def _encode_clef_event(event: ClefEvent, e: Encoder) -> dict[str, Any]:
    return {"clef": e.optional(event.clef)}


def _decode_clef_event(f: dict[str, Any], d: Decoder) -> ClefEvent:
    return ClefEvent(clef=d.optional(f["clef"], CLEF))


# --- nodes: marks and lyrics -------------------------------------------------------------------


def _encode_marking(marking: Marking | MarkSpanner, e: Encoder) -> dict[str, Any]:
    return {"mark": e.value(marking.mark)}


def _decode_marking(f: dict[str, Any], d: Decoder) -> Marking:
    return Marking(mark=d.value(f["mark"], MARK))


def _decode_mark_spanner(f: dict[str, Any], d: Decoder) -> MarkSpanner:
    return MarkSpanner(mark=d.value(f["mark"], MARK))


def _encode_lyric_section(section: LyricSection, e: Encoder) -> dict[str, Any]:
    return {
        "section_type": section.section_type,
        "section_number": section.section_number,
        "section_name": section.section_name,
        "language": section.language,
    }


def _decode_lyric_section(f: dict[str, Any], d: Decoder) -> LyricSection:
    section_type, section_name = (
        _optional_string(f["section_type"]),
        _optional_string(f["section_name"]),
    )
    if section_type is not None and section_name is None:
        # The model names such a section itself, so a null name could not be read back as null.
        raise ValueError("A LyricSection with a section_type must have a section_name.")
    return LyricSection(
        section_type=section_type,
        section_number=_optional_integer(f["section_number"]),
        section_name=section_name,
        language=_optional_string(f["language"]),
    )


# --- nodes: performers, groups, scores, timelines ------------------------------------------------


def _encode_part(part: Part, e: Encoder) -> dict[str, Any]:
    return {"name": part.name}


def _decode_part(f: dict[str, Any], d: Decoder) -> Part:
    return Part(name=decode_string(f["name"]))


def _encode_percussion_part(part: PercussionPart, e: Encoder) -> dict[str, Any]:
    return {"name": part.name, "palette": e.optional(part.palette)}


def _decode_percussion_part(f: dict[str, Any], d: Decoder) -> PercussionPart:
    return PercussionPart(
        name=decode_string(f["name"]), palette=d.optional(f["palette"], TONE_COLLECTION)
    )


def _encode_stint(stint: Stint, e: Encoder) -> dict[str, Any]:
    return {"transposition": e.optional(stint.transposition)}


def _decode_stint(f: dict[str, Any], d: Decoder) -> Stint:
    return Stint(transposition=d.optional(f["transposition"], INTERVAL))


def _encode_line_group(group: LineGroup, e: Encoder) -> dict[str, Any]:
    return {"name": group.name}


def _decode_line_group(f: dict[str, Any], d: Decoder) -> LineGroup:
    return LineGroup(name=_optional_string(f["name"]))


def _encode_stack_group(group: StackGroup, e: Encoder) -> dict[str, Any]:
    return {
        "name": group.name,
        "abbreviation": group.abbreviation,
        "shape": e.optional(group.shape),
    }


def _decode_stack_group(f: dict[str, Any], d: Decoder) -> StackGroup:
    return StackGroup(
        name=_optional_string(f["name"]),
        abbreviation=_optional_string(f["abbreviation"]),
        shape=d.optional(f["shape"], STACK_GROUP_SHAPE),
    )


SCORE_FIELDS = (
    "title",
    "subtitle",
    "composer",
    "lyricist",
    "arranger",
    "copyright",
    "opus",
    "dedication",
)


def _encode_score(score: Score, e: Encoder) -> dict[str, Any]:
    return {name: getattr(score, name) for name in SCORE_FIELDS}


def _decode_score(f: dict[str, Any], d: Decoder) -> Score:
    return Score(**{name: _optional_string(f[name]) for name in SCORE_FIELDS})


def _encode_sync_line(line: SyncLine, e: Encoder) -> dict[str, Any]:
    return {
        "temporal_system": e.temporal_system(line.temporal_system),
        "name": line.name,
        "description": line.description,
    }


def _decode_sync_line(f: dict[str, Any], d: Decoder) -> SyncLine:
    return SyncLine(
        temporal_system=d.temporal_system(f["temporal_system"]),
        name=_optional_string(f["name"]),
        description=_optional_string(f["description"]),
    )


def _encode_sync_point(point: SyncPoint, e: Encoder) -> dict[str, Any]:
    return {"offset": e.value(point.offset), "name": point.name, "description": point.description}


def _decode_sync_point(f: dict[str, Any], d: Decoder) -> SyncPoint:
    return SyncPoint(
        offset=d.value(f["offset"], DURATION),
        name=_optional_string(f["name"]),
        description=_optional_string(f["description"]),
    )


# --- edges -----------------------------------------------------------------------------------


def _encode_next(edge: Next, e: Encoder) -> dict[str, Any]:
    return {"origin": encode_enum(edge.origin)}


def _decode_next(f: dict[str, Any], d: Decoder) -> Next:
    return Next(origin=decode_enum(EdgeOrigin, f["origin"]))


def _encode_timed(edge: Branch | Simultaneous, e: Encoder) -> dict[str, Any]:
    return {
        "origin": encode_enum(edge.origin),
        "anchor": encode_enum(edge.anchor),
        "displacement": e.optional(edge.displacement),
    }


def _decode_branch(f: dict[str, Any], d: Decoder) -> Branch:
    return Branch(
        origin=decode_enum(EdgeOrigin, f["origin"]),
        anchor=decode_enum(TimingAnchor, f["anchor"]),
        displacement=d.optional(f["displacement"], DURATION),
    )


def _decode_simultaneous(f: dict[str, Any], d: Decoder) -> Simultaneous:
    return Simultaneous(
        origin=decode_enum(EdgeOrigin, f["origin"]),
        anchor=decode_enum(TimingAnchor, f["anchor"]),
        displacement=d.optional(f["displacement"], DURATION),
    )


def _encode_contains(edge: Contains, e: Encoder) -> dict[str, Any]:
    return {"origin": encode_enum(edge.origin), "displacement": e.optional(edge.displacement)}


def _decode_contains(f: dict[str, Any], d: Decoder) -> Contains:
    return Contains(
        origin=decode_enum(EdgeOrigin, f["origin"]),
        displacement=d.optional(f["displacement"], DURATION),
    )


def _encode_edge(edge: OmkEdge, e: Encoder) -> dict[str, Any]:
    return {"origin": encode_enum(edge.origin), "relation": encode_enum(edge.type)}


def _decode_edge(f: dict[str, Any], d: Decoder) -> OmkEdge:
    vocabulary, local = d.resolve(f["relation"])
    if vocabulary.prefix != "omk":
        # No vocabulary can add a relation yet (`EdgeType` is closed; `_plans/revisit.md`).
        raise ValueError(f"{f['relation']!r} is not a relation of {vocabulary.uri}.")
    return OmkEdge(type=decode_enum(EdgeType, local), origin=decode_enum(EdgeOrigin, f["origin"]))


# --- values ----------------------------------------------------------------------------------


def _encode_nothing(value: Any, e: Encoder) -> dict[str, Any]:
    return {}


def _encode_grace_duration(grace: GraceDuration, e: Encoder) -> dict[str, Any]:
    return {"nominal": e.value(grace.nominal), "on_beat": grace.on_beat}


def _decode_grace_duration(f: dict[str, Any], d: Decoder) -> GraceDuration:
    return GraceDuration(d.value(f["nominal"], DURATION), on_beat=decode_boolean(f["on_beat"]))


def _encode_clock_duration(duration: ClockDuration, e: Encoder) -> dict[str, Any]:
    return {"microseconds": encode_rational(duration.microseconds)}


def _decode_clock_duration(f: dict[str, Any], d: Decoder) -> ClockDuration:
    return ClockDuration(decode_rational(f["microseconds"]))


def _encode_temporal_unit(unit: TemporalUnit, e: Encoder) -> dict[str, Any]:
    return {"count": unit.count, "base": e.value(unit.base)}


def _decode_temporal_unit(f: dict[str, Any], d: Decoder) -> TemporalUnit:
    return TemporalUnit(decode_integer(f["count"]), d.value(f["base"], MEASURABLE))


def _encode_compound_temporal_unit(unit: CompoundTemporalUnit, e: Encoder) -> dict[str, Any]:
    return {"units": e.array(unit.units)}


def _decode_compound_temporal_unit(f: dict[str, Any], d: Decoder) -> CompoundTemporalUnit:
    return CompoundTemporalUnit(d.array(f["units"], MEASURABLE))


def _encode_temporal_ratio(ratio: TemporalRatio, e: Encoder) -> dict[str, Any]:
    return {"nominal": e.value(ratio.nominal), "contextual": e.value(ratio.contextual)}


def _decode_temporal_ratio(f: dict[str, Any], d: Decoder) -> TemporalRatio:
    return TemporalRatio(d.value(f["nominal"], MEASURABLE), d.value(f["contextual"], MEASURABLE))


def _encode_tempo(tempo: Tempo, e: Encoder) -> dict[str, Any]:
    return {
        "count": tempo.nominal.count,
        "beat": e.value(tempo.nominal.base),
        "clock_time": e.value(tempo.contextual.base),
    }


def _decode_tempo(f: dict[str, Any], d: Decoder) -> Tempo:
    return Tempo(
        decode_integer(f["count"]),
        d.value(f["beat"], DURATION),
        d.value(f["clock_time"], CLOCK_DURATION),
    )


def _encode_tone_collection(collection: ToneCollection, e: Encoder) -> dict[str, Any]:
    return {
        "tones": e.array(collection.tones),
        "root": e.optional(collection.root),
        "name": e.template(collection.name_template, collection.root),
    }


def _decode_tone_collection(f: dict[str, Any], d: Decoder) -> ToneCollection:
    root = d.optional(f["root"], TONE)
    return ToneCollection(d.array(f["tones"], TONE), root=root, name=d.template(f["name"], root))


def _encode_mark(mark: Mark, e: Encoder) -> dict[str, Any]:
    return {
        "name": mark.name,
        "description": mark.description,
        "kind": _optional_enum(mark.kind),
        "attachment_mode": _optional_enum(mark.attachment_mode),
        "aliases": list(mark.aliases),
        "binds": mark.binds,
    }


def _decode_mark(f: dict[str, Any], d: Decoder) -> Mark:
    return Mark(
        name=decode_string(f["name"]),
        description=_optional_string(f["description"]),
        kind=None if f["kind"] is None else decode_enum(MarkType, f["kind"]),
        attachment_mode=(
            None
            if f["attachment_mode"] is None
            else decode_enum(AttachmentMode, f["attachment_mode"])
        ),
        aliases=_strings(f["aliases"]),
        binds=decode_boolean(f["binds"]),
    )


def _strings(data: Any) -> tuple[str, ...]:
    if type(data) is not list:
        raise ValueError(f"Expected an array of strings, found {data!r}.")
    return tuple(decode_string(item) for item in data)


def _encode_tempo_term(term: TempoTerm, e: Encoder) -> dict[str, Any]:
    return {"name": term.name, "description": term.description, "aliases": list(term.aliases)}


def _decode_tempo_term(f: dict[str, Any], d: Decoder) -> TempoTerm:
    return TempoTerm(
        name=decode_string(f["name"]),
        description=_optional_string(f["description"]),
        aliases=_strings(f["aliases"]),
    )


def _encode_word(word: Word, e: Encoder) -> dict[str, Any]:
    return {"syllables": list(word.syllables), "stress": [_optional_enum(s) for s in word.stress]}


def _decode_word(f: dict[str, Any], d: Decoder) -> Word:
    stress = f["stress"]
    if type(stress) is not list:
        raise ValueError(f"Expected an array of stresses, found {stress!r}.")
    syllables = _strings(f["syllables"])
    if len(stress) != len(syllables):
        raise ValueError(f"A Word has {len(syllables)} syllables and {len(stress)} stresses.")
    return Word(
        syllables,
        stress=[None if s is None else decode_enum(LexicalStress, s) for s in stress],
    )


def _node(name, cls, fields, encode, decode) -> TypeCodec:
    return TypeCodec(name, cls, "node", fields, encode, decode)


def _edge(name, cls, fields, encode, decode) -> TypeCodec:
    return TypeCodec(name, cls, "edge", fields, encode, decode)


def _value(name, cls, fields, encode, decode, kinds=(), display_forms=()) -> TypeCodec:
    return TypeCodec(
        name, cls, "value", fields, encode, decode, frozenset(kinds), frozenset(display_forms)
    )


_DURATION_KINDS = (DURATION, MEASURABLE)

CORE = Vocabulary(
    prefix="omk",
    uri="https://openmusickit.org/spec/omk",
    version="0.1",
    codecs=(
        _node(
            "NoteEvent", NoteEvent, ("duration", "tones"), _encode_note_event, _decode_note_event
        ),
        _node(
            "ChordEvent",
            ChordEvent,
            ("duration", "chord"),
            _encode_chord_event,
            _decode_chord_event,
        ),
        _node(
            "LyricSyllable",
            LyricSyllable,
            ("duration", "word", "index"),
            _encode_lyric_syllable,
            _decode_lyric_syllable,
        ),
        _node(
            "DivisionEvent",
            DivisionEvent,
            ("shape",),
            _encode_division_event,
            _decode_division_event,
        ),
        _node(
            "ModalContextEvent",
            ModalContextEvent,
            ("modal_context",),
            _encode_modal_context_event,
            _decode_modal_context_event,
        ),
        _node("MeterEvent", MeterEvent, ("meter",), _encode_meter_event, _decode_meter_event),
        _node(
            "TempoEvent", TempoEvent, ("tempo", "term"), _encode_tempo_event, _decode_tempo_event
        ),
        _node("ClefEvent", ClefEvent, ("clef",), _encode_clef_event, _decode_clef_event),
        _node("Marking", Marking, ("mark",), _encode_marking, _decode_marking),
        _node("MarkSpanner", MarkSpanner, ("mark",), _encode_marking, _decode_mark_spanner),
        _node(
            "LyricSection",
            LyricSection,
            ("section_type", "section_number", "section_name", "language"),
            _encode_lyric_section,
            _decode_lyric_section,
        ),
        _node("Part", Part, ("name",), _encode_part, _decode_part),
        _node(
            "PercussionPart",
            PercussionPart,
            ("name", "palette"),
            _encode_percussion_part,
            _decode_percussion_part,
        ),
        _node("Stint", Stint, ("transposition",), _encode_stint, _decode_stint),
        _node("LineGroup", LineGroup, ("name",), _encode_line_group, _decode_line_group),
        _node(
            "StackGroup",
            StackGroup,
            ("name", "abbreviation", "shape"),
            _encode_stack_group,
            _decode_stack_group,
        ),
        _node("Score", Score, SCORE_FIELDS, _encode_score, _decode_score),
        _node(
            "SyncLine",
            SyncLine,
            ("temporal_system", "name", "description"),
            _encode_sync_line,
            _decode_sync_line,
        ),
        _node(
            "SyncPoint",
            SyncPoint,
            ("offset", "name", "description"),
            _encode_sync_point,
            _decode_sync_point,
        ),
        _edge("Next", Next, ("origin",), _encode_next, _decode_next),
        _edge(
            "Branch", Branch, ("origin", "anchor", "displacement"), _encode_timed, _decode_branch
        ),
        _edge(
            "Simultaneous",
            Simultaneous,
            ("origin", "anchor", "displacement"),
            _encode_timed,
            _decode_simultaneous,
        ),
        _edge("Contains", Contains, ("origin", "displacement"), _encode_contains, _decode_contains),
        _edge("Edge", OmkEdge, ("origin", "relation"), _encode_edge, _decode_edge),
        _value("SilentTone", SilentTone, (), _encode_nothing, lambda f, d: SilentTone(), (TONE,)),
        _value(
            "ZeroDuration",
            ZeroDuration,
            (),
            _encode_nothing,
            lambda f, d: ZeroDuration(),
            _DURATION_KINDS,
        ),
        _value(
            "GraceDuration",
            GraceDuration,
            ("nominal", "on_beat"),
            _encode_grace_duration,
            _decode_grace_duration,
            _DURATION_KINDS,
        ),
        _value(
            "ClockDuration",
            ClockDuration,
            ("microseconds",),
            _encode_clock_duration,
            _decode_clock_duration,
            (*_DURATION_KINDS, CLOCK_DURATION),
        ),
        _value(
            "TemporalUnit",
            TemporalUnit,
            ("count", "base"),
            _encode_temporal_unit,
            _decode_temporal_unit,
            (MEASURABLE,),
        ),
        _value(
            "CompoundTemporalUnit",
            CompoundTemporalUnit,
            ("units",),
            _encode_compound_temporal_unit,
            _decode_compound_temporal_unit,
            (MEASURABLE,),
        ),
        _value(
            "TemporalRatio",
            TemporalRatio,
            ("nominal", "contextual"),
            _encode_temporal_ratio,
            _decode_temporal_ratio,
            (TEMPORAL_RATIO,),
        ),
        _value(
            "Tempo",
            Tempo,
            ("count", "beat", "clock_time"),
            _encode_tempo,
            _decode_tempo,
            (TEMPORAL_RATIO,),
        ),
        _value(
            "ToneCollection",
            ToneCollection,
            ("tones", "root", "name"),
            _encode_tone_collection,
            _decode_tone_collection,
            (TONE_COLLECTION, EXACT_TONE_COLLECTION),
        ),
        _value(
            "Mark",
            Mark,
            ("name", "description", "kind", "attachment_mode", "aliases", "binds"),
            _encode_mark,
            _decode_mark,
            (MARK,),
        ),
        _value(
            "TempoTerm",
            TempoTerm,
            ("name", "description", "aliases"),
            _encode_tempo_term,
            _decode_tempo_term,
            (TEMPO_TERM,),
        ),
        _value("Word", Word, ("syllables", "stress"), _encode_word, _decode_word, (WORD,)),
    ),
    temporal_systems={"any": ANY_TEMPORAL_SYSTEM, "clock-time": CLOCK_TIME},
    tonal_systems={"any": ANY_TONAL_SYSTEM},
)
