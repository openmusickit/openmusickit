"""MusicXML in: a `<score-partwise>` document becomes an `OmkGraph` holding one `Score`.

The mapping, rule by rule, is `_plans/musicxml.md` §5; in short:

- a `<score-part>` is a `Part` with a `Stint` over its line, or a `Part`
  performing a `LineGroup` of one line per staff, or, for a drum kit, a
  `LineGroup` of one line per `<score-instrument>` with a `PercussionPart` each;
- on a staff, the lowest voice number is the main line and every contiguous
  run of another voice is a line branched from the event it starts under;
- every measure boundary is a `DivisionEvent` in every line that crosses it,
  with the bar-line shape; key, meter, clef and tempo are context events on
  every staff's main line;
- a `<note>` is a `NoteEvent` at sounding pitch; a chord whose tones differ in
  what is tied to them or fingered on them is split so that every tie has an
  event of its own; ties, slurs, hairpins and pedals are `MarkSpanner`s,
  everything else in `<notations>` and `<direction>` a `Marking`;
- `<lyric>`s are syllable lines, one per verse number, joined to their notes;
  `<harmony>` is a `ChordEvent` on a chord line, pinned to the event at its
  position, with no duration;
- with two or more parts, a bar grid (`SyncLine`) pins every part's head and
  divisions to one instant per bar line.

Presentation is dropped. What the writer needs back and the model cannot
hold goes in `node.meta["musicxml"]`, a dict OMK core never reads. Its keys:

- `Score`: `movement_number`, `movement_title`, `encoding`, `source`.
- `Part`: `id`, `index`, `abbreviation`, `groups`, `instruments`, `midi`.
- a line's head event: `staff`, `voice`, `hidden`.
- `DivisionEvent`: `number`, `implicit`, `width`, `left`, `multiple_rest`, `slash`.
- `NoteEvent`: `forward` (a gap the file left), `hidden`, `cue`, `slash_pitch`,
  `display` (unpitched step and octave), `notehead`, `instrument`, `voice`
  (kit lines), `tuplet`, `measure_repeat`, `staff` (only where it differs).
- `Marking` / `MarkSpanner`: `offset`, `tremolo`, `fingering`, `accidental_mark`,
  `ending`, `element` (a minted mark's source element), `fermata_type`, `text`.
- `MeterEvent`: `symbol`; `TempoEvent`: `sound_tempo`, `per_minute`, `tempo_hidden` (the figure is not printed), `term_hidden`.
- `LyricSyllable`: `extend`, `humming`, `laughing`, `end_line`, `end_paragraph`.
- `ChordEvent`: `kind`, `kind_text`, `frame`.
"""

from __future__ import annotations

import warnings
import xml.etree.ElementTree as ET
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import IO

from openmusickit.errors import MusicXmlError, OmkWarning
from openmusickit.graph.graph import GraphMeta, OmkGraph
from openmusickit.graph.graph_adapter import GraphAdapter
from openmusickit.io.musicxml import container, tables
from openmusickit.objects.chord_event import ChordEvent
from openmusickit.objects.context_event import (
    ClefEvent,
    ContextEvent,
    MeterEvent,
    ModalContextEvent,
    TempoEvent,
)
from openmusickit.objects.division_event import DivisionEvent
from openmusickit.objects.lyrics import LyricSection, LyricSyllable
from openmusickit.objects.marking import Marking, MarkSpanner
from openmusickit.objects.note_event import NoteEvent, Rest
from openmusickit.objects.omk_object import OmkObject, SequentialEvent
from openmusickit.objects.part import LineGroup, Part, PercussionPart, Stint
from openmusickit.objects.score import Score
from openmusickit.objects.sync_line import SyncLine
from openmusickit.systems.wsmn.percussion.symbols import hit
from openmusickit.systems.wsmn.scoring import symbols as scoring
from openmusickit.systems.wsmn.scoring.staff_clef import ClefSign, StaffClef
from openmusickit.systems.wsmn.temporal.metrical_duration import MetricalDuration
from openmusickit.systems.wsmn.temporal.time_signature import TimeSignature
from openmusickit.systems.wsmn.temporal.wsmn import WSMN_TEMPORAL
from openmusickit.systems.wsmn.tonal.chords import Chord, ChordType
from openmusickit.systems.wsmn.tonal.key import Key, KeySignature
from openmusickit.systems.wsmn.tonal.symbols import P4, P5, C
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from openmusickit.values.scoring.mark import AttachmentMode, Mark, MarkType
from openmusickit.values.text.word import Word
from openmusickit.values.time.clock_time import Tempo
from openmusickit.values.time.duration import (
    Duration,
    GraceDuration,
    Measurable,
    TemporalRatio,
    TemporalUnit,
    ZeroDuration,
)

XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
ORIGIN = TonalVector((0, 0, 0))

# Sort ranks for events that share an onset: a bar line ends the bar before
# the contexts of the next bar, a left bar line follows them, then the notes.
_DIVISION, _CONTEXT, _LEFT_BAR, _NOTE = 0, 1, 2, 3


def read(source: str | Path | IO[bytes], graph_engine: GraphAdapter | None = None) -> OmkGraph:
    """The score in a MusicXML file, as a new graph holding one `Score`.

    `source` is a path or a binary stream; `.mxl` archives are recognised by
    their contents. Every musical fact the reader cannot place raises an
    `OmkWarning` naming the measure.

    >>> import io
    >>> from openmusickit.objects.note_event import NoteEvent
    >>> from openmusickit.objects.score import Score
    >>> doc = io.BytesIO(b'''<score-partwise version="4.0">
    ...   <work><work-title>Two notes</work-title></work>
    ...   <part-list><score-part id="P1"><part-name>Flute</part-name></score-part></part-list>
    ...   <part id="P1"><measure number="1">
    ...     <attributes><divisions>1</divisions>
    ...       <time><beats>2</beats><beat-type>4</beat-type></time></attributes>
    ...     <note><pitch><step>C</step><octave>4</octave></pitch>
    ...       <duration>1</duration><type>quarter</type></note>
    ...     <note><pitch><step>D</step><octave>4</octave></pitch>
    ...       <duration>1</duration><type>quarter</type></note>
    ...   </measure></part></score-partwise>''')
    >>> graph = read(doc)
    >>> score = next(graph.nodes(Score))
    >>> score.title, [part.name for part in graph.score_parts(score)]
    ('Two notes', ['Flute'])
    >>> head = next(graph.score_lines(score))
    >>> [type(event).__name__ for event in graph.walk_line(head)]
    ['MeterEvent', 'NoteEvent', 'NoteEvent', 'DivisionEvent']

    Raises
    ------
    MusicXmlError
        if `source` is not a partwise MusicXML score (see `container.load`).
    """
    graph = OmkGraph(GraphMeta(), graph_engine)
    read_into(graph, source)
    return graph


def read_into(graph: OmkGraph, source: str | Path | IO[bytes]) -> Score:
    """Adds the score in `source` to `graph` and returns its `Score` node.
    Nothing already on the graph is touched or related to the new score."""
    root = container.load(source)
    return _Reader(graph, root).build()


def xml_meta(node: OmkObject) -> dict:
    """The `musicxml` dict of `node.meta`, made on first use."""
    return node.meta.setdefault("musicxml", {})


# --- the document as a whole ------------------------------------------------------------------


@dataclass
class _PartInfo:
    id: str
    index: int
    name: str
    abbreviation: str | None
    instruments: dict[str, str]  # instrument id -> name, in part-list order
    midi: dict[str, dict[str, str]]
    groups: list[dict[str, str | None]]


class _Reader:
    def __init__(self, graph: OmkGraph, root: ET.Element):
        self.graph = graph
        self.root = root
        self.score = Score()
        self._counts: Counter[str] = Counter()

    def warn(self, message: str) -> None:
        warnings.warn(message, OmkWarning, stacklevel=4)

    def build(self) -> Score:
        self._read_header()
        infos = self._read_part_list()
        parts = {part.get("id"): part for part in self.root.findall("part")}
        lengths = self._measure_lengths(infos, parts)
        self.graph.add_node(self.score)
        grid_lines: list[tuple[SequentialEvent, list[tuple[Fraction, DivisionEvent]]]] = []
        for info in infos:
            element = parts.get(info.id)
            if element is None:
                self.warn(f"part {info.name!r} ({info.id}) is listed but has no <part>; skipped")
                continue
            reader = _PartReader(self, info, element, lengths)
            grid_lines.extend(reader.build())
        if len(grid_lines) >= 2:
            self._build_grid(grid_lines)
        return self.score

    # header

    def _read_header(self) -> None:
        root, score = self.root, self.score
        work = root.find("work")
        title = _text(work, "work-title") if work is not None else None
        movement_title = _text(root, "movement-title")
        score.title = title or movement_title
        if title and movement_title:
            xml_meta(score)["movement_title"] = movement_title
        if work is not None and _text(work, "work-number"):
            score.opus = _text(work, "work-number")
        if _text(root, "movement-number"):
            xml_meta(score)["movement_number"] = _text(root, "movement-number")
        identification = root.find("identification")
        if identification is not None:
            for creator in identification.findall("creator"):
                kind, name = creator.get("type"), (creator.text or "").strip()
                if not name:
                    continue
                if kind in ("composer", "lyricist", "arranger") and getattr(score, kind) is None:
                    setattr(score, kind, name)
                else:
                    xml_meta(score).setdefault("creators", []).append([kind, name])
            rights = [(r.text or "").strip() for r in identification.findall("rights")]
            rights = [r for r in rights if r]
            if rights:
                score.copyright = "\n".join(rights)
            encoding = identification.find("encoding")
            if encoding is not None:
                xml_meta(score)["encoding"] = [
                    [child.tag, (child.text or "").strip()]
                    for child in encoding
                    if child.tag in ("software", "encoding-date", "encoder", "encoding-description")
                ]
            if _text(identification, "source"):
                xml_meta(score)["source"] = _text(identification, "source")

    def _read_part_list(self) -> list[_PartInfo]:
        infos: list[_PartInfo] = []
        open_groups: dict[str, dict[str, str | None]] = {}
        part_list = self.root.find("part-list")
        if part_list is None:
            raise MusicXmlError("The score has no <part-list>.")
        for child in part_list:
            if child.tag == "part-group":
                number = child.get("number", "1")
                if child.get("type") == "start":
                    open_groups[number] = {
                        "number": number,
                        "symbol": _text(child, "group-symbol"),
                        "name": _text(child, "group-name"),
                        "barline": _text(child, "group-barline"),
                    }
                else:
                    open_groups.pop(number, None)
            elif child.tag == "score-part":
                instruments = {
                    inst.get("id"): _text(inst, "instrument-name") or ""
                    for inst in child.findall("score-instrument")
                }
                midi = {}
                for inst in child.findall("midi-instrument"):
                    midi[inst.get("id")] = {sub.tag: (sub.text or "").strip() for sub in inst}
                infos.append(
                    _PartInfo(
                        id=child.get("id"),
                        index=len(infos),
                        name=child.findtext("part-name") or "",
                        abbreviation=child.findtext("part-abbreviation"),
                        instruments=instruments,
                        midi=midi,
                        groups=[dict(group) for group in open_groups.values()],
                    )
                )
        return infos

    def _measure_lengths(
        self, infos: list[_PartInfo], parts: dict[str, ET.Element]
    ) -> list[Fraction]:
        """Every measure's length, the longest any part makes it; parts that
        disagree are reported, and the reader pads the shorter ones."""
        per_part: dict[str, list[Fraction]] = {}
        for info in infos:
            element = parts.get(info.id)
            if element is not None:
                per_part[info.id] = _content_lengths(element)
        if not per_part:
            return []
        count = max(len(lengths) for lengths in per_part.values())
        for info in infos:
            lengths = per_part.get(info.id)
            if lengths is not None and len(lengths) != count:
                raise MusicXmlError(
                    f"part {info.name!r} has {len(lengths)} measures; another part has {count}."
                )
        combined: list[Fraction] = []
        for index in range(count):
            found = {info.id: per_part[info.id][index] for info in infos if info.id in per_part}
            longest = max(found.values())
            combined.append(longest)
            short = [info.name for info in infos if info.id in found and found[info.id] < longest]
            if short and longest > 0:
                self.warn(
                    f"measure {index + 1}: parts {short} are shorter than the longest part "
                    f"({longest} whole notes); their lines are padded with unspecified content"
                )
        return combined

    def _build_grid(
        self, grid_lines: list[tuple[SequentialEvent, list[tuple[Fraction, DivisionEvent]]]]
    ) -> None:
        grid = SyncLine(temporal_system=WSMN_TEMPORAL, name=self.score.title or "bars")
        self.graph.add_sync_line_to_score(self.score, grid)
        for head, divisions in grid_lines:
            self.graph.sync_event(head, grid, ZeroDuration())
            for position, division in divisions:
                if position > 0:
                    self.graph.sync_event(division, grid, MetricalDuration.from_length(position))


def _text(element: ET.Element | None, tag: str) -> str | None:
    if element is None:
        return None
    text = element.findtext(tag)
    return text.strip() if text and text.strip() else None


def _content_lengths(part: ET.Element) -> list[Fraction]:
    """Each measure's length in whole notes, from its own notes, backups and forwards."""
    lengths: list[Fraction] = []
    divisions = 1
    for measure in part.findall("measure"):
        cursor = longest = Fraction(0)
        for child in measure:
            if child.tag == "attributes" and child.findtext("divisions"):
                divisions = int(child.findtext("divisions"))
            elif child.tag == "note":
                if child.find("chord") is None and child.find("grace") is None:
                    cursor += _duration_of(child, divisions)
            elif child.tag == "backup":
                cursor -= _duration_of(child, divisions)
            elif child.tag == "forward":
                cursor += _duration_of(child, divisions)
            longest = max(longest, cursor)
        lengths.append(longest)
    return lengths


def _duration_of(element: ET.Element, divisions: int) -> Fraction:
    text = element.findtext("duration")
    return Fraction(int(text), divisions * 4) if text else Fraction(0)


# --- lines under construction ---------------------------------------------------------------


@dataclass(order=True)
class _Placed:
    position: Fraction
    rank: int
    order: int
    event: SequentialEvent = field(compare=False)


def _length(event: SequentialEvent) -> Fraction:
    duration = event.duration
    return duration.rational_length if isinstance(duration, Measurable) else Fraction(0)


class _LineBuilder:
    """The events of one line with where each starts, sorted and gap-filled
    at the end, then indexed by onset so directions can find their events."""

    def __init__(self, staff: int, voice: str | None, name: str | None = None):
        self.staff = staff
        self.voice = voice
        self.name = name
        self.items: list[_Placed] = []
        self.divisions: list[tuple[Fraction, DivisionEvent]] = []
        self.head_meta: dict = {}
        self.events: list[SequentialEvent] = []
        self.onsets: list[Fraction] = []
        self.ends: dict[Fraction, SequentialEvent] = {}
        self.division_at: dict[Fraction, DivisionEvent] = {}

    def add(self, position: Fraction, rank: int, order: int, event: SequentialEvent) -> None:
        self.items.append(_Placed(position, rank, order, event))
        if isinstance(event, DivisionEvent):
            self.divisions.append((position, event))
            self.division_at[position] = event

    def finalize(self, total: Fraction) -> list[SequentialEvent]:
        self.items.sort()
        events: list[SequentialEvent] = []
        cursor = Fraction(0)
        for placed in self.items:
            if placed.position > cursor:
                events.append(_filler(placed.position - cursor))
                cursor = placed.position
            events.append(placed.event)
            cursor = max(cursor, placed.position + _length(placed.event))
        if total > cursor:
            events.append(_filler(total - cursor))
        self.events = events
        position = Fraction(0)
        for event in events:
            self.onsets.append(position)
            length = _length(event)
            if length:
                self.ends[position + length] = event
            position += length
        return events

    @property
    def head(self) -> SequentialEvent:
        return self.events[0]

    def at(self, position: Fraction) -> SequentialEvent | None:
        """The event starting at `position`: a sounding note over a grace, a
        note over a context or division; None if nothing starts there."""
        first = bisect_left(self.onsets, position)
        candidates = []
        for index in range(first, len(self.onsets)):
            if self.onsets[index] != position:
                break
            candidates.append(self.events[index])
        for event in candidates:
            if isinstance(event, NoteEvent) and _length(event):
                return event
        for event in candidates:
            if isinstance(event, NoteEvent):
                return event
        return candidates[0] if candidates else None

    def ending_at(self, position: Fraction) -> SequentialEvent | None:
        return self.ends.get(position)

    def containing(self, position: Fraction) -> tuple[SequentialEvent, Fraction] | None:
        """The sounding event under `position`, with its onset."""
        index = bisect_right(self.onsets, position) - 1
        while index >= 0:
            event, onset = self.events[index], self.onsets[index]
            length = _length(event)
            if length and onset <= position < onset + length:
                return event, onset
            if onset + length < position and length:
                return None
            index -= 1
        return None

    def anchor(self, position: Fraction) -> tuple[SequentialEvent, Fraction]:
        """An event at `position`, or the one under it with the displacement to it."""
        event = self.at(position)
        if event is not None:
            return event, Fraction(0)
        found = self.containing(position)
        if found is not None:
            event, onset = found
            return event, position - onset
        return self.events[-1], position - self.onsets[-1]


def _filler(length: Fraction) -> NoteEvent:
    """A stretch the file says nothing about: unspecified content, not a rest."""
    event = NoteEvent(tones=set(), duration=MetricalDuration.from_length(length))
    xml_meta(event)["forward"] = True
    return event


class _Run:
    """A contiguous run of one voice number: the events of a branched line."""

    def __init__(self, staff: int, voice: str, start: Fraction):
        self.staff = staff
        self.voice = voice
        self.start = start
        self.end = start
        self.events: list[SequentialEvent] = []
        self.pending_division: DivisionEvent | None = None

    def append(self, event: SequentialEvent) -> None:
        if self.pending_division is not None:
            self.events.append(self.pending_division)
            self.pending_division = None
        self.events.append(event)
        self.end += _length(event)


# --- one <note> and its tones ------------------------------------------------------------------


@dataclass
class _ToneData:
    tone: TonalVector | None  # None for a rest or an unpitched hit
    tie_start: bool = False
    tie_stop: bool = False
    marks: list[Mark] = field(default_factory=list)  # per-tone marks (fingering, string...)
    mark_meta: list[dict] = field(default_factory=list)
    instrument: str | None = None
    display: tuple[str, str] | None = None
    notehead: str | None = None
    written: tuple[str, str, str] | None = None  # step, alter, octave of a slash note

    def signature(self) -> tuple:
        return (self.tie_start, self.tie_stop, tuple(sorted(m.name for m in self.marks)))


@dataclass
class _Span:
    kind: str
    number: str
    type: str
    mark: Mark | None
    meta: dict = field(default_factory=dict)


@dataclass
class _LyricData:
    key: str
    name: str | None
    language: str | None
    syllables: list[tuple[str, str | None]]
    meta: dict


@dataclass
class _NoteData:
    onset: Fraction
    order: int
    staff: int
    voice: str
    duration: Duration
    rest: bool
    grace: bool
    tones: list[_ToneData]
    marks: list[Mark] = field(default_factory=list)  # chord-level marks
    mark_meta: list[dict] = field(default_factory=list)
    spans: list[_Span] = field(default_factory=list)
    lyrics: list[_LyricData] = field(default_factory=list)
    meta: dict = field(default_factory=dict)
    slash: bool = False


@dataclass
class _DirectionSpan:
    kind: str
    number: str
    staff: int
    position: Fraction
    order: int
    start: bool
    mark: Mark | None = None
    meta: dict = field(default_factory=dict)
    expected_open: bool = False


@dataclass
class _PointMark:
    position: Fraction
    staff: int
    mark: Mark
    at_end: bool = False
    on_division: bool = False
    meta: dict = field(default_factory=dict)


# --- one <part> --------------------------------------------------------------------------------


class _PartReader:
    def __init__(
        self, reader: _Reader, info: _PartInfo, element: ET.Element, lengths: list[Fraction]
    ):
        self.reader = reader
        self.graph = reader.graph
        self.info = info
        self.element = element
        self.lengths = lengths
        self.starts: list[Fraction] = []
        total = Fraction(0)
        for length in lengths:
            self.starts.append(total)
            total += length
        self.total = total
        self.order = 0
        self.divisions_value = 1
        self.cursor = Fraction(0)
        self.measure_index = 0
        self.measure_start = Fraction(0)
        self.measure_number = ""
        self.lines: dict[int, _LineBuilder] = {}
        self.kit_lines: dict[str, _LineBuilder] = {}
        self.kit = False
        self.n_staves = 1
        self.main_voice: dict[int, str] = {}
        self.hidden_staves: set[int] = set()
        self.transpose: dict[int, TonalVector] = {}
        self.runs: list[_Run] = []
        self.open_runs: dict[tuple[int, str], _Run] = {}
        self.splits: list[tuple[NoteEvent, NoteEvent]] = []
        self.marks: list[tuple[Marking, SequentialEvent]] = []
        self.spanners: list[tuple[MarkSpanner, SequentialEvent, SequentialEvent | None]] = []
        self.open_ties: dict[tuple[int, TonalVector], NoteEvent] = {}
        self.last_tie_start: dict[tuple[int, TonalVector], NoteEvent] = {}
        self.open_spans: dict[tuple[str, str], list[tuple[NoteEvent, Mark | None, dict]]] = (
            defaultdict(list)
        )
        self.direction_spans: list[_DirectionSpan] = []
        self.point_marks: list[_PointMark] = []
        self.harmonies: list[tuple[Fraction, int, ChordEvent]] = []
        self.lyric_lines: dict[tuple[int, str, str], list] = defaultdict(list)
        self.lyric_info: dict[tuple[int, str, str], tuple[str | None, str | None]] = {}
        self.tempos: dict[Fraction, dict[int, TempoEvent]] = defaultdict(dict)
        self.kit_contexts: list[tuple[Fraction, int, Callable[[], ContextEvent]]] = []
        self.sound_tempos: list[tuple[Fraction, int, str]] = []
        self.endings: list[dict] = []
        self.open_ending: dict | None = None
        self.measure_repeat: dict | None = None
        self.last_note: _NoteData | None = None
        self.end_divisions: list[DivisionEvent] = []
        self.boundaries: list[tuple[Fraction, int, object, dict]] = []
        self.right_shape = None
        self.right_marks: list[Mark] = []
        self.measure_meta: dict = {}
        self.counts: Counter[str] = Counter()

    # -- helpers

    def warn(self, message: str) -> None:
        self.reader.warn(f"part {self.info.name!r}, measure {self.measure_number}: {message}")

    def count(self, what: str) -> None:
        self.counts[what] += 1

    def next_order(self) -> int:
        self.order += 1
        return self.order

    def position(self) -> Fraction:
        return self.measure_start + self.cursor

    def duration_of(self, element: ET.Element) -> Fraction:
        return _duration_of(element, self.divisions_value)

    def line_for(self, staff: int) -> _LineBuilder:
        if self.kit:
            return self.kit_line(next(iter(self.kit_lines)) if self.kit_lines else "")
        return self.lines[staff]

    def kit_line(self, instrument: str) -> _LineBuilder:
        """The line of one kit instrument, made at its first stroke with the
        contexts and bar lines of the measures already read."""
        line = self.kit_lines.get(instrument)
        if line is None:
            name = self.info.instruments.get(instrument) or self.info.name
            line = self.kit_lines[instrument] = _LineBuilder(1, None, name)
            for position, order, make in self.kit_contexts:
                line.add(position, _CONTEXT, order, make())
            for position, order, shape, meta in self.boundaries:
                division = DivisionEvent(shape=shape)
                xml_meta(division).update(meta)
                line.add(position, _DIVISION, order, division)
        return line

    def all_lines(self) -> list[_LineBuilder]:
        return list(self.kit_lines.values()) if self.kit else list(self.lines.values())

    def add_context(self, staffs: list[int], make: Callable[[], ContextEvent]) -> None:
        """A context event on each of `staffs`' main lines (every line of a kit)."""
        position, order = self.position(), self.next_order()
        if self.kit:
            self.kit_contexts.append((position, order, make))
            for line in self.kit_lines.values():
                line.add(position, _CONTEXT, order, make())
            return
        for staff in staffs:
            self.lines[staff].add(position, _CONTEXT, order, make())

    # -- the part

    def build(self) -> list[tuple[SequentialEvent, list[tuple[Fraction, DivisionEvent]]]]:
        self.prescan()
        for index, measure in enumerate(self.element.findall("measure")):
            self.read_measure(index, measure)
        return self.finish()

    def prescan(self) -> None:
        staves = [int(s.text) for s in self.element.iter("staves") if s.text]
        self.n_staves = max(staves) if staves else 1
        voices: dict[int, set[str]] = defaultdict(set)
        for note in self.element.iter("note"):
            if note.find("unpitched") is not None:
                self.kit = True
            staff = int(note.findtext("staff") or 1)
            voices[staff].add(note.findtext("voice") or "1")
        for staff in range(1, self.n_staves + 1):
            found = voices.get(staff) or {"1"}
            self.main_voice[staff] = min(found, key=_voice_key)
            self.lines[staff] = _LineBuilder(staff, self.main_voice[staff])
        for details in self.element.iter("staff-details"):
            if details.get("print-object") == "no":
                self.hidden_staves.add(int(details.get("number") or 1))

    def read_measure(self, index: int, measure: ET.Element) -> None:
        self.measure_index = index
        self.measure_start = self.starts[index]
        self.measure_number = measure.get("number") or str(index + 1)
        self.cursor = Fraction(0)
        self.right_shape = None
        self.right_marks = []
        self.measure_meta = {}
        for child in measure:
            if child.tag != "note":
                self.flush_note()
            match child.tag:
                case "attributes":
                    self.read_attributes(child)
                case "note":
                    self.read_note(child)
                case "backup":
                    self.cursor -= self.duration_of(child)
                case "forward":
                    self.cursor += self.duration_of(child)
                case "direction":
                    self.read_direction(child)
                case "harmony":
                    self.read_harmony(child)
                case "barline":
                    self.read_barline(child)
                case "sound":
                    self.read_sound(child, self.position(), 1)
                case "figured-bass":
                    self.count("figured-bass")
                case _:
                    pass  # print, bookmark, link, grouping, listening: presentation
        self.flush_note()
        self.end_measure(measure)

    # -- attributes

    def read_attributes(self, attributes: ET.Element) -> None:
        if attributes.findtext("divisions"):
            self.divisions_value = int(attributes.findtext("divisions"))
        for key in attributes.findall("key"):
            self.read_key(key)
        for time in attributes.findall("time"):
            self.read_time(time)
        for clef in attributes.findall("clef"):
            self.read_clef(clef)
        for transpose in attributes.findall("transpose"):
            self.read_transpose(transpose)
        for style in attributes.findall("measure-style"):
            self.read_measure_style(style)

    def staffs_of(self, element: ET.Element, default_all: bool) -> list[int]:
        number = element.get("number")
        if number:
            return [int(number)]
        return list(range(1, self.n_staves + 1)) if default_all else [1]

    def read_key(self, key: ET.Element) -> None:
        if key.find("fifths") is None:
            self.warn("a non-traditional <key> (key-step/key-alter) is not modelled; skipped")
            return
        fifths = int(key.findtext("fifths"))
        mode = (key.findtext("mode") or "").strip().lower()
        signature = KeySignature.from_alts(fifths)
        if mode in tables.MODES:
            tonic = C
            step = P5 if fifths > 0 else P4  # a fifth down is a fourth up, octaves aside
            for _ in range(abs(fifths)):
                tonic = tonic + step
            degree = tables.MODE_TONIC_DEGREE[mode]
            tonic = tonic + TonalVector((degree, tables.STEP_CHROMATIC[degree]))
            context = Key.of(tonic, tables.MODES[mode], signature=signature)
        else:
            context = Key.from_signature(signature)
        self.add_context(
            self.staffs_of(key, True), lambda: ModalContextEvent(modal_context=context)
        )

    def read_time(self, time: ET.Element) -> None:
        if time.find("senza-misura") is not None:
            meter = None
        else:
            beats = [b.text.strip() for b in time.findall("beats") if b.text]
            types = [t.text.strip() for t in time.findall("beat-type") if t.text]
            units = []
            for numerator, denominator in zip(beats, types, strict=False):
                base = MetricalDuration(1, int(denominator))
                units.extend(TemporalUnit(int(part), base) for part in numerator.split("+"))
            if not units:
                self.warn("a <time> with no beats; skipped")
                return
            meter = TimeSignature(units, presentation=("+".join(beats), "+".join(types)))
        symbol = time.get("symbol")

        def make() -> MeterEvent:
            event = MeterEvent(meter=meter)
            if symbol:
                xml_meta(event)["symbol"] = symbol
            if meter is None:
                xml_meta(event)["senza_misura"] = True
            return event

        self.add_context(self.staffs_of(time, True), make)

    def read_clef(self, clef: ET.Element) -> None:
        sign = (clef.findtext("sign") or "").strip()
        if sign not in tables.CLEF_SIGNS:
            self.warn(f"clef sign {sign!r} is not modelled; skipped")
            return
        clef_sign = tables.CLEF_SIGNS[sign]
        line = clef.findtext("line")
        line_number = (
            int(line) if line and clef_sign in (ClefSign.G, ClefSign.F, ClefSign.C) else None
        )
        if line_number is None and clef_sign in (ClefSign.G, ClefSign.F, ClefSign.C):
            line_number = {ClefSign.G: 2, ClefSign.F: 4, ClefSign.C: 3}[clef_sign]
        octave = int(clef.findtext("clef-octave-change") or 0)
        value = StaffClef(clef_sign, line_number, octave_change=octave)
        self.add_context(self.staffs_of(clef, False), lambda: ClefEvent(clef=value))

    def read_transpose(self, transpose: ET.Element) -> None:
        diatonic = int(transpose.findtext("diatonic") or 0)
        chromatic = int(transpose.findtext("chromatic") or 0)
        octave = int(transpose.findtext("octave-change") or 0)
        interval = _interval(diatonic, chromatic, octave)
        for staff in self.staffs_of(transpose, True):
            if staff in self.transpose and self.transpose[staff] != interval:
                self.warn("the transposition changes mid-part; the new one applies from here")
            self.transpose[staff] = interval

    def read_measure_style(self, style: ET.Element) -> None:
        for child in style:
            match child.tag:
                case "measure-repeat":
                    if child.get("type") == "start":
                        self.measure_repeat = {
                            "slashes": child.get("slashes"),
                            "measures": (child.text or "").strip() or "1",
                        }
                        self.count(
                            "measure-repeat (%) bars recorded as unspecified content with a "
                            "simile mark (control flow is not modelled)"
                        )
                    else:
                        self.measure_repeat = None
                case "multiple-rest":
                    self.measure_meta["multiple_rest"] = int(child.text or 1)
                case "slash":
                    self.measure_meta["slash"] = child.get("type")
                    self.count("slash")
                case _:
                    pass

    # -- notes

    def read_note(self, note: ET.Element) -> None:
        data = self.parse_note(note)
        if data is None:
            return
        if note.find("chord") is not None and self.last_note is not None:
            self.last_note.tones.extend(data.tones)
            self.last_note.marks.extend(m for m in data.marks if m not in self.last_note.marks)
            self.last_note.mark_meta.extend(data.mark_meta)
            self.last_note.spans.extend(data.spans)
            self.last_note.lyrics.extend(data.lyrics)
            return
        self.flush_note()
        self.last_note = data
        if not data.grace:
            self.cursor += self.duration_of(note)

    def parse_note(self, note: ET.Element) -> _NoteData | None:
        grace = note.find("grace")
        rest = note.find("rest")
        pitch = note.find("pitch")
        unpitched = note.find("unpitched")
        staff = int(note.findtext("staff") or 1)
        voice = note.findtext("voice") or self.main_voice.get(staff, "1")
        note_type = (note.findtext("type") or "").strip()
        dots = len(note.findall("dot"))
        file_length = self.duration_of(note) if grace is None else None
        if note.find("chord") is not None and self.last_note is not None:
            duration = self.last_note.duration  # a chord note's own value is not consulted
        else:
            duration = self.note_duration(note, note_type, dots, grace, rest, file_length)
        if duration is None:
            return None
        tone = _ToneData(tone=None)
        if pitch is not None:
            tone.tone = self.read_pitch(pitch, staff)
        elif unpitched is not None:
            tone.tone = hit
            tone.display = (
                (unpitched.findtext("display-step") or "").strip(),
                (unpitched.findtext("display-octave") or "").strip(),
            )
        instrument = note.find("instrument")
        if instrument is not None and len(self.info.instruments) > 1:
            tone.instrument = instrument.get("id")
        notehead = note.find("notehead")
        if notehead is not None and (notehead.text or "").strip():
            tone.notehead = notehead.text.strip()
        data = _NoteData(
            onset=self.position(),
            order=self.next_order(),
            staff=staff,
            voice=voice,
            duration=duration,
            rest=rest is not None,
            grace=grace is not None,
            tones=[tone],
        )
        if note.get("print-object") == "no":
            data.meta["hidden"] = True
        if note.find("cue") is not None:
            data.meta["cue"] = True
        if tone.notehead == "slash" and pitch is not None:
            data.slash = True
            tone.written = (
                (pitch.findtext("step") or "").strip(),
                (pitch.findtext("alter") or "0").strip(),
                (pitch.findtext("octave") or "").strip(),
            )
        for tie in note.findall("tie"):
            self.read_tie(tie.get("type"), tone)
        for notations in note.findall("notations"):
            self.read_notations(notations, data, tone)
        for lyric in note.findall("lyric"):
            data.lyrics.append(self.read_lyric(lyric))
        return data

    def note_duration(
        self,
        note: ET.Element,
        note_type: str,
        dots: int,
        grace: ET.Element | None,
        rest: ET.Element | None,
        file_length: Fraction | None,
    ) -> Duration | None:
        if grace is not None:
            numerator, denominator = tables.NOTE_TYPES.get(note_type, (1, 8))
            nominal = MetricalDuration(numerator, denominator, dots)
            return GraceDuration(nominal, on_beat=grace.get("slash") != "yes")
        whole_measure = rest is not None and rest.get("measure") == "yes"
        if note_type not in tables.NOTE_TYPES or whole_measure:
            if not file_length:
                self.warn("a note with neither a <type> nor a <duration>; skipped")
                return None
            if note_type and note_type not in tables.NOTE_TYPES:
                self.warn(f"note type {note_type!r} is not known; its <duration> is used")
            return MetricalDuration.from_length(file_length)
        numerator, denominator = tables.NOTE_TYPES[note_type]
        ratio = self.time_modification(note, denominator)
        duration = MetricalDuration(numerator, denominator, dots, ratio=ratio)
        if file_length is not None and duration.rational_length != file_length:
            if rest is not None:
                # a whole rest in a short bar: the symbol is conventional, the duration is the fact
                self.count("rests whose <type> and <duration> disagree (the <duration> is used)")
                return MetricalDuration.from_length(file_length)
            self.warn(
                f"a {note_type} with {dots} dot(s) is notated as {duration.rational_length} "
                f"whole notes but its <duration> says {file_length}; the notated value is used"
            )
        return duration

    def time_modification(self, note: ET.Element, denominator: int) -> TemporalRatio | None:
        modification = note.find("time-modification")
        if modification is None:
            return None
        actual = int(modification.findtext("actual-notes"))
        normal = int(modification.findtext("normal-notes"))
        normal_type = (modification.findtext("normal-type") or "").strip()
        normal_dots = len(modification.findall("normal-dot"))
        if normal_type in tables.NOTE_TYPES:
            base_numerator, base_denominator = tables.NOTE_TYPES[normal_type]
        else:
            base_numerator, base_denominator = 1, denominator
        base = MetricalDuration(base_numerator, base_denominator, normal_dots)
        return TemporalRatio(TemporalUnit(actual, base), TemporalUnit(normal, base))

    def read_pitch(self, pitch: ET.Element, staff: int) -> TonalVector:
        step = (pitch.findtext("step") or "C").strip().upper()
        alter_text = (pitch.findtext("alter") or "0").strip()
        alter = Fraction(alter_text)
        if alter.denominator != 1:
            self.warn(f"a microtonal <alter> of {alter_text} is rounded to the nearest semitone")
            alter = Fraction(round(alter))
        octave = int(pitch.findtext("octave") or 4)
        tone = tables.tone_from_pitch(step, int(alter), octave)
        interval = self.transpose.get(staff)
        return tone.transpose(interval) if interval is not None else tone

    def read_tie(self, kind: str | None, tone: _ToneData) -> None:
        if kind == "start":
            tone.tie_start = True
        elif kind == "stop":
            tone.tie_stop = True
        elif kind == "continue":
            tone.tie_start = tone.tie_stop = True

    def read_notations(self, notations: ET.Element, data: _NoteData, tone: _ToneData) -> None:
        for child in notations:
            match child.tag:
                case "tied":
                    if child.get("type") == "let-ring":
                        data.marks.append(scoring.laissez_vibrer)
                    else:
                        self.read_tie(child.get("type"), tone)
                case "slur" | "glissando" | "slide":
                    meta = {}
                    if child.tag != "slur" and (child.text or "").strip():
                        meta["text"] = child.text.strip()
                    data.spans.append(
                        _Span(
                            child.tag,
                            child.get("number", "1"),
                            child.get("type", "start"),
                            tables.NOTATION_SPANS[child.tag],
                            meta,
                        )
                    )
                case "tuplet":
                    data.meta.setdefault("tuplet", []).append(
                        {
                            k: v
                            for k, v in child.attrib.items()
                            if k in ("type", "number", "bracket", "show-number", "show-type")
                        }
                    )
                case "articulations":
                    for item in child:
                        self.read_articulation(item, data)
                case "ornaments":
                    self.read_ornaments(child, data)
                case "technical":
                    for item in child:
                        self.read_technical(item, data, tone)
                case "dynamics":
                    for item in child:
                        mark = self.dynamic_mark(item)
                        if mark is not None:
                            data.marks.append(mark)
                            data.mark_meta.append({})
                case "fermata":
                    shape = (child.text or "").strip()
                    mark = tables.FERMATAS.get(shape)
                    if mark is None:
                        mark = Mark(name=f"fermata ({shape})", kind=MarkType.PHRASING)
                        self.count(f"minted mark {mark.name!r}")
                    data.marks.append(mark)
                    data.mark_meta.append(
                        {"fermata_type": child.get("type")} if child.get("type") else {}
                    )
                case "arpeggiate":
                    data.marks.append(
                        tables.ARPEGGIOS.get(child.get("direction"), scoring.arpeggio)
                    )
                    data.mark_meta.append({})
                case "non-arpeggiate":
                    data.marks.append(scoring.non_arpeggio)
                    data.mark_meta.append({})
                case "accidental-mark":
                    data.meta["accidental_mark"] = (child.text or "").strip()
                case "other-notation":
                    text = (child.text or "").strip() or "other-notation"
                    data.marks.append(self.minted(text, MarkType.OTHER, "other-notation"))
                    data.mark_meta.append({"element": "other-notation"})
                case _:
                    pass

    def read_articulation(self, item: ET.Element, data: _NoteData) -> None:
        text = (item.text or "").strip()
        if item.tag == "breath-mark":
            mark = tables.BREATH_MARKS.get(text, scoring.breath_mark)
        elif item.tag == "caesura":
            mark = scoring.caesura
        elif item.tag == "other-articulation":
            mark = tables.WORDS.get(tables.normalize_words(text)) or self.minted(
                text or "other-articulation", MarkType.ARTICULATION, "other-articulation"
            )
        else:
            mark = tables.ARTICULATIONS.get(item.tag)
            if mark is None:
                mark = self.minted(item.tag, MarkType.ARTICULATION, item.tag)
        data.marks.append(mark)
        data.mark_meta.append({})

    def read_ornaments(self, ornaments: ET.Element, data: _NoteData) -> None:
        for item in ornaments:
            text = (item.text or "").strip()
            if item.tag == "accidental-mark":
                if data.mark_meta:
                    data.mark_meta[-1]["accidental_mark"] = text
                continue
            if item.tag == "tremolo":
                kind = item.get("type", "single")
                meta = {"tremolo": text or None, "tremolo_type": kind}
                if kind == "single" or kind == "unmeasured":
                    data.marks.append(scoring.tremolo)
                    data.mark_meta.append(meta)
                else:
                    data.spans.append(_Span("tremolo", "1", kind, scoring.tremolo, meta))
                continue
            if item.tag == "wavy-line":
                data.spans.append(
                    _Span(
                        "wavy-line",
                        item.get("number", "1"),
                        item.get("type", "start"),
                        scoring.wavy_line,
                    )
                )
                continue
            if item.tag == "other-ornament":
                mark = tables.WORDS.get(tables.normalize_words(text)) or self.minted(
                    text or "other-ornament", MarkType.ORNAMENT, "other-ornament"
                )
            else:
                mark = tables.ORNAMENTS.get(item.tag) or self.minted(
                    item.tag, MarkType.ORNAMENT, item.tag
                )
            data.marks.append(mark)
            data.mark_meta.append({})

    def read_technical(self, item: ET.Element, data: _NoteData, tone: _ToneData) -> None:
        text = (item.text or "").strip()
        meta: dict = {}
        match item.tag:
            case "fingering":
                mark = tables.FINGERINGS.get(text)
                if mark is None:
                    mark = self.minted(f"fingering {text}", MarkType.FINGERING, "fingering")
                    meta["fingering"] = text
            case "string":
                mark = tables.STRINGS.get(text) or self.minted(
                    f"string {text}", MarkType.FINGERING, "string"
                )
            case "fret":
                mark = self.minted(f"fret {text}", MarkType.FINGERING, "fret")
            case "pluck":
                mark = tables.PLUCKS.get(text) or self.minted(
                    f"pluck {text}", MarkType.FINGERING, "pluck"
                )
            case "handbell":
                mark = tables.HANDBELLS.get(text) or self.minted(
                    text or "handbell", MarkType.TECHNIQUE, "handbell"
                )
            case "harmon-mute":
                mark = tables.HARMON_MUTES.get((item.findtext("harmon-closed") or "yes").strip())
            case "hole":
                mark = tables.HOLES.get((item.findtext("hole-closed") or "yes").strip())
            case "other-technical":
                mark = tables.WORDS.get(tables.normalize_words(text)) or self.minted(
                    text or "other-technical", MarkType.TECHNIQUE, "other-technical"
                )
            case "arrow":
                mark = self.minted("arrow", MarkType.TECHNIQUE, "arrow")
            case _:
                mark = tables.TECHNICAL.get(item.tag) or self.minted(
                    item.tag, MarkType.TECHNIQUE, item.tag
                )
        if item.get("type") in ("start", "stop"):
            meta["type"] = item.get("type")
        if item.tag in tables.PER_TONE_TECHNICAL:
            tone.marks.append(mark)
            tone.mark_meta.append(meta)
        else:
            data.marks.append(mark)
            data.mark_meta.append(meta)

    def dynamic_mark(self, item: ET.Element) -> Mark | None:
        if item.tag == "other-dynamics":
            text = (item.text or "").strip()
            if not text:
                return None
            return tables.WORDS.get(tables.normalize_words(text)) or self.minted(
                text, MarkType.EXPRESSION, "other-dynamics"
            )
        return tables.DYNAMICS.get(item.tag) or self.minted(item.tag, MarkType.DYNAMIC, item.tag)

    def minted(self, name: str, kind: MarkType, element: str) -> Mark:
        """A mark for a name the tables do not know: the file's word, kept."""
        self.count(f"minted mark {name!r} from <{element}>")
        return Mark(name=name, kind=kind)

    def read_lyric(self, lyric: ET.Element) -> _LyricData:
        number = lyric.get("number") or "1"
        syllables: list[tuple[str, str | None]] = []
        syllabic: str | None = None
        meta: dict = {}
        for child in lyric:
            match child.tag:
                case "syllabic":
                    syllabic = (child.text or "").strip() or None
                case "text":
                    text = child.text or ""
                    if text.strip():
                        syllables.append((text, syllabic))
                    else:
                        meta["blank"] = True  # Sibelius marks a melisma with a blank syllable
                    syllabic = None
                case "extend":
                    meta["extend"] = child.get("type") or "start"
                case "elision":
                    pass
                case "humming" | "laughing" | "end-line" | "end-paragraph":
                    meta[child.tag.replace("-", "_")] = True
                case _:
                    pass
        return _LyricData(
            key=number,
            name=lyric.get("name"),
            language=lyric.get(XML_LANG),
            syllables=syllables,
            meta=meta,
        )

    def flush_note(self) -> None:
        data, self.last_note = self.last_note, None
        if data is None or self.measure_repeat is not None:
            return
        if self.kit:
            self.place_kit_note(data)
        elif data.rest:
            event = Rest(data.duration)
            self.apply_meta(event, data.meta)
            self.attach_chord_level(event, data)
            self.place(event, data)
        else:
            self.place_pitched_note(data)

    def place_kit_note(self, data: _NoteData) -> None:
        if data.rest:
            return  # a rest in a kit staff belongs to a voice, not to any instrument
        first: NoteEvent | None = None
        for tone in data.tones:
            event = NoteEvent(tones={hit}, duration=data.duration)
            meta = xml_meta(event)
            meta["voice"] = data.voice
            if tone.display:
                meta["display"] = list(tone.display)
            if tone.notehead:
                meta["notehead"] = tone.notehead
            if tone.instrument:
                meta["instrument"] = tone.instrument
            self.apply_meta(event, data.meta)
            self.kit_line(tone.instrument or "").add(data.onset, _NOTE, data.order, event)
            for mark, mark_meta in zip(tone.marks, tone.mark_meta, strict=False):
                self.add_mark(mark, event, mark_meta)
            if first is None:
                first = event
        if first is not None:
            self.attach_chord_level(first, data)

    def place_pitched_note(self, data: _NoteData) -> None:
        classes: dict[tuple, list[_ToneData]] = defaultdict(list)
        for tone in data.tones:
            classes[tone.signature()].append(tone)
        ordered = sorted(
            classes.values(), key=lambda group: (-len(group), min(t.tone for t in group))
        )
        placed: list[tuple[list[_ToneData], NoteEvent]] = []
        main = self.make_event(ordered[0], data)
        self.attach_chord_level(main, data)
        self.place(main, data)
        placed.append((ordered[0], main))
        for group in ordered[1:]:
            event = self.make_event(group, data)
            self.splits.append((main, event))
            placed.append((group, event))
        at_bar_start = data.onset == self.measure_start
        for group, event in placed:
            for tone in group:
                self.resolve_ties(tone, event, data.staff, at_bar_start)
                for mark, mark_meta in zip(tone.marks, tone.mark_meta, strict=False):
                    self.add_mark(mark, event, mark_meta)

    def make_event(self, tones: list[_ToneData], data: _NoteData) -> NoteEvent:
        if data.slash:
            event = NoteEvent(tones=set(), duration=data.duration)
            xml_meta(event)["slash_pitch"] = [list(t.written) for t in tones if t.written]
        else:
            event = NoteEvent(tones={t.tone for t in tones}, duration=data.duration)
        self.apply_meta(event, data.meta)
        noteheads = {t.notehead for t in tones if t.notehead and t.notehead != "slash"}
        if noteheads:
            xml_meta(event)["notehead"] = sorted(noteheads)[0]
        instruments = {t.instrument for t in tones if t.instrument}
        if instruments:
            xml_meta(event)["instrument"] = sorted(instruments)[0]
        return event

    @staticmethod
    def apply_meta(event: OmkObject, meta: dict) -> None:
        if meta:
            xml_meta(event).update(meta)

    def attach_chord_level(self, event: NoteEvent, data: _NoteData) -> None:
        for mark, meta in zip(data.marks, data.mark_meta, strict=False):
            self.add_mark(mark, event, meta)
        for span in data.spans:
            self.notation_span(span, event)
        for lyric in data.lyrics:
            key = (data.staff, data.voice, lyric.key)
            self.lyric_lines[key].append((data.onset, data.order, event, lyric))
            if key not in self.lyric_info or self.lyric_info[key] == (None, None):
                self.lyric_info[key] = (lyric.name, lyric.language)

    def add_mark(self, mark: Mark, event: SequentialEvent, meta: dict | None = None) -> None:
        if mark.attachment_mode is AttachmentMode.SPAN:
            marking = Marking(mark=Mark(name=mark.name, kind=mark.kind))
        else:
            marking = Marking(mark=mark)
        if meta:
            xml_meta(marking).update({k: v for k, v in meta.items() if v is not None})
        self.marks.append((marking, event))

    def resolve_ties(
        self, tone: _ToneData, event: NoteEvent, staff: int, at_bar_start: bool
    ) -> None:
        if tone.tone is None:
            return
        key = (staff, tone.tone)
        if tone.tie_stop:
            start = self.open_ties.pop(key, None)
            if start is None and at_bar_start and key in self.last_tie_start:
                # a tie into the first note of a bar with no start before it: the
                # note before a repeat or a first ending is tied into this ending too
                start = self.last_tie_start[key]
                self.count("ties with one start and two ends (into both endings of a repeat)")
            if start is None:
                self.warn(f"a tie ends on {tone.tone.pitch.unicode} with no tie into it; ignored")
            else:
                self.spanners.append((MarkSpanner(mark=scoring.tie), start, event))
        if tone.tie_start:
            if key in self.open_ties:
                self.warn(f"a tie from {tone.tone.pitch.unicode} was never ended; replaced")
            self.open_ties[key] = event
            self.last_tie_start[key] = event

    def notation_span(self, span: _Span, event: NoteEvent) -> None:
        """Starts and stops of one kind and number pair off innermost first,
        so nested slurs that share a number (Sibelius reuses them) still close."""
        key = (span.kind, span.number)
        if span.type == "start":
            self.open_spans[key].append((event, span.mark, span.meta))
        elif span.type == "stop":
            if not self.open_spans[key]:
                self.warn(f"a {span.kind} {span.number} stops with no start; ignored")
                return
            self.close_open_span(key, event)

    def close_open_span(self, key: tuple[str, str], end: NoteEvent | None) -> None:
        start, mark, meta = self.open_spans[key].pop()
        if mark is None or mark.attachment_mode is AttachmentMode.SINGLE:
            marking_meta = dict(meta, tremolo_span="start")
            self.add_mark(mark or Mark(name=key[0], kind=MarkType.OTHER), start, marking_meta)
            if end is not None:
                self.add_mark(
                    mark or Mark(name=key[0], kind=MarkType.OTHER),
                    end,
                    dict(meta, tremolo_span="stop"),
                )
            return
        spanner = MarkSpanner(mark=mark)
        if meta:
            xml_meta(spanner).update(meta)
        self.spanners.append((spanner, start, end))

    def place(self, event: SequentialEvent, data: _NoteData) -> None:
        staff, voice = data.staff, data.voice
        if voice == self.main_voice.get(staff):
            self.lines[staff].add(data.onset, _NOTE, data.order, event)
            return
        run = self.open_runs.get((staff, voice))
        if run is None or run.end != data.onset:
            if run is not None:
                self.close_run(run)
            run = _Run(staff, voice, data.onset)
            self.open_runs[(staff, voice)] = run
        run.append(event)

    def close_run(self, run: _Run) -> None:
        self.open_runs.pop((run.staff, run.voice), None)
        if run.events:
            self.runs.append(run)

    # -- directions, harmony, bar lines

    def read_direction(self, direction: ET.Element) -> None:
        staff = int(direction.findtext("staff") or 1)
        offset = direction.find("offset")
        position = self.position()
        if offset is not None and (offset.text or "").strip():
            position += Fraction(int(Fraction(offset.text.strip())), self.divisions_value * 4)
        order = self.next_order()
        hidden = direction.get("print-object") == "no"
        words: list[str] = []
        elements: list[ET.Element] = []
        for direction_type in direction.findall("direction-type"):
            for element in direction_type:
                if element.tag == "words":
                    text = (element.text or "").strip()
                    if text:
                        words.append(text)
                else:
                    elements.append(element)
        dashes = next((e for e in elements if e.tag in ("dashes", "bracket")), None)
        for element in elements:
            self.read_direction_element(element, position, staff, order, words, hidden)
        if dashes is None or dashes.get("type") != "start":
            for text in words:
                self.read_words(text, position, staff, hidden)
        sound = direction.find("sound")
        if sound is not None:
            self.read_sound(sound, position, staff)

    def read_direction_element(
        self,
        element: ET.Element,
        position: Fraction,
        staff: int,
        order: int,
        words: list[str],
        hidden: bool,
    ) -> None:
        kind = element.get("type")
        number = element.get("number", "1")
        match element.tag:
            case "dynamics":
                for item in element:
                    mark = self.dynamic_mark(item)
                    if mark is not None:
                        self.point_marks.append(_PointMark(position, staff, mark))
            case "wedge":
                if kind == "stop":
                    self.direction_spans.append(
                        _DirectionSpan("wedge", number, staff, position, order, False)
                    )
                else:
                    mark = tables.WEDGES.get(
                        (kind, element.get("niente") == "yes"), scoring.crescendo
                    )
                    self.direction_spans.append(
                        _DirectionSpan("wedge", number, staff, position, order, True, mark)
                    )
            case "dashes" | "bracket":
                if kind == "stop":
                    self.direction_spans.append(
                        _DirectionSpan(element.tag, number, staff, position, order, False)
                    )
                    return
                text = " ".join(words)
                mark = tables.WORDS.get(tables.normalize_words(text)) if text else None
                if mark is not None and mark.attachment_mode is AttachmentMode.SINGLE:
                    mark = Mark(name=mark.name, kind=mark.kind, attachment_mode=AttachmentMode.SPAN)
                if mark is None:
                    kind_of = MarkType.EXPRESSION if element.tag == "dashes" else MarkType.OTHER
                    mark = self.minted(text or element.tag, kind_of, element.tag)
                    mark = Mark(name=mark.name, kind=mark.kind, attachment_mode=AttachmentMode.SPAN)
                meta = {"element": element.tag} if element.tag == "bracket" else {}
                self.direction_spans.append(
                    _DirectionSpan(element.tag, number, staff, position, order, True, mark, meta)
                )
            case "pedal":
                mark = tables.PEDALS["sostenuto" if kind == "sostenuto" else "sustain"]
                meta = {k: v for k, v in element.attrib.items() if k in ("line", "sign")}
                if kind in ("start", "sostenuto", "resume"):
                    self.direction_spans.append(
                        _DirectionSpan("pedal", number, staff, position, order, True, mark, meta)
                    )
                elif kind in ("stop", "discontinue"):
                    self.direction_spans.append(
                        _DirectionSpan("pedal", number, staff, position, order, False)
                    )
                elif kind == "change":
                    self.direction_spans.append(
                        _DirectionSpan("pedal", number, staff, position, order, False)
                    )
                    self.direction_spans.append(
                        _DirectionSpan(
                            "pedal",
                            number,
                            staff,
                            position,
                            self.next_order(),
                            True,
                            mark,
                            dict(meta, change=True),
                        )
                    )
            case "octave-shift":
                if kind == "stop":
                    self.direction_spans.append(
                        _DirectionSpan("octave-shift", number, staff, position, order, False)
                    )
                elif kind in ("up", "down"):
                    size = int(element.get("size", "8"))
                    mark = tables.OCTAVE_SHIFTS.get((kind, size))
                    if mark is None:
                        mark = self.minted(
                            f"octave shift {kind} {size}", MarkType.TRANSPOSITION, "octave-shift"
                        )
                        mark = Mark(
                            name=mark.name, kind=mark.kind, attachment_mode=AttachmentMode.SPAN
                        )
                    self.direction_spans.append(
                        _DirectionSpan("octave-shift", number, staff, position, order, True, mark)
                    )
            case "metronome":
                self.read_metronome(element, position, hidden)
            case "rehearsal":
                text = (element.text or "").strip()
                if text:
                    self.point_marks.append(
                        _PointMark(position, staff, Mark(name=text, kind=MarkType.REHEARSAL))
                    )
            case "segno":
                self.point_marks.append(
                    _PointMark(position, staff, scoring.segno, on_division=True)
                )
            case "coda":
                self.point_marks.append(_PointMark(position, staff, scoring.coda, on_division=True))
            case "eyeglasses":
                self.point_marks.append(_PointMark(position, staff, scoring.eyeglasses))
            case "damp":
                self.point_marks.append(_PointMark(position, staff, scoring.damp))
            case "damp-all":
                self.point_marks.append(_PointMark(position, staff, scoring.damp_all))
            case "string-mute":
                mark = scoring.con_sordino if kind == "on" else scoring.senza_sordino
                self.point_marks.append(_PointMark(position, staff, mark))
            case _:
                pass  # harp-pedals, accordion-registration, image, principal-voice, other-direction ...

    def read_words(self, text: str, position: Fraction, staff: int, hidden: bool) -> None:
        if text == ",":
            self.point_marks.append(_PointMark(position, staff, scoring.breath_mark, at_end=True))
            return
        normalized = tables.normalize_words(text)
        term = tables.TEMPO_TERMS.get(normalized) or tables.TEMPO_TERMS.get(normalized.rstrip("."))
        if term is not None:
            for event in self.tempo_events(position):
                if event.term is None:
                    event.term = term
                if hidden:
                    xml_meta(event)["term_hidden"] = True
            return
        if tables.is_gradual_tempo(text):
            self.count(f"gradual tempo word {text!r} recorded at a point (its span has no end)")
            mark = Mark(name=text, kind=MarkType.EXPRESSION)
            self.point_marks.append(_PointMark(position, staff, mark, meta={"gradual_tempo": True}))
            return
        mark = tables.WORDS.get(normalized)
        if mark is None:
            mark = self.minted(text, MarkType.EXPRESSION, "words")
            self.point_marks.append(_PointMark(position, staff, mark, meta={"element": "words"}))
            return
        if mark is scoring.tre_corde:
            self.direction_spans.append(
                _DirectionSpan("una corda", "1", staff, position, self.next_order(), False)
            )
            return
        if mark is scoring.una_corda:
            self.direction_spans.append(
                _DirectionSpan(
                    "una corda",
                    "1",
                    staff,
                    position,
                    self.next_order(),
                    True,
                    mark,
                    expected_open=True,
                )
            )
            return
        meta = {"hidden": True} if hidden else {}
        self.point_marks.append(_PointMark(position, staff, mark, meta=meta))

    def read_metronome(self, element: ET.Element, position: Fraction, hidden: bool) -> None:
        units = []
        for child in element:
            if child.tag == "beat-unit":
                units.append([(child.text or "quarter").strip(), 0])
            elif child.tag == "beat-unit-dot" and units:
                units[-1][1] += 1
        per_minute = (element.findtext("per-minute") or "").strip()
        if not units:
            return
        beats = [
            MetricalDuration(*tables.NOTE_TYPES.get(name, (1, 4)), dots) for name, dots in units
        ]
        tempo: TemporalRatio | None = None
        meta: dict = {}
        if per_minute:
            try:
                tempo = Tempo(int(per_minute), beats[0])
            except ValueError:
                meta["per_minute"] = per_minute
                self.warn(f"a metronome mark of {per_minute!r} is not a whole number; kept as text")
        elif len(beats) >= 2:
            tempo = TemporalRatio(beats[1], beats[0])
        if element.get("parentheses") == "yes":
            meta["parentheses"] = True
        if hidden:
            meta["tempo_hidden"] = True
        for event in self.tempo_events(position):
            if event.tempo is None:
                event.tempo = tempo
            elif tempo is not None and event.tempo != tempo:
                self.warn("two metronome marks at one position; the first is kept")
            if meta:
                xml_meta(event).update(meta)

    def tempo_events(self, position: Fraction) -> list[TempoEvent]:
        """The TempoEvent at `position` on every line of the part, made on first use."""
        existing = self.tempos[position]
        if existing:
            return list(existing.values())
        saved_cursor = self.cursor
        self.cursor = position - self.measure_start
        made: list[TempoEvent] = []

        def make() -> TempoEvent:
            event = TempoEvent()
            made.append(event)
            return event

        self.add_context(list(range(1, self.n_staves + 1)), make)
        self.cursor = saved_cursor
        if self.kit:
            existing[0] = made[0] if made else TempoEvent()
        else:
            for staff, event in zip(range(1, self.n_staves + 1), made, strict=False):
                existing[staff] = event
        return list(existing.values())

    def read_sound(self, sound: ET.Element, position: Fraction, staff: int) -> None:
        tempo = sound.get("tempo")
        if tempo:
            self.sound_tempos.append((position, staff, tempo))

    def read_harmony(self, harmony: ET.Element) -> None:
        staff = int(harmony.findtext("staff") or 1)
        position = self.position()
        offset = harmony.find("offset")
        if offset is not None and (offset.text or "").strip():
            position += Fraction(int(Fraction(offset.text.strip())), self.divisions_value * 4)
        root = harmony.find("root")
        kind = harmony.find("kind")
        kind_name = (kind.text or "").strip() if kind is not None else ""
        if root is None or kind_name == "none" or kind_name == "":
            self.count("chord symbols with no chord (N.C.) skipped")
            return
        base = tables.KINDS.get(kind_name)
        if base is None:
            self.count(f"chord symbols of kind {kind_name!r} skipped (no ChordType for it)")
            return
        root_tone = _abstract_tone(root.findtext("root-step"), root.findtext("root-alter"))
        chord_type = self.apply_degrees(base, harmony.findall("degree"), kind.get("text"))
        chord = root_tone(chord_type)
        bass = harmony.find("bass")
        if bass is not None:
            bass_tone = _abstract_tone(bass.findtext("bass-step"), bass.findtext("bass-alter"))
            if bass_tone in chord:
                chord = chord.inversion(bass_tone)
            else:
                chord = Chord(
                    chord.root, list(chord), bass=bass_tone, name=chord.name, suffix=chord.suffix
                )
        event = ChordEvent(chord=chord)
        meta = xml_meta(event)
        meta["kind"] = kind_name
        if kind.get("text"):
            meta["kind_text"] = kind.get("text")
        if harmony.find("frame") is not None:
            meta["frame"] = ET.tostring(harmony.find("frame"), encoding="unicode")
        self.harmonies.append((position, staff, event))

    def apply_degrees(
        self, base: ChordType, degrees: list[ET.Element], text: str | None
    ) -> ChordType:
        if not degrees:
            return base
        tones = list(base)
        labels = []
        for degree in degrees:
            value = int(degree.findtext("degree-value") or 0)
            alter = int(degree.findtext("degree-alter") or 0)
            kind = (degree.findtext("degree-type") or "add").strip()
            index = (value - 1) % 7
            tone = TonalVector((index, (tables.STEP_CHROMATIC[index] + alter) % 12))
            if kind == "subtract":
                tones = [t for t in tones if t.d != index]
            elif kind == "alter":
                tones = (
                    [tone if t.d == index else t for t in tones]
                    if any(t.d == index for t in tones)
                    else [*tones, tone]
                )
            else:
                if tone not in tones:
                    tones.append(tone)
            labels.append(f"{kind} {alter:+d}{value}" if alter else f"{kind} {value}")
        name = f"{base.name} ({', '.join(labels)})"
        return ChordType(tones, name=name, quality=base.quality, suffix=text or base.suffix)

    def read_barline(self, barline: ET.Element) -> None:
        location = barline.get("location", "right")
        style = (barline.findtext("bar-style") or "").strip()
        repeat = barline.find("repeat")
        ending = barline.find("ending")
        marks = []
        for child in barline:
            if child.tag == "fermata":
                marks.append(tables.FERMATAS.get((child.text or "").strip(), scoring.fermata))
            elif child.tag == "segno":
                marks.append(scoring.segno)
            elif child.tag == "coda":
                marks.append(scoring.coda)
        if location == "left":
            self.left_barline(style, repeat, ending, marks)
        else:
            self.right_shape = self.shape_of(style, repeat, None)
            self.right_marks.extend(marks)
            if ending is not None and ending.get("type") in ("stop", "discontinue"):
                self.close_ending(ending)

    def shape_of(self, style: str, repeat: ET.Element | None, previous):
        if repeat is not None:
            direction = repeat.get("direction")
            if direction == "forward":
                return (
                    scoring.double_repeat
                    if previous is scoring.end_repeat
                    else scoring.start_repeat
                )
            return scoring.end_repeat
        if style:
            return tables.BAR_STYLES.get(style, scoring.single_bar)
        return previous

    def left_barline(self, style, repeat, ending, marks: list[Mark]) -> None:
        if ending is not None and ending.get("type") == "start":
            self.open_ending = {
                "number": ending.get("number", "1"),
                "text": (ending.text or "").strip() or None,
                "start": self.measure_start,
            }
        if self.measure_index == 0 or not self.end_divisions:
            shape = self.shape_of(style, repeat, None)
            if shape is None and not marks:
                return
            head_divisions = []
            for line in self.all_lines() or [self.lines[1]]:
                division = DivisionEvent(shape=shape)
                xml_meta(division)["left"] = True
                line.add(self.measure_start, _LEFT_BAR, self.next_order(), division)
                head_divisions.append(division)
            for mark in marks:
                self.add_mark(mark, head_divisions[0])
            return
        for division in self.end_divisions:
            division.shape = self.shape_of(style, repeat, division.shape)
            if repeat is not None or style:
                xml_meta(division)["left"] = True
        for mark in marks:
            self.add_mark(mark, self.end_divisions[0])

    def close_ending(self, ending: ET.Element) -> None:
        if self.open_ending is None:
            self.warn("an <ending> stops with no start; ignored")
            return
        record = dict(self.open_ending)
        record["stop"] = self.measure_start + self.lengths[self.measure_index]
        record["type"] = ending.get("type")
        self.endings.append(record)
        self.open_ending = None

    def end_measure(self, measure: ET.Element) -> None:
        boundary = self.measure_start + self.lengths[self.measure_index]
        meta = {"number": self.measure_number}
        if measure.get("implicit") == "yes":
            meta["implicit"] = True
        if measure.get("width"):
            meta["width"] = measure.get("width")
        meta.update(self.measure_meta)
        if self.measure_repeat is not None:
            self.repeat_measure(boundary)
        self.end_divisions = []
        order = self.next_order()
        self.boundaries.append((boundary, order, self.right_shape, dict(meta)))
        for line in self.all_lines():
            division = DivisionEvent(shape=self.right_shape)
            xml_meta(division).update(meta)
            line.add(boundary, _DIVISION, order, division)
            self.end_divisions.append(division)
        for mark in self.right_marks:
            if self.end_divisions:
                self.add_mark(mark, self.end_divisions[0])
        for run in list(self.open_runs.values()):
            if run.end == boundary:
                run.pending_division = DivisionEvent(shape=self.right_shape)
                xml_meta(run.pending_division).update(meta)
            else:
                self.close_run(run)

    def repeat_measure(self, boundary: Fraction) -> None:
        length = boundary - self.measure_start
        event = NoteEvent(tones=set(), duration=MetricalDuration.from_length(length))
        xml_meta(event)["measure_repeat"] = dict(self.measure_repeat)
        line = self.line_for(1)
        line.add(self.measure_start, _NOTE, self.next_order(), event)
        self.add_mark(scoring.simile, event)

    # -- after the last measure

    def finish(self) -> list[tuple[SequentialEvent, list[tuple[Fraction, DivisionEvent]]]]:
        for run in list(self.open_runs.values()):
            self.close_run(run)
        for key, stack in list(self.open_spans.items()):
            while stack:
                self.count(f"{key[0]} {key[1]} left open (no stop in the file)")
                self.close_open_span(key, None)
        for staff, tone in self.open_ties:
            self.warn(f"a tie from {tone.pitch.unicode} on staff {staff} was never ended; ignored")
        lines = self.all_lines()
        if not lines:
            self.emit_counts()
            return []
        for line in lines:
            events = line.finalize(self.total)
            self.graph.add_line(events)
            head_meta = xml_meta(line.head)
            head_meta["staff"] = line.staff
            if line.voice is not None:
                head_meta["voice"] = line.voice
            if line.staff in self.hidden_staves:
                head_meta["hidden"] = True
        for run in self.runs:
            self.graph.add_line(run.events)
            anchor, displacement = self.lines[run.staff].anchor(run.start)
            self.graph.add_branch(
                anchor,
                run.events[0],
                displacement=MetricalDuration.from_length(displacement) if displacement else None,
            )
            xml_meta(run.events[0]).update({"staff": run.staff, "voice": run.voice})
        for main, event in self.splits:
            self.graph.add_line([event])
            self.graph.add_branch(main, event)
        self.place_harmonies()
        for marking, event in self.marks:
            self.graph.add_articulation(marking, event)
        for spanner, start, end in self.spanners:
            self.graph.add_spanner(spanner, start, end)
        self.place_direction_spans()
        self.place_point_marks()
        self.place_sound_tempos()
        self.place_lyrics()
        self.place_endings()
        self.register_parts(lines)
        self.emit_counts()
        first = lines[0]
        return [(first.head, first.divisions)]

    def place_harmonies(self) -> None:
        if not self.harmonies:
            return
        self.harmonies.sort(key=lambda item: item[0])
        events = [event for _, _, event in self.harmonies]
        self.graph.add_line(events)
        for position, staff, event in self.harmonies:
            line = self.line_for(staff if staff in self.lines else 1)
            anchor, displacement = line.anchor(position)
            self.graph.add_simultaneous(
                anchor,
                event,
                displacement=MetricalDuration.from_length(displacement) if displacement else None,
            )
        self.graph.add_line_to_score(self.reader.score, events[0])

    def target_at(
        self, staff: int, position: Fraction, at_end: bool = False
    ) -> tuple[SequentialEvent, dict]:
        line = self.line_for(staff if staff in self.lines else 1)
        if at_end:
            event = line.ending_at(position)
            if event is not None:
                return event, {}
        event = line.at(position)
        if event is not None:
            return event, {}
        found = line.containing(position)
        if found is not None:
            event, onset = found
            return event, {"offset": position - onset}
        return line.events[-1], {"offset": position - line.onsets[-1]}

    def place_direction_spans(self) -> None:
        open_starts: dict[tuple[str, str, int], _DirectionSpan] = {}
        for span in sorted(self.direction_spans, key=lambda s: (s.position, s.start, s.order)):
            key = (span.kind, span.number, span.staff)
            if span.start:
                if key in open_starts:
                    self.finish_direction_span(open_starts.pop(key), None)
                open_starts[key] = span
            else:
                start = open_starts.pop(key, None)
                if start is None:
                    # the stop may name a staff the start did not
                    match = next((k for k in open_starts if k[:2] == key[:2]), None)
                    if match is None:
                        self.warn(f"a {span.kind} stops with no start; ignored")
                        continue
                    start = open_starts.pop(match)
                self.finish_direction_span(start, span)
        for start in open_starts.values():
            if not start.expected_open:
                self.count(f"{start.kind} left open (no stop in the file)")
            self.finish_direction_span(start, None)

    def finish_direction_span(self, start: _DirectionSpan, stop: _DirectionSpan | None) -> None:
        assert start.mark is not None
        start_event, start_meta = self.target_at(start.staff, start.position)
        spanner = MarkSpanner(mark=start.mark)
        meta = dict(start.meta)
        if start_meta:
            meta["offset"] = start_meta["offset"]
        end_event = None
        if stop is not None:
            end_event, end_meta = self.target_at(stop.staff, stop.position, at_end=True)
            if end_meta:
                meta["end_offset"] = end_meta["offset"]
        if meta:
            xml_meta(spanner).update(meta)
        self.graph.add_spanner(spanner, start_event, end_event)

    def place_point_marks(self) -> None:
        for point in self.point_marks:
            line = self.line_for(point.staff if point.staff in self.lines else 1)
            event = line.division_at.get(point.position) if point.on_division else None
            meta: dict = {}
            if event is None:
                event, meta = self.target_at(point.staff, point.position, at_end=point.at_end)
            self.add_mark(point.mark, event, dict(point.meta, **meta))
            marking, target = self.marks[-1]
            self.graph.add_articulation(marking, target)

    def place_sound_tempos(self) -> None:
        for position, staff, tempo in self.sound_tempos:
            events = self.tempos.get(position)
            if events:
                for event in events.values():
                    xml_meta(event).setdefault("sound_tempo", tempo)
                continue
            event, _ = self.target_at(staff, position)
            xml_meta(event).setdefault("sound_tempo", tempo)

    def place_lyrics(self) -> None:
        for key, entries in self.lyric_lines.items():
            entries.sort(key=lambda entry: (entry[0], entry[1]))
            flat: list[tuple[NoteEvent, str, str | None, dict]] = []
            for _, _, event, lyric in entries:
                for index, (text, syllabic) in enumerate(lyric.syllables):
                    flat.append(
                        (
                            event,
                            text,
                            syllabic,
                            lyric.meta if index == len(lyric.syllables) - 1 else {},
                        )
                    )
            syllables = _syllables_of(flat)
            if not syllables:
                continue
            name, language = self.lyric_info.get(key, (None, None))
            number = _verse_number(key[2])
            section = LyricSection(
                section_type="verse", section_number=number, section_name=name, language=language
            )
            self.graph.add_lyrics(syllables, section=section)
            for syllable, (event, _, _, meta) in zip(syllables, flat, strict=True):
                self.graph.connect_lyric_to_object(syllable, event)
                if meta:
                    xml_meta(syllable).update(meta)
            xml_meta(section)["number"] = key[2]

    def place_endings(self) -> None:
        for record in self.endings:
            start_event, start_meta = self.target_at(1, record["start"])
            end_event, end_meta = self.target_at(1, record["stop"], at_end=True)
            name = f"ending {record['number']}"
            spanner = MarkSpanner(
                mark=Mark(name=name, kind=MarkType.NAVIGATION, attachment_mode=AttachmentMode.SPAN)
            )
            xml_meta(spanner)["ending"] = {
                "number": record["number"],
                "type": record["type"],
                "text": record["text"],
            }
            self.graph.add_spanner(spanner, start_event, end_event)
            self.count(
                "<ending> brackets recorded as navigation spans (control flow is not modelled)"
            )
        if self.open_ending is not None:
            self.warn("an <ending> starts and never stops; dropped")

    def register_parts(self, lines: list[_LineBuilder]) -> None:
        score = self.reader.score
        info = self.info
        part_meta = {
            "id": info.id,
            "index": info.index,
            "abbreviation": info.abbreviation,
            "instruments": dict(info.instruments),
            "midi": dict(info.midi),
            "groups": [dict(g) for g in info.groups],
        }
        part_meta = {k: v for k, v in part_meta.items() if v not in (None, {}, [])}
        heads = [line.head for line in lines]
        transposition = self.stint_transposition()
        if self.kit:
            group = LineGroup(name=info.name)
            self.graph.add_group(group, heads)
            for instrument, line in self.kit_lines.items():
                part = PercussionPart(name=line.name or info.name)
                xml_meta(part).update(part_meta)
                if instrument:
                    xml_meta(part)["instrument"] = instrument
                self.graph.add_stint(part, Stint(), line.head)
                self.graph.add_part_to_score(score, part)
                self.graph.add_line_to_score(score, line.head)
            return
        part = Part(name=info.name)
        xml_meta(part).update(part_meta)
        if len(lines) > 1:
            group = LineGroup(name=info.name)
            self.graph.add_group(group, heads)
            self.graph.add_performs(part, group)
            if transposition is not None:
                self.warn(
                    "a transposing part with several staves; the transposition is kept in meta only"
                )
                xml_meta(group)["transposition"] = repr(transposition)
            for line in lines:
                self.graph.add_line_to_score(score, line.head)
        else:
            self.graph.add_stint(part, Stint(transposition=transposition), heads[0])
            self.graph.add_line_to_score(score, heads[0])
        self.graph.add_part_to_score(score, part)

    def stint_transposition(self) -> TonalVector | None:
        """How the part reads the stored (sounding) pitches: written = sounding + this."""
        intervals = {interval for interval in self.transpose.values()}
        if not intervals:
            return None
        interval = next(iter(intervals))
        if len(intervals) > 1:
            self.warn("the staves transpose differently; the first staff's transposition is kept")
        return ORIGIN - interval

    def emit_counts(self) -> None:
        for what, count in self.counts.items():
            self.reader.warn(f"part {self.info.name!r}: {count} {what}")


def _voice_key(voice: str) -> tuple[int, str]:
    return (int(voice), "") if voice.isdigit() else (10**6, voice)


def _interval(diatonic: int, chromatic: int, octave_change: int) -> TonalVector:
    """The interval from written to sounding pitch that a <transpose> describes."""
    total_diatonic = diatonic + 7 * octave_change
    total_chromatic = chromatic + 12 * octave_change
    return TonalVector((total_diatonic % 7, total_chromatic % 12, total_diatonic // 7))


def _abstract_tone(step: str | None, alter: str | None) -> TonalVector:
    degree = tables.STEPS.index((step or "C").strip().upper())
    chromatic = (tables.STEP_CHROMATIC[degree] + int(Fraction((alter or "0").strip()))) % 12
    return TonalVector((degree, chromatic))


def _verse_number(key: str) -> int | None:
    digits = ""
    for char in reversed(key):
        if char.isdigit():
            digits = char + digits
        elif digits:
            break
    return int(digits) if digits else None


def _syllables_of(flat: list[tuple[NoteEvent, str, str | None, dict]]) -> list[LyricSyllable]:
    """Words from `<syllabic>` flags read as advisory: a run closes on `end` or
    `single`, or when the next syllable says `begin` or `single`, so a wrong
    flag can never reorder or lose text."""
    words: list[list[str]] = []
    current: list[str] = []
    for _, text, syllabic, _ in flat:
        if current and syllabic in ("begin", "single", None):
            words.append(current)
            current = []
        current.append(text)
        if syllabic in ("end", "single", None):
            words.append(current)
            current = []
    if current:
        words.append(current)
    syllables: list[LyricSyllable] = []
    for parts in words:
        word = Word([part if part else " " for part in parts])
        syllables.extend(LyricSyllable(word=word, index=i) for i in range(len(word)))
    return syllables
