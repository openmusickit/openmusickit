"""MusicXML out: one `Score` of an `OmkGraph` becomes a `<score-partwise>` document.

The inverse of `reader`, rule by rule (`_plans/musicxml.md` §5 and §6); in short:

- the parts are written in their `STACKS_ABOVE` order: a `Part` with a
  `Stint` over a line is one staff, a `Part` performing a `LineGroup` is one
  staff per line in the group's stack order, and a `LineGroup` whose lines
  are each performed by a `PercussionPart` is one staff of a drum kit;
- a line's `DivisionEvent`s are its bar lines, and between them (or on a line
  without them) the `MeterEvent` in force puts one every meter, which is
  exactly what `OmkGraph.remove_derivable_divisions` takes away, so a graph
  stripped of derivable bar lines writes the same document as the full one;
- a branched line is another voice on its parent's staff, except a single
  event branched with no displacement from a chord it fits, which is written
  back into that chord as `<chord/>` notes;
- pitches are written as written: a `Stint.transposition` is added back to
  the stored sounding pitches and becomes `<transpose>`;
- ties, slurs, hairpins, pedals and other spanners become start/stop pairs,
  markings become `<notations>` or `<direction>`s through `tables`, lyric
  syllables become `<lyric>`s numbered by their verse, and a chord line
  pinned to a part becomes that part's `<harmony>`s;
- what the reader kept in `node.meta["musicxml"]` (voice and measure numbers,
  hidden notes, tuplet brackets, part ids and instruments) is written back.

The writer refuses (`UnexportableError`) only when no document can be
written. Everything else it cannot write -- an event of unknown or clock-time
duration and the rest of its line, an annotation, a line no part performs --
raises an `OmkWarning` naming what was left out.
"""

from __future__ import annotations

import bisect
import warnings
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from fractions import Fraction
from math import lcm
from pathlib import Path
from typing import IO
from uuid import UUID

from openmusickit.errors import OmkWarning, UnexportableError
from openmusickit.graph.edge import EdgeType, TimingAnchor
from openmusickit.graph.graph import OmkGraph, Stackable
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
from openmusickit.objects.lyrics import LyricSection, LyricSyllable, SyllablePlacement
from openmusickit.objects.marking import Marking, MarkSpanner
from openmusickit.objects.note_event import NoteEvent
from openmusickit.objects.omk_object import OmkObject, SequentialEvent
from openmusickit.objects.part import LineGroup, Part, PercussionPart, StackGroup, Stint
from openmusickit.objects.score import Score
from openmusickit.systems.wsmn.percussion.percussion_tone import PercussionTone
from openmusickit.systems.wsmn.scoring import symbols as scoring
from openmusickit.systems.wsmn.scoring.bracket_shape import BracketShape
from openmusickit.systems.wsmn.scoring.staff_clef import StaffClef
from openmusickit.systems.wsmn.temporal.metrical_duration import MetricalDuration, TiedDuration
from openmusickit.systems.wsmn.temporal.time_signature import TimeSignature
from openmusickit.systems.wsmn.temporal.wsmn import WSMN_TEMPORAL
from openmusickit.systems.wsmn.tonal.key import Key
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from openmusickit.values.scoring.mark import Mark, MarkType
from openmusickit.values.time.clock_time import Tempo
from openmusickit.values.time.duration import (
    Duration,
    GraceDuration,
    Measurable,
    TemporalRatio,
    TemporalUnit,
    ZeroDuration,
)

DOCTYPE = (
    '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN" '
    '"http://www.musicxml.org/dtds/partwise.dtd">'
)
SOFTWARE = "Open Music Kit"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
ORIGIN = TonalVector((0, 0, 0))
MAX_NUMBER = 16  # MusicXML's number-level: at most 16 spans of one kind open at once
NEVER = (10**9,)  # the emission order of a stop that is never written


def write(
    graph: OmkGraph,
    target: str | Path | IO[bytes],
    score: Score | None = None,
    omit: Iterable[type[OmkObject]] = (),
) -> None:
    """Writes `score` (the graph's only Score when None) as MusicXML 4.0,
    compressed `.mxl` when the target's name ends in `.mxl`.
    Nodes of the `omit` types are left out, with whatever hangs from them.

    >>> import io
    >>> from openmusickit.graph.graph import GraphMeta
    >>> from openmusickit.io.musicxml import read
    >>> from openmusickit.objects.context_event import MeterEvent
    >>> from openmusickit.objects.note_event import NoteEvent
    >>> from openmusickit.systems.wsmn.scoring.symbols import final_bar
    >>> from openmusickit.systems.wsmn.temporal.symbols import half, two_four
    >>> c4, d4 = TonalVector((0, 0, 0)), TonalVector((1, 2, 0))
    >>> graph = OmkGraph(GraphMeta())
    >>> line = [MeterEvent(meter=two_four), NoteEvent(tones={c4}, duration=half),
    ...         NoteEvent(tones={d4}, duration=half), DivisionEvent(shape=final_bar)]
    >>> graph.add_line(line)
    >>> score, flute = Score(title="Two bars"), Part(name="Flute")
    >>> graph.add_line_to_score(score, line[0])
    >>> graph.add_part_to_score(score, flute)
    >>> graph.add_stint(flute, Stint(), line[0])
    >>> out = io.BytesIO()
    >>> write(graph, out)
    >>> again = read(io.BytesIO(out.getvalue()))
    >>> head = next(again.score_lines(next(again.nodes(Score))))
    >>> [type(event).__name__ for event in again.walk_line(head)]
    ['MeterEvent', 'NoteEvent', 'DivisionEvent', 'NoteEvent', 'DivisionEvent']

    The meter put the bar line between the two notes, as it would in the reader's full form.

    Raises
    ------
    UnexportableError
        if the graph holds no Score, or several and `score` is None, or the
        Score has no parts.
    """
    data = to_bytes(graph, score, omit)
    name = str(target) if isinstance(target, (str, Path)) else str(getattr(target, "name", ""))
    if name.lower().endswith(".mxl"):
        data = container.zipped(data, Path(name).with_suffix(".musicxml").name)
    if isinstance(target, (str, Path)):
        Path(target).write_bytes(data)
    else:
        target.write(data)


def to_bytes(
    graph: OmkGraph, score: Score | None = None, omit: Iterable[type[OmkObject]] = ()
) -> bytes:
    """The uncompressed document `write` writes, as bytes.

    Raises
    ------
    UnexportableError
        as `write` does.
    """
    root = document(graph, score, omit)
    ET.indent(root, space="  ")
    body = ET.tostring(root, encoding="unicode")
    header = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n' + DOCTYPE + "\n"
    return (header + body + "\n").encode("utf-8")


def document(
    graph: OmkGraph, score: Score | None = None, omit: Iterable[type[OmkObject]] = ()
) -> ET.Element:
    """The `<score-partwise>` element `write` serializes.

    Raises
    ------
    UnexportableError
        as `write` does.
    """
    return _Writer(graph, _score_to_write(graph, score), tuple(omit)).build()


def _score_to_write(graph: OmkGraph, score: Score | None) -> Score:
    if score is not None:
        if graph.get_node(score.id) is None:
            raise UnexportableError(f"{score!r} is not on the graph.")
        return score
    scores = list(graph.nodes(Score))
    if not scores:
        raise UnexportableError("The graph holds no Score, so there is nothing to write.")
    if len(scores) > 1:
        titles = ", ".join(sorted(repr(s.title) for s in scores))
        raise UnexportableError(
            f"The graph holds {len(scores)} Scores ({titles}); pass the one to write."
        )
    return scores[0]


def _meta(node: OmkObject) -> dict:
    """The reader's `musicxml` dict on `node`, or an empty one (not stored)."""
    return node.meta.get("musicxml", {})


def _length(event: SequentialEvent) -> Fraction:
    duration = event.duration
    return duration.rational_length if isinstance(duration, Measurable) else Fraction(0)


def _element(tag: str, text: object = None, **attributes: str) -> ET.Element:
    element = ET.Element(tag, {k.replace("_", "-"): v for k, v in attributes.items()})
    if text is not None:
        element.text = str(text)
    return element


def _sub(parent: ET.Element, tag: str, text: object = None, **attributes: str) -> ET.Element:
    element = _element(tag, text, **attributes)
    parent.append(element)
    return element


def _describe(node: OmkObject) -> str:
    return repr(node)


def _voice_key(voice: str) -> tuple[int, str]:
    return (int(voice), "") if voice.isdigit() else (10**6, voice)


# --- laying the score out in time -----------------------------------------------------------


@dataclass
class _Line:
    """A line as written: its events in order, each with its onset in whole notes."""

    events: list[SequentialEvent]
    onsets: list[Fraction]
    end: Fraction

    def divisions(self) -> list[tuple[Fraction, DivisionEvent]]:
        return [
            (onset, event)
            for onset, event in zip(self.onsets, self.events, strict=True)
            if isinstance(event, DivisionEvent)
        ]


@dataclass
class _Voice:
    """One `<voice>` of a staff: a main line, a branch, or a kit voice's strokes."""

    staff: int
    number: str
    line: _Line
    main: bool
    chords: list[list[SequentialEvent]] | None = None  # a kit voice: the strokes struck together


@dataclass
class _Bar:
    start: Fraction
    end: Fraction
    closing: DivisionEvent | None  # the reference line's division at `end`, if it has one


@dataclass
class _Piece:
    """What one `<note>` (or chord of them) writes: the events sounding
    together, from `onset` for `length`, notated as `duration`. An event
    split at a bar line, or with a tied duration, makes several pieces."""

    events: list[SequentialEvent]
    onset: Fraction
    length: Fraction
    duration: Duration
    first: bool
    last: bool


@dataclass
class _Item:
    """Something written at a position on a staff but not as a note:
    attributes, a direction, a harmony, a sound."""

    staff: int
    position: Fraction
    rank: int
    order: int
    element: ET.Element
    offset_ok: bool = True  # <attributes> and <sound> have no <offset>; the cursor moves instead


@dataclass
class _Unit:
    """One `<part>`: a Part's staves, or a drum kit."""

    member: Stackable
    name: str
    meta: dict
    staves: list[_Voice]  # one main line per staff, in staff order (a kit: its first line)
    voices: list[_Voice]  # every voice written, staff by staff
    kit_parts: list[PercussionPart] = field(default_factory=list)
    kit_lines: list[_Line] = field(default_factory=list)
    transposition: TonalVector | None = None
    id: str = ""
    merged: dict[UUID, list[NoteEvent]] = field(default_factory=dict)  # a chord's split tones
    hidden_staves: set[int] = field(default_factory=set)
    bars: list[_Bar] = field(default_factory=list)
    harmonies: list[tuple[int, Fraction, ChordEvent]] = field(default_factory=list)

    def top_level_lines(self) -> list[_Line]:
        return [voice.line for voice in self.staves] + self.kit_lines[1:]


@dataclass
class _Placed:
    unit: _Unit
    voice: _Voice
    onset: Fraction


class _Writer:
    def __init__(self, graph: OmkGraph, score: Score, omit: tuple[type[OmkObject], ...]):
        self.graph = graph
        self.score = score
        self.omit = omit
        self.counts: Counter[str] = Counter()
        self.placed: dict[UUID, _Placed] = {}
        self.used_lines: set[UUID] = set()

    def warn(self, message: str) -> None:
        warnings.warn(message, OmkWarning, stacklevel=5)

    def count(self, what: str) -> None:
        self.counts[what] += 1

    def omitted(self, node: OmkObject) -> bool:
        return bool(self.omit) and isinstance(node, self.omit)

    def build(self) -> ET.Element:
        root = ET.Element("score-partwise", version="4.0")
        self.write_header(root)
        units = self.lay_out_units()
        if not units:
            raise UnexportableError(f"{self.score!r} has no parts, so there is nothing to write.")
        self.assign_ids(units)
        self.cut_into_bars(units)
        self.check_grids(units)
        self.place_harmonies()
        self.warn_unwritten_lines()
        self.write_part_list(root, units)
        for unit in units:
            root.append(_PartWriter(self, unit).build())
        for what, count in self.counts.items():
            self.warn(f"{count} {what}")
        return root

    # -- header

    def write_header(self, root: ET.Element) -> None:
        score, meta = self.score, _meta(self.score)
        if score.title is not None or score.opus is not None:
            work = _sub(root, "work")
            if score.opus is not None:
                _sub(work, "work-number", score.opus)
            if score.title is not None:
                _sub(work, "work-title", score.title)
        if meta.get("movement_number"):
            _sub(root, "movement-number", meta["movement_number"])
        if meta.get("movement_title"):
            _sub(root, "movement-title", meta["movement_title"])
        identification = _sub(root, "identification")
        for kind in ("composer", "lyricist", "arranger"):
            if getattr(score, kind):
                _sub(identification, "creator", getattr(score, kind), type=kind)
        for kind, name in meta.get("creators", []):
            creator = _sub(identification, "creator", name)
            if kind:
                creator.set("type", kind)
        if score.copyright:
            for line in score.copyright.split("\n"):
                _sub(identification, "rights", line)
        encoding = _sub(identification, "encoding")
        _sub(encoding, "software", SOFTWARE)
        for element in ("accidental", "beam", "stem"):
            _sub(encoding, "supports", element=element, type="no")
        if meta.get("source"):
            _sub(identification, "source", meta["source"])
        for kind in ("subtitle", "dedication"):
            if getattr(score, kind):
                credit = _sub(root, "credit", page="1")
                _sub(credit, "credit-type", kind)
                _sub(credit, "credit-words", getattr(score, kind))

    # -- parts and their lines

    def lay_out_units(self) -> list[_Unit]:
        units: list[_Unit] = []
        kits: dict[UUID, _Unit] = {}
        for part in sorted(self.graph.score_parts(self.score), key=lambda part: part.name):
            if self.omitted(part):
                continue
            groups = list(self.graph.groups(part))
            stints = list(self.graph.stints(part))
            if groups:
                if len(groups) > 1 or stints:
                    self.warn(
                        f"{_describe(part)} performs several things; its first group is written"
                    )
                units.append(self.multi_staff_unit(part, groups[0]))
                continue
            if not stints:
                self.warn(f"{_describe(part)} performs nothing; it is written as an empty staff")
                units.append(
                    _Unit(member=part, name=part.name, meta=_meta(part), staves=[], voices=[])
                )
                continue
            if len(stints) > 1:
                self.warn(f"{_describe(part)} has {len(stints)} stints; one is written")
            start, end = self.graph._stint_bounds(stints[0])
            kit = self.kit_group(start)
            if kit is not None and isinstance(part, PercussionPart):
                if kit.id not in kits:
                    kits[kit.id] = _Unit(
                        member=kit,
                        name=kit.name or part.name,
                        meta=_meta(part),
                        staves=[],
                        voices=[],
                    )
                    units.append(kits[kit.id])
                kits[kit.id].kit_parts.append(part)
                continue
            if self.graph.get_previous(start) is not None or end is not None:
                self.warn(f"{_describe(part)} performs part of a line; that part is written")
            units.append(self.single_staff_unit(part, stints[0], start, end))
        for unit in kits.values():
            self.fill_kit(unit)
        return self.stack_order(units)

    def kit_group(self, head: SequentialEvent) -> LineGroup | None:
        """The group of a drum kit's lines: a LineGroup no Part performs."""
        for group in self.graph.groups_of(head):
            if not any(self.graph._graph.predecessors(group, Part, EdgeType.PERFORMS)):
                return group
        return None

    def single_staff_unit(
        self, part: Part, stint: Stint, start: SequentialEvent, end: SequentialEvent | None
    ) -> _Unit:
        voice = self.main_voice(start, 1, end)
        unit = _Unit(member=part, name=part.name, meta=_meta(part), staves=[voice], voices=[])
        if isinstance(stint.transposition, TonalVector):
            unit.transposition = stint.transposition
        elif stint.transposition is not None:
            self.warn(
                f"{_describe(part)}: the transposition {stint.transposition!r} is not written"
            )
        if _meta(start).get("hidden"):
            unit.hidden_staves.add(1)
        self.add_branches(unit, voice)
        return unit

    def multi_staff_unit(self, part: Part, group: LineGroup) -> _Unit:
        unit = _Unit(member=part, name=part.name, meta=_meta(part), staves=[], voices=[])
        if _meta(group).get("transposition"):
            self.warn(
                f"{_describe(part)}: a transposing part of several staves is written as it sounds"
            )
        for number, head in enumerate(
            self.in_stack_order(list(self.graph.group_members(group))), 1
        ):
            voice = self.main_voice(head, number)
            unit.staves.append(voice)
            if _meta(head).get("hidden"):
                unit.hidden_staves.add(number)
        for voice in list(unit.staves):
            self.add_branches(unit, voice)
        return unit

    def in_stack_order(self, heads: list[SequentialEvent]) -> list[SequentialEvent]:
        """A group's lines top to bottom: by their stack, else by the staff
        the reader recorded."""
        ids = {head.id for head in heads}
        for head in heads:
            above = self.graph.stacked_above(head)
            if above is None or above.id not in ids:
                ordered = [m for m in self.graph.walk_stack(head) if m.id in ids]
                if len(ordered) == len(heads):
                    return ordered  # type: ignore[return-value]
        if len(heads) > 1:
            self.warn("a part's lines are not one stack; they are written by recorded staff")
        return sorted(heads, key=lambda head: _meta(head).get("staff", 0))

    def fill_kit(self, unit: _Unit) -> None:
        """A kit is one staff: its lines' strokes, voice by voice. The first
        line's contexts and bar lines stand for all of them."""
        for part in unit.kit_parts:
            start, _ = self.graph._stint_bounds(next(self.graph.stints(part)))
            unit.kit_lines.append(self.lay_out(start, Fraction(0)))
            self.used_lines.add(start.id)
        reference = _Voice(staff=1, number="1", line=unit.kit_lines[0], main=True)
        unit.staves = [reference]
        strokes: dict[str, list[tuple[Fraction, int, SequentialEvent]]] = defaultdict(list)
        for index, line in enumerate(unit.kit_lines):
            for onset, event in zip(line.onsets, line.events, strict=True):
                self.placed[event.id] = _Placed(unit, reference, onset)
                if isinstance(event, NoteEvent) and event.tones and not event.is_rest:
                    strokes[str(_meta(event).get("voice") or "1")].append((onset, index, event))
        for number in sorted(strokes, key=_voice_key) or ["1"]:
            chords: list[list[SequentialEvent]] = []
            onsets: list[Fraction] = []
            for onset, _, event in sorted(strokes[number], key=lambda s: (s[0], s[1])):
                if onsets and onsets[-1] == onset and _length(chords[-1][0]) == _length(event):
                    chords[-1].append(event)
                else:
                    chords.append([event])
                    onsets.append(onset)
            heads = [chord[0] for chord in chords]
            end = max(
                (o + _length(e) for o, e in zip(onsets, heads, strict=True)), default=Fraction(0)
            )
            voice = _Voice(1, number, _Line(heads, onsets, end), main=False, chords=chords)
            unit.voices.append(voice)
            for chord, onset in zip(chords, onsets, strict=True):
                for event in chord:
                    self.placed[event.id] = _Placed(unit, voice, onset)

    def main_voice(
        self, head: SequentialEvent, staff: int, end: SequentialEvent | None = None
    ) -> _Voice:
        self.used_lines.add(head.id)
        number = str(_meta(head).get("voice") or (4 * (staff - 1) + 1))
        return _Voice(
            staff=staff, number=number, line=self.lay_out(head, Fraction(0), end), main=True
        )

    def lay_out(
        self, head: SequentialEvent, start: Fraction, end: SequentialEvent | None = None
    ) -> _Line:
        events: list[SequentialEvent] = []
        onsets: list[Fraction] = []
        position = start
        for event in self.graph.walk_line(head, end):
            if not _writable(event.duration):
                self.warn(
                    f"{_describe(event)} has the duration {event.duration!r}, which MusicXML "
                    "cannot place; it and the rest of its line are left out"
                )
                break
            if not self.omitted(event):
                events.append(event)
                onsets.append(position)
            position += _length(event)
        return _Line(events, onsets, position)

    def add_branches(self, unit: _Unit, main: _Voice) -> None:
        """Every line branched from `main` (and from its branches) as a voice
        of its staff, or folded back into the chord the reader split it from."""
        branches: list[tuple[Fraction, _Line, SequentialEvent]] = []
        splits: dict[UUID, list[tuple[NoteEvent, Fraction]]] = defaultdict(list)
        parents: dict[UUID, NoteEvent] = {}
        pending = [main.line]
        while pending:
            line = pending.pop()
            for onset, event in zip(line.onsets, line.events, strict=True):
                for head in self.graph.branches_from(event):
                    if self.omitted(head):
                        continue
                    edge = self.graph.get_edge(event, head, EdgeType.BRANCHES)
                    start = onset + (_length(event) if edge.anchor is TimingAnchor.OFFSET else 0)
                    if isinstance(edge.displacement, Measurable):
                        start += edge.displacement.rational_length
                    if self.is_chord_split(event, head, edge):
                        splits[event.id].append((head, start))  # type: ignore[arg-type]
                        parents[event.id] = event  # type: ignore[assignment]
                        continue
                    branch = self.lay_out(head, start)
                    branches.append((start, branch, head))
                    pending.append(branch)
        for parent_id, found in splits.items():
            heads = [head for head, _ in found]
            if self.chord_folds_back(parents[parent_id], heads):
                unit.merged[parent_id] = heads
            else:
                branches.extend((start, self.lay_out(head, start), head) for head, start in found)
        unit.voices.append(main)
        for onset, event in zip(main.line.onsets, main.line.events, strict=True):
            self.placed[event.id] = _Placed(unit, main, onset)
        for voice in self.number_voices(main, branches):
            unit.voices.append(voice)
            for onset, event in zip(voice.line.onsets, voice.line.events, strict=True):
                self.placed[event.id] = _Placed(unit, voice, onset)
        for parent_id, heads in unit.merged.items():
            for head in heads:
                if parent_id in self.placed:
                    self.placed[head.id] = self.placed[parent_id]

    def is_chord_split(self, parent: SequentialEvent, head: SequentialEvent, edge) -> bool:
        """Whether `head` looks like a tone class the reader split off a
        chord: one note at the chord's onset and of its value, carrying
        nothing of its own but ties and per-tone marks."""
        if edge.anchor is not TimingAnchor.ONSET or edge.displacement is not None:
            return False
        if self.graph.get_next(head) is not None or any(self.graph.branches_from(head)):
            return False
        for event in (parent, head):
            if not isinstance(event, NoteEvent) or event.is_rest or not event.tones:
                return False
            if not all(isinstance(t, TonalVector) and t.has_octave for t in event.tones):
                return False
        if _length(parent) != _length(head) or parent.duration != head.duration:
            return False
        if isinstance(head.duration, GraceDuration) != isinstance(parent.duration, GraceDuration):
            return False
        nodes = self.graph._graph
        if not all(
            tables.is_per_tone(m.mark) for m in nodes.predecessors(head, Marking, EdgeType.MARKS)
        ):
            return False
        for edge_type in (EdgeType.STARTS_AT, EdgeType.ENDS_AT):
            if any(
                s.mark is not scoring.tie for s in nodes.predecessors(head, MarkSpanner, edge_type)
            ):
                return False
        if any(nodes.successors(head, LyricSyllable, EdgeType.LYRIC)):
            return False
        return not any(nodes.in_edges(head, EdgeType.SIMULTANEOUS)) and not any(
            nodes.out_edges(head, EdgeType.SIMULTANEOUS)
        )

    def chord_folds_back(self, parent: NoteEvent, splits: list[NoteEvent]) -> bool:
        """Whether `parent` and `splits` written as one chord read back as they
        are: every tone class distinct, and `parent` the one the reader keeps
        on the line (the largest, ties broken by the lowest tone)."""
        events = [parent, *splits]
        signatures = [self.tone_signature(event) for event in events]
        if len(set(signatures)) != len(signatures):
            return False
        return min(events, key=lambda e: (-len(e.tones), min(e.tones))) is parent

    def tone_signature(self, event: NoteEvent) -> tuple:
        """What the reader partitions a chord's tones by: tied in, tied out,
        and the per-tone marks on each tone."""
        nodes = self.graph._graph
        tie_out = any(
            s.mark is scoring.tie
            for s in nodes.predecessors(event, MarkSpanner, EdgeType.STARTS_AT)
        )
        tie_in = any(
            s.mark is scoring.tie for s in nodes.predecessors(event, MarkSpanner, EdgeType.ENDS_AT)
        )
        names = sorted(
            m.mark.name
            for m in nodes.predecessors(event, Marking, EdgeType.MARKS)
            if tables.is_per_tone(m.mark)
        )
        tones = len(event.tones)
        return (tie_out, tie_in, tuple(names[::tones]) if len(names) % tones == 0 else tuple(names))

    def number_voices(
        self, main: _Voice, branches: list[tuple[Fraction, _Line, SequentialEvent]]
    ) -> list[_Voice]:
        """A voice number for each branch of a staff: the one the reader
        recorded while it still fits, else the lowest free one above the main
        voice. A voice holds one line at a time, and two lines of one number
        must not touch, or the reader would read them as one."""
        last_end: dict[str, Fraction] = {}
        voices: list[_Voice] = []
        main_key = _voice_key(main.number)

        def free(number: str, start: Fraction) -> bool:
            return _voice_key(number) > main_key and last_end.get(number, Fraction(-1)) < start

        for start, line, head in sorted(branches, key=lambda b: (b[0], b[1].end)):
            wanted = str(_meta(head).get("voice") or "")
            number = wanted if wanted and free(wanted, start) else None
            candidate = int(main.number) + 1 if main.number.isdigit() else 2
            while number is None:
                if free(str(candidate), start):
                    number = str(candidate)
                candidate += 1
            last_end[number] = max(line.end, start)
            voices.append(_Voice(staff=main.staff, number=number, line=line, main=False))
            self.used_lines.add(head.id)
        return sorted(voices, key=lambda voice: _voice_key(voice.number))

    def stack_order(self, units: list[_Unit]) -> list[_Unit]:
        """The units top to bottom by their stack; several stacks are written
        one after another, ordered by their first part's name."""
        by_member = {unit.member.id: unit for unit in units}
        chains: dict[UUID, list[_Unit]] = {}
        for unit in units:
            top = unit.member
            while (above := self.graph.stacked_above(top)) is not None:
                top = above
            if top.id not in chains:
                chains[top.id] = [
                    by_member[m.id] for m in self.graph.walk_stack(top) if m.id in by_member
                ]
        ordered = sorted(chains.values(), key=lambda chain: chain[0].name)
        if len(ordered) > 1:
            listed = "; ".join(
                "[" + ", ".join(repr(u.name) for u in chain) + "]" for chain in ordered
            )
            self.warn(f"the parts are not one stack; they are written stack by stack: {listed}")
        return [unit for chain in ordered for unit in chain]

    def assign_ids(self, units: list[_Unit]) -> None:
        taken: set[str] = set()
        for unit in units:
            wanted = unit.meta.get("id")
            if isinstance(wanted, str) and wanted and wanted not in taken:
                unit.id = wanted
                taken.add(wanted)
        number = 1
        for unit in units:
            while not unit.id:
                if f"P{number}" not in taken:
                    unit.id = f"P{number}"
                    taken.add(unit.id)
                number += 1

    # -- bars

    def cut_into_bars(self, units: list[_Unit]) -> None:
        """Every part is cut at the same bar lines: those of the first part
        whose first staff has any, else of the first with a meter."""
        cuts = {id(unit): self.bars_of(unit.staves[0].line) for unit in units if unit.staves}
        ranked = sorted(
            (unit for unit in units if unit.staves),
            key=lambda unit: {"explicit": 0, "meter": 1, "none": 2}[cuts[id(unit)][1]],
        )
        if not ranked:
            for unit in units:
                unit.bars = [_Bar(Fraction(0), Fraction(0), None)]
            return
        reference = ranked[0]
        bars, how = cuts[id(reference)]
        if how == "none":
            self.warn(f"part {reference.name!r} has no bar lines and no meter; it is one measure")
        elif how == "meter":
            self.warn(f"part {reference.name!r} has no bar lines; its meter places them")
        ends = [bar.end for bar in bars]
        for unit in units:
            if unit is reference:
                unit.bars = bars
                continue
            own: dict[Fraction, _Bar] = {}
            if unit.staves:
                own_bars, _ = cuts[id(unit)]
                own = {bar.end: bar for bar in own_bars}
                stray = [bar.end for bar in own_bars[:-1] if bar.end not in ends]
                if own_bars[-1].end > ends[-1]:
                    stray.append(own_bars[-1].end)
                if stray:
                    self.warn(
                        f"part {unit.name!r} has a bar line at {stray[0]} whole notes where part "
                        f"{reference.name!r} has none; it is written in {reference.name!r}'s bars"
                    )
                elif own_bars[-1].end < ends[-1]:
                    self.warn(
                        f"part {unit.name!r} ends {ends[-1] - own_bars[-1].end} whole notes before "
                        f"part {reference.name!r}; its last measures are left empty"
                    )
            unit.bars = [
                _Bar(bar.start, bar.end, own[bar.end].closing if bar.end in own else None)
                for bar in bars
            ]

    def bars_of(self, line: _Line) -> tuple[list[_Bar], str]:
        """The bars of a line: its divisions, with the meter in force filling
        the gaps (the inverse of `remove_derivable_divisions`), and how they
        were found: "explicit", "meter" or "none"."""
        explicit = {onset for onset, _ in line.divisions() if onset > 0}
        bars: list[_Bar] = []
        start = Fraction(0)
        meter: Fraction | None = None
        saw_meter = False
        for onset, event in zip(line.onsets, line.events, strict=True):
            length = _length(event)
            while meter:
                boundary = start + meter
                reached = boundary < onset + length if length else boundary <= onset
                if not reached or boundary in explicit or boundary >= line.end:
                    break
                bars.append(_Bar(start, boundary, None))
                start = boundary
            if isinstance(event, DivisionEvent) and onset > start:
                bars.append(_Bar(start, onset, event))
                start = onset
            if isinstance(event, MeterEvent):
                saw_meter = True
                value = event.meter
                meter = value.rational_length if isinstance(value, Measurable) else None
        if line.end > start or not bars:
            bars.append(_Bar(start, line.end, None))
        return bars, "explicit" if explicit else ("meter" if saw_meter else "none")

    # -- the bar grid, chord lines, and what is left out

    def check_grids(self, units: list[_Unit]) -> None:
        """A bar grid records that bar n is bar n in every part. The writer
        aligns parts by their own durations, so a grid is checked against
        them, not used: each pinned event must fall as far after its part's
        head as its point lies after the head's. A sync line pinning anything
        but the parts' own lines is not written."""
        positions: dict[UUID, tuple[_Unit, Fraction, bool]] = {}
        for unit in units:
            for line in unit.top_level_lines():
                for index, (onset, event) in enumerate(zip(line.onsets, line.events, strict=True)):
                    positions.setdefault(event.id, (unit, onset, index == 0))
        for sync_line in self.graph.score_sync_lines(self.score):
            if self.omitted(sync_line):
                continue
            if not sync_line.temporal_system.compatible_with(WSMN_TEMPORAL):
                self.warn(f"{_describe(sync_line)} is not in metrical time; it is not written")
                continue
            pins: list[tuple[_Unit, Fraction, bool, Fraction]] = []
            foreign = 0
            for point in self.graph.sync_points(sync_line):
                offset = (
                    point.offset.rational_length if isinstance(point.offset, Measurable) else None
                )
                for event in self.graph.synced_events(point):
                    found = positions.get(event.id)
                    if found is None or offset is None:
                        foreign += 1
                    else:
                        pins.append((*found, offset))
            if foreign:
                self.warn(
                    f"{_describe(sync_line)} pins {foreign} events that are not on the written "
                    "parts' lines; it is not written"
                )
                continue
            origins = {id(unit): offset for unit, _, is_head, offset in pins if is_head}
            for unit, position, is_head, offset in pins:
                origin = origins.get(id(unit))
                if not is_head and origin is not None and offset - origin != position:
                    self.warn(
                        f"part {unit.name!r}: the event at {position} whole notes is pinned at "
                        f"{offset - origin} on {sync_line.name!r}; the part's durations are written"
                    )
                    break

    def place_harmonies(self) -> None:
        """A line of ChordEvents pinned to a part's events is that part's <harmony>s."""
        for head in self.graph.score_lines(self.score):
            if head.id in self.used_lines:
                continue
            events = list(self.graph.walk_line(head))
            if not events or not all(isinstance(e, ChordEvent) for e in events):
                continue
            self.used_lines.add(head.id)
            previous: tuple[_Unit, int, Fraction, ChordEvent] | None = None
            for event in events:
                if self.omitted(event):
                    previous = None
                    continue
                found = self.pinned_position(event)
                if found is None and previous is not None and previous[3].duration is not None:
                    unit, staff, position, chord = previous
                    found = (unit, staff, position + _length(chord))
                if found is None:
                    self.warn(f"{_describe(event)} is pinned to nothing written; it is left out")
                    continue
                if event.duration is not None:
                    self.count("chord-symbol durations not written (a <harmony> has none)")
                unit, staff, position = found
                unit.harmonies.append((staff, position, event))
                previous = (unit, staff, position, event)

    def pinned_position(self, event: ChordEvent) -> tuple[_Unit, int, Fraction] | None:
        nodes = self.graph._graph
        for edge in nodes.in_edges(event, EdgeType.SIMULTANEOUS):
            source = nodes.get_source_of_edge(edge)
            placed = self.placed.get(source.id)
            if placed is not None:
                position = placed.onset
                if edge.anchor is TimingAnchor.OFFSET:
                    position += _length(source)
                if isinstance(edge.displacement, Measurable):
                    position += edge.displacement.rational_length
                return placed.unit, placed.voice.staff, position
        for edge in nodes.out_edges(event, EdgeType.SIMULTANEOUS):
            target = nodes.get_target_of_edge(edge)
            placed = self.placed.get(target.id)
            if placed is None or (edge.anchor is TimingAnchor.OFFSET and event.duration is None):
                continue
            position = placed.onset
            if edge.anchor is TimingAnchor.OFFSET:
                position -= _length(event)
            if isinstance(edge.displacement, Measurable):
                position -= edge.displacement.rational_length
            return placed.unit, placed.voice.staff, position
        return None

    def warn_unwritten_lines(self) -> None:
        for head in self.graph.score_lines(self.score):
            if head.id not in self.used_lines and not self.omitted(head):
                self.warn(
                    f"the score line from {_describe(head)} is performed by no part; it is left out"
                )

    # -- the part list

    def write_part_list(self, root: ET.Element, units: list[_Unit]) -> None:
        part_list = _sub(root, "part-list")
        index = {unit.member.id: i for i, unit in enumerate(units)}
        starts: dict[int, list[tuple[int, StackGroup]]] = defaultdict(list)
        stops: dict[int, list[tuple[int, StackGroup]]] = defaultdict(list)
        seen: set[UUID] = set()
        for unit in units:
            for group in self.graph.stack_groups_of(unit.member):
                if group.id in seen or self.omitted(group):
                    continue
                seen.add(group.id)
                members = [
                    index[m.id] for m in self.graph.stack_group_members(group) if m.id in index
                ]
                if members:
                    starts[members[0]].append((members[-1], group))
                    stops[members[-1]].append((members[0], group))
        numbers: dict[UUID, int] = {}
        for i, unit in enumerate(units):
            for _, group in sorted(starts[i], key=lambda item: -item[0]):  # the outermost first
                number = 1
                while number in numbers.values():
                    number += 1
                numbers[group.id] = number
                self.write_group(part_list, group, number)
            self.write_score_part(part_list, unit)
            for _, group in sorted(stops[i], key=lambda item: -item[0]):  # the innermost first
                _sub(part_list, "part-group", type="stop", number=str(numbers.pop(group.id)))

    def write_group(self, part_list: ET.Element, group: StackGroup, number: int) -> None:
        element = _sub(part_list, "part-group", type="start", number=str(number))
        if group.name is not None:
            _sub(element, "group-name", group.name)
        if group.abbreviation is not None:
            _sub(element, "group-abbreviation", group.abbreviation)
        if isinstance(group.shape, BracketShape):
            _sub(element, "group-symbol", tables.GROUP_SYMBOL_NAMES.get(group.shape.symbol, "none"))
            _sub(
                element,
                "group-barline",
                tables.GROUP_BARLINE_NAMES.get(group.shape.bar_lines, "no"),
            )
        elif group.shape is not None:
            self.warn(f"{_describe(group)}: the shape is not a WSMN bracket; it is not written")

    def write_score_part(self, part_list: ET.Element, unit: _Unit) -> None:
        element = _sub(part_list, "score-part", id=unit.id)
        _sub(element, "part-name", unit.name)
        if unit.meta.get("abbreviation") is not None:
            _sub(element, "part-abbreviation", unit.meta["abbreviation"])
        instruments = dict(unit.meta.get("instruments") or {})
        if unit.kit_parts and not instruments:
            for number, part in enumerate(unit.kit_parts, start=1):
                instruments[_meta(part).get("instrument") or f"{unit.id}-I{number}"] = part.name
        for instrument_id, name in instruments.items():
            instrument = _sub(element, "score-instrument", id=instrument_id)
            _sub(instrument, "instrument-name", name)
        for instrument_id, settings in (unit.meta.get("midi") or {}).items():
            midi = _sub(element, "midi-instrument", id=instrument_id)
            for tag, value in settings.items():
                _sub(midi, tag, value)


def _writable(duration: Duration | None) -> bool:
    if isinstance(duration, (MetricalDuration, ZeroDuration)):
        return True
    if isinstance(duration, TiedDuration):
        return all(isinstance(member, MetricalDuration) for member in duration)
    return False


# --- one <part> ---------------------------------------------------------------------------------

_CONTEXT, _DIRECTION, _HARMONY = 0, 1, 2

_SYLLABIC = {
    SyllablePlacement.WHOLE: "single",
    SyllablePlacement.BEGINNING: "begin",
    SyllablePlacement.MIDDLE: "middle",
    SyllablePlacement.END: "end",
}


class _PartWriter:
    def __init__(self, writer: _Writer, unit: _Unit):
        self.writer = writer
        self.graph = writer.graph
        self.unit = unit
        self.bars = unit.bars
        self.ends = [bar.end for bar in unit.bars]
        self.multi_staff = len(unit.staves) > 1
        self.divisions = 1
        self.order = 0
        self.items: dict[int, list[_Item]] = defaultdict(list)  # by bar
        self.leading: dict[int, list[tuple[int, ContextEvent]]] = defaultdict(list)  # by bar
        self.pieces: list[dict[int, list[_Piece]]] = []  # by voice, then by bar
        self.first_piece: dict[UUID, tuple[int, int, int]] = {}  # bar, voice, sequence
        self.last_piece: dict[UUID, tuple[int, int, int]] = {}
        self.first_written: dict[UUID, tuple[int, int, int]] = {}  # bar, place in the bar, sequence
        self.last_written: dict[UUID, tuple[int, int, int]] = {}
        self.bar_orders: list[list[int]] = []
        self.ordered_pairs: list[
            tuple[SequentialEvent, SequentialEvent]
        ] = []  # starts before stops
        self.notations: dict[UUID, list[tuple[Mark, dict]]] = defaultdict(list)
        self.ties_out: dict[UUID, set] = defaultdict(set)
        self.ties_in: dict[UUID, set] = defaultdict(set)
        self.notation_spans: list[
            tuple[str, int, SequentialEvent, SequentialEvent | None, dict]
        ] = []
        self.span_starts: dict[UUID, list[tuple[str, int, dict]]] = defaultdict(list)
        self.span_stops: dict[UUID, list[tuple[str, int]]] = defaultdict(list)
        self.span_numbers: dict[int, str] = {}
        self.direction_spans: list[tuple[MarkSpanner, int, Fraction, int, Fraction | None]] = []
        self.barline_marks: dict[Fraction, list[Mark]] = defaultdict(list)  # by bar-line position
        self.endings_start: dict[int, list[tuple[str, str | None]]] = defaultdict(list)
        self.endings_stop: dict[int, list[tuple[str, str]]] = defaultdict(list)
        self.tuplets: dict[UUID, list[dict]] = {}
        self.lyric_lines: dict[UUID, tuple[str, str | None, str | None]] = {}

    def warn(self, message: str) -> None:
        self.writer.warn(f"part {self.unit.name!r}: {message}")

    def count(self, what: str) -> None:
        self.writer.count(f"{what} (part {self.unit.name!r})")

    def next_order(self) -> int:
        self.order += 1
        return self.order

    def build(self) -> ET.Element:
        part = ET.Element("part", id=self.unit.id)
        if not self.unit.voices:
            self.divisions = self.compute_divisions()
            for index, bar in enumerate(self.bars):
                measure = _sub(part, "measure", number=str(index + 1))
                if index == 0:
                    _sub(_sub(measure, "attributes"), "divisions", self.divisions)
                note = _sub(measure, "note")
                _sub(note, "rest", measure="yes")
                _sub(note, "duration", self.duration_value(bar.end - bar.start))
                _sub(note, "voice", "1")
            return part
        self.cut_pieces()
        self.collect_attachments()
        self.collect_contexts()
        self.collect_harmonies()
        self.divisions = self.compute_divisions()
        for index, bar in enumerate(self.bars):
            part.append(self.write_measure(index, bar))
        return part

    # -- each voice cut at the bar lines

    def bar_of(self, position: Fraction, at_end: bool = False) -> int:
        """The bar a position belongs to: the one it starts, or for a stop
        the one it ends; past the last bar, the last."""
        if at_end:
            return min(bisect.bisect_left(self.ends, position), len(self.bars) - 1)
        return min(bisect.bisect_right(self.ends, position), len(self.bars) - 1)

    def voice_order(self) -> list[int]:
        """The voices in the order they are written in a measure."""
        voices = self.unit.voices
        return sorted(
            range(len(voices)),
            key=lambda i: (voices[i].staff, not voices[i].main, _voice_key(voices[i].number)),
        )

    def cut_pieces(self) -> None:
        for voice_index, voice in enumerate(self.unit.voices):
            by_bar: dict[int, list[_Piece]] = defaultdict(list)
            for item, (onset, event) in enumerate(
                zip(voice.line.onsets, voice.line.events, strict=True)
            ):
                if isinstance(event, DivisionEvent):
                    if voice.main and 0 < onset < voice.line.end and onset not in self.ends:
                        self.count("bar lines not on the part's bars, not written")
                    continue
                if not isinstance(event, NoteEvent):
                    if not isinstance(event, ContextEvent):
                        self.count(f"{type(event).__name__}s, which a staff cannot hold, left out")
                    continue
                if voice.chords is not None:
                    events: list[SequentialEvent] = list(voice.chords[item])
                else:
                    events = [event, *self.unit.merged.get(event.id, [])]
                for bar, piece in self.pieces_of(events, onset):
                    by_bar[bar].append(piece)
            for bar, pieces in by_bar.items():
                for sequence, piece in enumerate(pieces):
                    for event in piece.events:
                        if piece.first:
                            self.first_piece[event.id] = (bar, voice_index, sequence)
                        if piece.last:
                            self.last_piece[event.id] = (bar, voice_index, sequence)
            self.pieces.append(by_bar)

    def order_bars(self) -> None:
        """The order of the voices in each measure: staff by staff, the main
        voice first, except that a voice in which a slur or tie starts comes
        before the voice in which it stops. The reader pairs starts and
        stops in file order, and a voice may cross from one staff to another."""
        default = self.voice_order()
        rank = {voice_index: r for r, voice_index in enumerate(default)}
        after: dict[int, dict[int, set[int]]] = defaultdict(lambda: defaultdict(set))
        for start, end in self.ordered_pairs:
            first, last = self.first_piece.get(start.id), self.last_piece.get(end.id)
            if (
                first is not None
                and last is not None
                and first[0] == last[0]
                and first[1] != last[1]
            ):
                after[first[0]][last[1]].add(first[1])
        for index in range(len(self.bars)):
            constraints = after.get(index, {})
            remaining = set(default)
            order: list[int] = []
            while remaining:
                ready = [v for v in remaining if not (constraints.get(v, set()) & remaining)]
                chosen = min(ready or remaining, key=lambda v: rank[v])
                order.append(chosen)
                remaining.discard(chosen)
            self.bar_orders.append(order)
        position = [{v: i for i, v in enumerate(order)} for order in self.bar_orders]
        for table, pieces in (
            (self.first_written, self.first_piece),
            (self.last_written, self.last_piece),
        ):
            for event_id, (bar, voice_index, sequence) in pieces.items():
                table[event_id] = (bar, position[bar][voice_index], sequence)

    def pieces_of(self, events: list[SequentialEvent], onset: Fraction) -> list[tuple[int, _Piece]]:
        duration = events[0].duration
        if _length(events[0]) == 0:
            return [(self.bar_of(onset), _Piece(events, onset, Fraction(0), duration, True, True))]  # type: ignore[arg-type]
        members = list(duration) if isinstance(duration, TiedDuration) else [duration]
        chunks: list[tuple[Fraction, Fraction, Duration]] = []
        position = onset
        for member in members:
            size = member.rational_length  # type: ignore[union-attr]
            cuts = [end for end in self.ends if position < end < position + size]
            if not cuts:
                chunks.append((position, size, member))  # type: ignore[arg-type]
            else:
                self.count("notes split at bar lines and tied")
                edges = [position, *cuts, position + size]
                for left, right in zip(edges, edges[1:], strict=False):
                    spelled = MetricalDuration.from_length(right - left)
                    for part in spelled if isinstance(spelled, TiedDuration) else [spelled]:
                        chunks.append((left, part.rational_length, part))
                        left += part.rational_length
            position += size
        last = len(chunks) - 1
        return [
            (self.bar_of(start), _Piece(events, start, size, member, i == 0, i == last))
            for i, (start, size, member) in enumerate(chunks)
        ]

    # -- what hangs from the events

    def all_events(self) -> Iterator[tuple[_Voice, Fraction, SequentialEvent]]:
        for voice in self.unit.voices:
            for item, (onset, event) in enumerate(
                zip(voice.line.onsets, voice.line.events, strict=True)
            ):
                if voice.chords is not None:
                    members: list[SequentialEvent] = list(voice.chords[item])
                else:
                    members = [event, *self.unit.merged.get(event.id, [])]
                for member in members:
                    yield voice, onset, member
        for line in self.unit.kit_lines:  # a kit's contexts, bar lines and gaps are on its lines
            for onset, event in zip(line.onsets, line.events, strict=True):
                if not (isinstance(event, NoteEvent) and event.tones and not event.is_rest):
                    yield self.unit.staves[0], onset, event

    def collect_attachments(self) -> None:
        nodes = self.graph._graph
        annotations = 0
        spanners: dict[UUID, MarkSpanner] = {}
        for voice, onset, event in self.all_events():
            for marking in nodes.predecessors(event, Marking, EdgeType.MARKS):
                if not self.writer.omitted(marking):
                    self.place_marking(marking, voice, onset, event)
            for spanner in nodes.predecessors(event, MarkSpanner, EdgeType.STARTS_AT):
                if not self.writer.omitted(spanner):
                    spanners[spanner.id] = spanner
            annotations += sum(1 for _ in nodes.predecessors(event, edge_type=EdgeType.ANNOTATES))
            for syllable in nodes.successors(event, LyricSyllable, EdgeType.LYRIC):
                if not self.writer.omitted(syllable):
                    self.number_lyric_line(syllable)
        if annotations:
            self.count("annotations, which MusicXML cannot carry, left out")
        for spanner in spanners.values():
            self.place_spanner(spanner)
        self.order_bars()
        self.number_notation_spans()
        self.number_direction_spans()
        self.find_tuplets()

    def placed(self, event: SequentialEvent | None) -> _Placed | None:
        if event is None:
            return None
        placed = self.writer.placed.get(event.id)
        return placed if placed is not None and placed.unit is self.unit else None

    def place_marking(
        self, marking: Marking, voice: _Voice, onset: Fraction, event: SequentialEvent
    ) -> None:
        mark, meta = marking.mark, _meta(marking)
        on_bar_line = isinstance(event, DivisionEvent) and (onset == 0 or onset in self.ends)
        if on_bar_line and (
            mark in (scoring.segno, scoring.coda) or _fermata_shape(mark) is not None
        ):
            self.barline_marks[onset].append(mark)
            return
        if mark is scoring.simile and _meta(event).get("measure_repeat"):
            return  # the % bar says it
        if mark is scoring.breath_mark and meta.get("element") == "words":
            words = self.direction([_element("words", ",")], voice.staff)
            self.add_item(voice.staff, onset + _length(event), _DIRECTION, words, at_end=True)
            return  # a comma after the note, as the file wrote it
        if (
            isinstance(event, NoteEvent)
            and meta.get("element") != "words"
            and _notation_element(mark, meta) is not None
        ):
            # a dynamic under a note of the main line is a direction, as notation programs write it
            dynamic = _is_dynamic(mark) or meta.get("element") == "other-dynamics"
            if not (dynamic and voice.main and _length(event) > 0):
                self.notations[event.id].append((mark, meta))
                return
        position = onset + Fraction(meta.get("offset", 0))
        types = _direction_types(mark, meta)
        element = self.direction(types, voice.staff, hidden=bool(meta.get("hidden")))
        self.add_item(voice.staff, position, _DIRECTION, element)

    def direction(
        self,
        types: list[ET.Element],
        staff: int,
        hidden: bool = False,
        sound: ET.Element | None = None,
    ) -> ET.Element:
        direction = ET.Element("direction")
        if hidden:
            direction.set("print-object", "no")
        for child in types:
            _sub(direction, "direction-type").append(child)
        if self.multi_staff:
            _sub(direction, "staff", staff)
        if sound is not None:
            direction.append(sound)
        return direction

    def add_item(
        self,
        staff: int,
        position: Fraction,
        rank: int,
        element: ET.Element,
        at_end: bool = False,
        offset_ok: bool = True,
        bar: int | None = None,
    ) -> None:
        index = bar if bar is not None else self.bar_of(position, at_end)
        self.items[index].append(
            _Item(staff, position, rank, self.next_order(), element, offset_ok)
        )

    def number_lyric_line(self, syllable: LyricSyllable) -> None:
        """Each line of syllables is one `<lyric number>`: its section's, else the next free."""
        head = syllable
        while (previous := self.graph.get_previous(head)) is not None:
            head = previous  # type: ignore[assignment]
        if head.id not in self.lyric_lines:
            section = next(
                self.graph._graph.predecessors(head, LyricSection, EdgeType.STARTS_AT), None
            )
            number = name = language = None
            if section is not None:
                number = _meta(section).get("number")
                if number is None and section.section_number is not None:
                    number = str(section.section_number)
                name, language = section.section_name, section.language
            if number is None:
                used = {entry[0] for entry in self.lyric_lines.values()}
                candidate = 1
                while str(candidate) in used:
                    candidate += 1
                number = str(candidate)
            self.lyric_lines[head.id] = (str(number), name, language)
        self.lyric_lines[syllable.id] = self.lyric_lines[head.id]

    # -- spanners

    def place_spanner(self, spanner: MarkSpanner) -> None:
        start = self.graph.spanner_start(spanner)
        end = self.graph.spanner_end(spanner)
        placed_start, placed_end = self.placed(start), self.placed(end)
        if placed_start is None:
            self.count("spanners starting outside the part, left out")
            return
        if end is not None and placed_end is None:
            self.count("spanners ending outside the part, written open")
            end = None
        mark, meta = spanner.mark, _meta(spanner)
        if mark is scoring.tie:
            if end is None:
                self.count("ties with no end, left out")
                return
            tones = _shared_tones(start, end)
            self.ties_out[start.id].update(tones)
            self.ties_in[end.id].update(tones)
            self.ordered_pairs.append((start, end))
            return
        if mark in tables.NOTATION_SPAN_NAMES or mark is scoring.wavy_line:
            kind = tables.NOTATION_SPAN_NAMES.get(mark, "wavy-line")
            if not isinstance(start, NoteEvent) or (
                end is not None and not isinstance(end, NoteEvent)
            ):
                self.count(f"{kind}s not from note to note, left out")
                return
            self.notation_spans.append((kind, id(spanner), start, end, meta))
            if end is not None:
                self.ordered_pairs.append((start, end))
            return
        if meta.get("ending") or (
            mark.kind is MarkType.NAVIGATION and mark.name.startswith("ending")
        ):
            self.place_ending(spanner, placed_start, end, placed_end)
            return
        start_position = placed_start.onset + Fraction(meta.get("offset", 0))
        end_position = None
        if end is not None and placed_end is not None:
            if "end_offset" in meta:
                end_position = placed_end.onset + Fraction(meta["end_offset"])
            else:
                end_position = placed_end.onset + _length(end)
        end_staff = placed_end.voice.staff if placed_end is not None else placed_start.voice.staff
        self.direction_spans.append(
            (spanner, placed_start.voice.staff, start_position, end_staff, end_position)
        )

    def place_ending(
        self,
        spanner: MarkSpanner,
        placed_start: _Placed,
        end: SequentialEvent | None,
        placed_end: _Placed | None,
    ) -> None:
        meta = _meta(spanner).get("ending") or {}
        number = str(meta.get("number") or spanner.mark.name.removeprefix("ending").strip() or "1")
        first = self.bar_of(placed_start.onset)
        if end is not None and placed_end is not None:
            last = self.bar_of(placed_end.onset + _length(end), at_end=True)
        else:
            last = len(self.bars) - 1
        self.endings_start[first].append((number, meta.get("text")))
        self.endings_stop[last].append((number, meta.get("type") or "stop"))

    def number_notation_spans(self) -> None:
        """Slurs, glissandos and trill lines are numbered so that those open at
        once differ. One whose stop would come before its start in the file
        (a slur from a later voice back to an earlier one) is written open."""
        open_until: dict[tuple[str, int], tuple] = {}
        spans = sorted(self.notation_spans, key=lambda s: self.first_written.get(s[2].id, NEVER))
        for kind, key, start, end, meta in spans:
            begin = self.first_written.get(start.id)
            if begin is None:
                continue
            finish = self.last_written.get(end.id, NEVER) if end is not None else NEVER
            if finish < begin:
                self.count(
                    f"{kind}s ending in a voice written before the one they start in, written open"
                )
                finish, end = NEVER, None
            number = 1
            while number < MAX_NUMBER and open_until.get((kind, number), ()) >= begin:
                number += 1
            open_until[(kind, number)] = finish
            self.span_numbers[key] = str(number)
            self.span_starts[start.id].append((kind, key, meta))
            if end is not None:
                self.span_stops[end.id].append((kind, key))

    def number_direction_spans(self) -> None:
        """Hairpins, pedals, octave lines and lines of words, numbered so that
        those open at once on a staff differ. The reader pairs them by
        position, a stop before a start at one instant, so a span may take
        the number of one that ends where it starts."""
        open_until: dict[tuple[str, int, int], Fraction] = {}
        spans = sorted(enumerate(self.direction_spans), key=lambda s: (s[1][2], s[0]))
        for _, (spanner, staff, start, end_staff, end) in spans:
            kind, start_types, stop_types = self.direction_span_elements(spanner)
            numbered = kind in ("wedge", "dashes", "bracket", "pedal", "octave-shift")
            number = 1
            if kind == "pedal" and start_types[0].get("type") == "change":
                number = next(
                    (
                        n
                        for (k, s, n), until in open_until.items()
                        if (k, s, until) == (kind, staff, start)
                    ),
                    1,
                )
            else:
                while (
                    numbered
                    and number < MAX_NUMBER
                    and open_until.get((kind, staff, number), Fraction(-1)) > start
                ):
                    number += 1
            if numbered:
                open_until[(kind, staff, number)] = end if end is not None else Fraction(10**12)
                for element in [*start_types, *stop_types]:
                    if element.tag != "words":
                        element.set("number", str(number))
            self.add_item(staff, start, _DIRECTION, self.direction(start_types, staff))
            if end is not None and stop_types:
                stop = self.direction(stop_types, end_staff)
                self.add_item(end_staff, end, _DIRECTION, stop, at_end=True)

    def direction_span_elements(
        self, spanner: MarkSpanner
    ) -> tuple[str, list[ET.Element], list[ET.Element]]:
        """The kind of a direction span, and what its start and stop write."""
        mark, meta = spanner.mark, _meta(spanner)
        if mark in tables.WEDGE_TYPES:
            wedge_type, niente = tables.WEDGE_TYPES[mark]
            start = _element("wedge", type=wedge_type)
            if niente:
                start.set("niente", "yes")
            return "wedge", [start], [_element("wedge", type="stop")]
        if mark in (scoring.sustain_pedal, scoring.sostenuto_pedal):
            kind = "sostenuto" if mark is scoring.sostenuto_pedal else "start"
            if meta.get("change") and self.pedal_meets(spanner, at_start=True):
                kind = "change"
            start = _element("pedal", type=kind)
            for key in ("line", "sign"):
                if key in meta:
                    start.set(key, str(meta[key]))
            ended_by_change = self.pedal_meets(spanner, at_start=False)
            return "pedal", [start], [] if ended_by_change else [_element("pedal", type="stop")]
        shift = tables.OCTAVE_SHIFT_TYPES.get(mark)
        if (
            shift is None
            and mark.kind is MarkType.TRANSPOSITION
            and mark.name.startswith("octave shift ")
        ):
            direction, size = mark.name.removeprefix("octave shift ").split(" ")
            shift = (direction, int(size))
        if shift is not None:
            start = _element("octave-shift", type=shift[0], size=str(shift[1]))
            return (
                "octave-shift",
                [start],
                [_element("octave-shift", type="stop", size=str(shift[1]))],
            )
        if mark is scoring.una_corda:
            return "una corda", [_element("words", "una corda")], [_element("words", "tre corde")]
        kind = "bracket" if meta.get("element") == "bracket" else "dashes"
        line_end = {"line_end": "none"} if kind == "bracket" else {}
        start_types = (
            [] if kind == "bracket" and mark.name == "bracket" else [_element("words", mark.name)]
        )
        start_types.append(_element(kind, type="start", **line_end))
        return kind, start_types, [_element(kind, type="stop", **line_end)]

    def pedal_meets(self, spanner: MarkSpanner, at_start: bool) -> bool:
        """Whether a pedal change joins `spanner` to another pedal: at its
        start, one ending there; at its end, one starting there as a change."""
        mine = next(s for s in self.direction_spans if s[0] is spanner)
        for other, staff, start, end_staff, end in self.direction_spans:
            if other is spanner or other.mark not in (
                scoring.sustain_pedal,
                scoring.sostenuto_pedal,
            ):
                continue
            if at_start and end_staff == mine[1] and end == mine[2]:
                return True
            if not at_start and mine[4] is not None and _meta(other).get("change"):
                if staff == mine[3] and start == mine[4]:
                    return True
        return False

    # -- tuplets

    def find_tuplets(self) -> None:
        """`<tuplet>` brackets: the reader's record of them where it kept one,
        else every run of notes of one ratio that fills the ratio's span."""
        if any(_meta(event).get("tuplet") for _, _, event in self.all_events()):
            for _, _, event in self.all_events():
                if _meta(event).get("tuplet"):
                    self.tuplets[event.id] = _meta(event)["tuplet"]
            return
        for voice in self.unit.voices:
            run: list[SequentialEvent] = []
            ratio: TemporalRatio | None = None
            total = Fraction(0)
            for event in voice.line.events:
                duration = event.duration
                if not isinstance(event, NoteEvent) or _length(event) == 0:
                    continue
                this = duration.ratio if isinstance(duration, MetricalDuration) else None
                if this is None or (ratio is not None and this != ratio):
                    run, ratio, total = [], None, Fraction(0)
                    if this is None:
                        continue
                ratio = this
                run.append(event)
                total += duration.nominal_length  # type: ignore[union-attr]
                span = ratio.nominal.rational_length
                if total >= span:
                    if total == span and len(run) > 1:
                        self.tuplets[run[0].id] = [{"type": "start"}]
                        self.tuplets[run[-1].id] = [{"type": "stop"}]
                    run, ratio, total = [], None, Fraction(0)

    # -- contexts and harmonies, as items

    def collect_contexts(self) -> None:
        """Each staff's contexts become <attributes> and tempo <direction>s;
        those at a bar's start go in its leading block."""
        first_tempos: list[tuple[Fraction, TempoEvent]] = []
        for voice in self.unit.staves:
            passed: set[Fraction] = set()
            divisions_at = {onset for onset, _ in voice.line.divisions()}
            sounding_from = Fraction(-1)  # the onset of the last event with a length
            for onset, event in zip(voice.line.onsets, voice.line.events, strict=True):
                if _length(event):
                    sounding_from = onset
                if isinstance(event, DivisionEvent):
                    passed.add(onset)
                    continue
                if isinstance(event, NoteEvent) and _meta(event).get("sound_tempo"):
                    sound = _element("sound", tempo=str(_meta(event)["sound_tempo"]))
                    self.add_item(voice.staff, onset, _DIRECTION, sound, offset_ok=False)
                if not isinstance(event, ContextEvent):
                    continue
                if isinstance(event, TempoEvent):
                    if voice.staff == 1:
                        first_tempos.append((onset, event))
                    elif any(
                        sounding_from < position <= onset and tempo == event
                        for position, tempo in first_tempos
                    ):
                        # The reader puts a tempo on every staff of the part; where it
                        # falls inside a held note, at that note's end.
                        continue
                before_bar_line = 0 < onset and onset in divisions_at and onset not in passed
                bar = self.bar_of(onset, at_end=before_bar_line)
                if onset == self.bars[bar].start and not before_bar_line:
                    self.leading[bar].append((voice.staff, event))
                    continue
                for element in self.context_elements([(voice.staff, event)]):
                    offset_ok = element.tag == "direction"
                    self.add_item(
                        voice.staff, onset, _CONTEXT, element, offset_ok=offset_ok, bar=bar
                    )

    def context_elements(self, contexts: list[tuple[int, ContextEvent]]) -> list[ET.Element]:
        """`<attributes>` and tempo `<direction>`s for the contexts at one
        position, in the order the reader puts them back: key, time and clef
        share a block while they come in that order, and a new block starts
        when they do not. A key or time common to every staff is written once."""
        blocks: list[ET.Element] = []
        staves = sorted({staff for staff, _ in contexts})
        if not staves:
            return blocks
        by_staff: dict[int, list[ContextEvent]] = defaultdict(list)
        for staff, event in contexts:
            by_staff[staff].append(event)
        consumed: set[UUID] = set()
        attributes: ET.Element | None = None
        last_rank = -1
        for event in by_staff[staves[0]]:
            consumed.add(event.id)
            if isinstance(event, TempoEvent):
                attributes, last_rank = None, -1
                blocks.extend(self.tempo_elements(event, staves[0]))
                continue
            rank = _context_rank(event)
            if rank is None:
                self.count(f"{type(event).__name__}s, which MusicXML cannot carry, left out")
                continue
            if attributes is None or rank < last_rank:
                attributes = ET.Element("attributes")
                blocks.append(attributes)
            last_rank = rank
            others: dict[int, ContextEvent] = {}
            for staff in staves[1:]:
                match = next(
                    (
                        e
                        for e in by_staff[staff]
                        if e.id not in consumed and _context_rank(e) == rank
                    ),
                    None,
                )
                if match is not None:
                    others[staff] = match
                    consumed.add(match.id)
            shared = (
                rank < 2
                and len(others) == len(self.unit.staves) - 1
                and all(_same_context(event, other) for other in others.values())
            )
            if shared or not self.multi_staff:
                self.append_context(attributes, event, None)
            else:
                self.append_context(attributes, event, staves[0])
                for staff, other in others.items():
                    self.append_context(attributes, other, staff)
        for staff in staves[1:]:
            for event in by_staff[staff]:
                if (
                    event.id in consumed
                    or isinstance(event, TempoEvent)
                    or _context_rank(event) is None
                ):
                    continue
                attributes = next((b for b in blocks if b.tag == "attributes"), None)
                if attributes is None:
                    attributes = ET.Element("attributes")
                    blocks.insert(0, attributes)
                self.append_context(attributes, event, staff)
        for block in blocks:
            if block.tag == "attributes":
                _sort_attributes(block)
        return blocks

    def append_context(
        self, attributes: ET.Element, event: ContextEvent, staff: int | None
    ) -> None:
        number = {"number": str(staff)} if staff is not None and self.multi_staff else {}
        if isinstance(event, ModalContextEvent):
            key = _key_element(event.modal_context, number)
            if key is None:
                self.count("keys with no MusicXML signature, left out")
            else:
                attributes.append(key)
        elif isinstance(event, MeterEvent):
            attributes.append(_time_element(event, number))
        elif isinstance(event, ClefEvent):
            clef = _clef_element(event.clef, number)
            if clef is None:
                self.count("clefs that are not WSMN staff clefs, left out")
            else:
                attributes.append(clef)

    def tempo_elements(self, event: TempoEvent, staff: int) -> list[ET.Element]:
        meta = _meta(event)
        words = None
        if event.term is not None:
            words = _element("words", meta.get("term_text") or event.term.name)
        metronome = None
        if event.tempo is not None or meta.get("per_minute"):
            metronome = _metronome_element(event.tempo, meta)
            if metronome is None:
                self.count("tempos that are not beats per minute, left out")
        sound = None
        if meta.get("sound_tempo"):
            sound = _element("sound", tempo=str(meta["sound_tempo"]))
        elif isinstance(event.tempo, Tempo) and isinstance(event.tempo.nominal, TemporalUnit):
            beat = event.tempo.nominal
            sound = _element("sound", tempo=_decimal(beat.count * beat.base.rational_length * 4))
        if words is None and metronome is None:
            return [sound] if sound is not None else []
        term_hidden, tempo_hidden = bool(meta.get("term_hidden")), bool(meta.get("tempo_hidden"))
        if words is not None and metronome is not None and term_hidden != tempo_hidden:
            return [
                self.direction([words], staff, hidden=term_hidden),
                self.direction([metronome], staff, hidden=tempo_hidden, sound=sound),
            ]
        types = [e for e in (words, metronome) if e is not None]
        hidden = tempo_hidden if metronome is not None else term_hidden
        return [self.direction(types, staff, hidden=hidden, sound=sound)]

    def collect_harmonies(self) -> None:
        for staff, position, event in self.unit.harmonies:
            element = self.harmony_element(event, staff)
            if element is not None:
                self.add_item(staff, position, _HARMONY, element)

    def harmony_element(self, event: ChordEvent, staff: int) -> ET.Element | None:
        chord, meta = event.chord, _meta(event)
        root = getattr(chord, "root", None)
        if not isinstance(root, TonalVector):
            self.count("chord symbols with no root, left out")
            return None
        relative = [_minus(tone, root) for tone in chord]
        kind, degrees = _kind_and_degrees(
            relative, meta.get("kind"), getattr(chord, "name_template", None)
        )
        if kind is None:
            self.count("chord symbols of no MusicXML kind, left out")
            return None
        harmony = ET.Element("harmony")
        root_element = _sub(harmony, "root")
        step, alter = _step_alter(root)
        _sub(root_element, "root-step", step)
        if alter:
            _sub(root_element, "root-alter", alter)
        kind_element = _sub(harmony, "kind", kind)
        if meta.get("kind_text"):
            kind_element.set("text", meta["kind_text"])
        bass = getattr(chord, "bass", root)
        if isinstance(bass, TonalVector) and bass != root:
            bass_element = _sub(harmony, "bass")
            step, alter = _step_alter(bass)
            _sub(bass_element, "bass-step", step)
            if alter:
                _sub(bass_element, "bass-alter", alter)
        for value, alter, kind_of in degrees:
            degree = _sub(harmony, "degree")
            _sub(degree, "degree-value", value)
            _sub(degree, "degree-alter", alter)
            _sub(degree, "degree-type", kind_of)
        if meta.get("frame"):
            harmony.append(ET.fromstring(meta["frame"]))
        if self.multi_staff:
            _sub(harmony, "staff", staff)
        return harmony

    # -- divisions per quarter note

    def compute_divisions(self) -> int:
        """The smallest `<divisions>` that writes every duration and position whole."""
        values: list[Fraction] = []
        for by_bar in self.pieces:
            for pieces in by_bar.values():
                for piece in pieces:
                    values += [piece.onset, piece.length]
        for items in self.items.values():
            values += [item.position for item in items]
        for bar in self.bars:
            values += [bar.start, bar.end]
        return lcm(1, *((value * 4).denominator for value in values))

    def duration_value(self, length: Fraction) -> str:
        return str(int(length * 4 * self.divisions))

    # -- measures

    def write_measure(self, index: int, bar: _Bar) -> ET.Element:
        meta = _meta(bar.closing) if bar.closing is not None else {}
        measure = ET.Element("measure", number=self.measure_number(index, meta))
        if meta.get("implicit"):
            measure.set("implicit", "yes")
        if meta.get("width"):
            measure.set("width", str(meta["width"]))
        left = self.left_barline(index)
        if left is not None:
            measure.append(left)
        self.write_leading(measure, index, meta)
        items = sorted(self.items.get(index, []), key=lambda i: (i.position, i.rank, i.order))
        voices = self.unit.voices
        order = self.bar_orders[index]
        pending: dict[int, list[_Item]] = defaultdict(list)
        for item in items:
            pending[item.staff].append(item)
        carriers: dict[int, int] = {}  # the voice of each staff that writes its items
        for i in self.voice_order():
            carriers.setdefault(voices[i].staff, i)
        cursor = bar.start
        repeat = self.measure_repeat(index)
        for i in order:
            voice, pieces = voices[i], self.pieces[i].get(index, [])
            carries = carriers.get(voice.staff) == i
            if not pieces and not carries:
                continue
            staff_items = pending.pop(voice.staff, []) if carries else []
            cursor = self.back_to(measure, cursor, bar.start)
            if repeat is not None and voice.main and voice.staff == 1:
                self.flush(measure, staff_items, cursor, None)
                self.write_repeat_bar(measure, voice, bar)
                cursor = bar.end
                continue
            cursor = self.write_voice(measure, voice, pieces, bar, staff_items)
        for staff in sorted(pending):
            if pending[staff]:
                cursor = self.back_to(measure, cursor, bar.start)
                cursor = self.flush(measure, pending[staff], cursor, None)
        right = self.right_barline(index, bar)
        if right is not None:
            measure.append(right)
        return measure

    def back_to(self, measure: ET.Element, cursor: Fraction, position: Fraction) -> Fraction:
        if cursor > position:
            _sub(_sub(measure, "backup"), "duration", self.duration_value(cursor - position))
        elif cursor < position:
            _sub(_sub(measure, "forward"), "duration", self.duration_value(position - cursor))
        return position

    def measure_number(self, index: int, meta: dict) -> str:
        if meta.get("number"):
            return str(meta["number"])
        first = self.bars[0].closing
        pickup = first is not None and _meta(first).get("number") == "0"
        return str(index if pickup else index + 1)

    def measure_repeat(self, index: int) -> dict | None:
        """The reader's record of a % bar, on the event that fills it."""
        if index < 0 or not self.unit.voices or self.unit.voices[0].chords is not None:
            return None
        for piece in self.pieces[0].get(index, []):
            repeat = _meta(piece.events[0]).get("measure_repeat")
            if repeat:
                return repeat
        return None

    def write_leading(self, measure: ET.Element, index: int, meta: dict) -> None:
        blocks = self.context_elements(self.leading.get(index, []))
        styles = self.measure_styles(index, meta)
        attributes = next((block for block in blocks if block.tag == "attributes"), None)
        if attributes is None and (index == 0 or styles):
            attributes = ET.Element("attributes")
            blocks.insert(0, attributes)
        if attributes is not None:
            if index == 0:
                attributes.append(_element("divisions", self.divisions))
                if self.multi_staff:
                    attributes.append(_element("staves", len(self.unit.staves)))
                for staff in sorted(self.unit.hidden_staves):
                    details = _element("staff-details", print_object="no")
                    if self.multi_staff:
                        details.set("number", str(staff))
                    attributes.append(details)
                if self.unit.transposition is not None:
                    attributes.append(_transpose_element(self.unit.transposition))
            attributes.extend(styles)
            _sort_attributes(attributes)
        measure.extend(blocks)

    def measure_styles(self, index: int, meta: dict) -> list[ET.Element]:
        styles = []
        repeat, previous = self.measure_repeat(index), self.measure_repeat(index - 1)
        if repeat is not None and previous is None:
            style = _element("measure-style")
            element = _sub(style, "measure-repeat", repeat.get("measures") or "1", type="start")
            if repeat.get("slashes"):
                element.set("slashes", str(repeat["slashes"]))
            styles.append(style)
        elif repeat is None and previous is not None:
            style = _element("measure-style")
            _sub(style, "measure-repeat", type="stop")
            styles.append(style)
        if meta.get("multiple_rest"):
            style = _element("measure-style")
            _sub(style, "multiple-rest", meta["multiple_rest"])
            styles.append(style)
        if meta.get("slash"):
            style = _element("measure-style")
            _sub(style, "slash", type=str(meta["slash"]))
            styles.append(style)
        return styles

    def write_repeat_bar(self, measure: ET.Element, voice: _Voice, bar: _Bar) -> None:
        note = _sub(measure, "note")
        _sub(note, "rest", measure="yes")
        _sub(note, "duration", self.duration_value(bar.end - bar.start))
        _sub(note, "voice", voice.number)
        if self.multi_staff:
            _sub(note, "staff", voice.staff)

    def left_barline(self, index: int) -> ET.Element | None:
        style = repeat = None
        marks: list[Mark] = []
        if index == 0 and self.unit.staves:
            head = next((e for o, e in self.unit.staves[0].line.divisions() if o == 0), None)
            if head is not None:
                style, repeat = _left_style(head.shape)
            marks = self.barline_marks.get(Fraction(0), [])
        elif index > 0:
            previous = self.bars[index - 1].closing
            if previous is not None and previous.shape in (
                scoring.start_repeat,
                scoring.double_repeat,
            ):
                style, repeat = "heavy-light", "forward"
        endings = self.endings_start.get(index, [])
        if style is None and repeat is None and not marks and not endings:
            return None
        barline = _element("barline", location="left")
        if style is not None:
            _sub(barline, "bar-style", style)
        _append_barline_marks(barline, marks)
        for number, text in endings:
            _sub(barline, "ending", text, number=number, type="start")
        if repeat is not None:
            _sub(barline, "repeat", direction=repeat)
        return barline

    def right_barline(self, index: int, bar: _Bar) -> ET.Element | None:
        style = repeat = None
        shape = bar.closing.shape if bar.closing is not None else None
        if shape in (scoring.end_repeat, scoring.double_repeat):
            style, repeat = "light-heavy", "backward"
        elif shape is scoring.start_repeat:
            if index == len(self.bars) - 1:
                self.count("start repeats on the last bar line, written as heavy-light")
                style = "heavy-light"
        elif shape is not None:
            style = tables.BAR_STYLE_NAMES.get(shape)  # type: ignore[arg-type]
            if style is None:
                self.count("bar lines of shapes MusicXML has no name for, written as regular")
                style = "regular"
        marks = self.barline_marks.get(bar.end, []) if bar.end > 0 else []
        endings = self.endings_stop.get(index, [])
        if style is None and repeat is None and not marks and not endings:
            return None
        barline = _element("barline", location="right")
        if style is not None:
            _sub(barline, "bar-style", style)
        _append_barline_marks(barline, marks)
        for number, kind in endings:
            _sub(barline, "ending", number=number, type=kind)
        if repeat is not None:
            _sub(barline, "repeat", direction=repeat)
        return barline

    # -- one voice through one bar

    def write_voice(
        self,
        measure: ET.Element,
        voice: _Voice,
        pieces: list[_Piece],
        bar: _Bar,
        items: list[_Item],
    ) -> Fraction:
        """Writes `voice`'s pieces in `bar`, with the staff's items among them
        at their positions. A main voice is filled to the bar's end; a kit
        voice's gaps are rests, any other voice's are forwards."""
        cursor = bar.start
        for piece in pieces:
            if piece.onset > cursor:
                cursor = self.flush(measure, items, cursor, piece.onset)
                cursor = self.gap(measure, voice, cursor, piece.onset)
            elif piece.onset < cursor:
                self.count("overlapping notes in one voice, written over each other")
                cursor = self.back_to(measure, cursor, piece.onset)
            self.flush(
                measure, items, cursor, piece.onset + piece.length, inclusive=not piece.length
            )
            self.write_piece(measure, voice, piece, bar)
            cursor = piece.onset + piece.length
        cursor = self.flush(measure, items, cursor, None)
        if (voice.main or voice.chords is not None) and cursor < bar.end:
            cursor = self.gap(measure, voice, cursor, bar.end)
        return cursor

    def flush(
        self,
        measure: ET.Element,
        pending: list[_Item],
        cursor: Fraction,
        limit: Fraction | None,
        inclusive: bool = False,
    ) -> Fraction:
        """Writes the pending items before `limit` (every one when None), each
        at its position: an `<offset>` from the cursor where the element has
        one, else a forward to it and a backup after."""
        while pending:
            item = pending[0]
            if limit is not None and not (
                item.position < limit or (inclusive and item.position == limit)
            ):
                break
            pending.pop(0)
            offset = item.position - cursor
            if offset and not item.offset_ok:
                self.back_to(measure, cursor, item.position)
                measure.append(item.element)
                self.back_to(measure, item.position, cursor)
                continue
            if offset:
                value = self.duration_value(abs(offset))
                _insert_offset(item.element, value if offset > 0 else "-" + value)
            measure.append(item.element)
        return cursor

    def gap(
        self, measure: ET.Element, voice: _Voice, cursor: Fraction, until: Fraction
    ) -> Fraction:
        if voice.chords is not None:  # a kit voice: the silence between strokes is rests
            spelled = MetricalDuration.from_length(until - cursor)
            for member in spelled if isinstance(spelled, TiedDuration) else [spelled]:
                note = _sub(measure, "note")
                _sub(note, "rest")
                _sub(note, "duration", self.duration_value(member.rational_length))
                _sub(note, "voice", voice.number)
                self.write_type(note, member)
            return until
        forward = _sub(measure, "forward")
        _sub(forward, "duration", self.duration_value(until - cursor))
        _sub(forward, "voice", voice.number)
        if self.multi_staff:
            _sub(forward, "staff", voice.staff)
        return until

    def write_piece(self, measure: ET.Element, voice: _Voice, piece: _Piece, bar: _Bar) -> None:
        main = piece.events[0]
        assert isinstance(main, NoteEvent)
        meta = _meta(main)
        if piece.length == 0 and not isinstance(piece.duration, GraceDuration):
            self.count("notes of no length that are not grace notes, left out")
            return
        if not main.tones:
            if meta.get("forward") or meta.get("measure_repeat"):
                forward = _sub(measure, "forward")
                _sub(forward, "duration", self.duration_value(piece.length))
                _sub(forward, "voice", voice.number)
                if self.multi_staff:
                    _sub(forward, "staff", voice.staff)
                return
            if meta.get("slash_pitch") is not None:
                written = [tuple(p) for p in meta["slash_pitch"]] or [("B", "0", "4")]
                for i, (step, alter, octave) in enumerate(written):
                    note = self.note_start(measure, main, piece, chord=i > 0)
                    pitch = _sub(note, "pitch")
                    _sub(pitch, "step", step)
                    if str(alter) not in ("", "0"):
                        _sub(pitch, "alter", alter)
                    _sub(pitch, "octave", octave)
                    self.note_end(note, voice, main, piece, chord_level=i == 0, notehead="slash")
                return
            self.count("events of unspecified content written as rests")
            note = self.note_start(measure, main, piece)
            _sub(note, "rest")
            self.note_end(note, voice, main, piece, chord_level=True)
            return
        if main.is_rest:
            note = self.note_start(measure, main, piece)
            rest = _sub(note, "rest")
            whole = (
                voice.main
                and piece.first
                and piece.last
                and (piece.onset, piece.length)
                == (
                    bar.start,
                    bar.end - bar.start,
                )
            )
            if whole:
                rest.set("measure", "yes")
            self.note_end(note, voice, main, piece, chord_level=True, measure_rest=whole)
            return
        tones = [
            (event, tone)
            for event in piece.events
            for tone in sorted(event.tones, key=_pitch_key)  # type: ignore[attr-defined]
            if _writable_tone(tone)
        ]
        skipped = sum(len(event.tones) for event in piece.events) - len(tones)  # type: ignore[attr-defined]
        if skipped:
            self.count("tones MusicXML cannot carry (no octave, or not WSMN), left out")
        if not tones:
            note = self.note_start(measure, main, piece)
            _sub(note, "rest")
            self.note_end(note, voice, main, piece, chord_level=True)
            return
        shares = self.per_tone_shares(piece) if piece.first else {}
        for i, (event, tone) in enumerate(tones):
            note = self.note_start(measure, event, piece, chord=i > 0)
            if isinstance(tone, PercussionTone):
                unpitched = _sub(note, "unpitched")
                display = _meta(event).get("display")
                if display and display[0]:
                    _sub(unpitched, "display-step", display[0])
                    _sub(unpitched, "display-octave", display[1])
            else:
                written = (
                    tone.transpose(self.unit.transposition) if self.unit.transposition else tone
                )
                step, alter, octave = tables.pitch_of_tone(written)
                pitch = _sub(note, "pitch")
                _sub(pitch, "step", step)
                if alter:
                    _sub(pitch, "alter", alter)
                _sub(pitch, "octave", octave)
            self.note_end(
                note,
                voice,
                event,
                piece,
                tone=tone,
                chord_level=i == 0,
                tone_marks=shares.get((event.id, tone), []),
            )

    def per_tone_shares(self, piece: _Piece) -> dict[tuple[UUID, object], list[tuple[Mark, dict]]]:
        """Each tone's share of its event's per-tone marks: as many of each
        mark as every tone of the event carries alike (the rest on the lowest)."""
        shares: dict[tuple[UUID, object], list[tuple[Mark, dict]]] = defaultdict(list)
        for event in piece.events:
            marks = [(m, mm) for m, mm in self.notations.get(event.id, []) if tables.is_per_tone(m)]
            tones = sorted((t for t in event.tones if _writable_tone(t)), key=_pitch_key)  # type: ignore[attr-defined]
            if not marks or not tones:
                continue
            by_name: dict[str, list[tuple[Mark, dict]]] = defaultdict(list)
            for entry in marks:
                by_name[entry[0].name].append(entry)
            for group in by_name.values():
                each = len(group) // len(tones)
                for i, tone in enumerate(tones):
                    taken = group[i * each : (i + 1) * each]
                    if i == 0:
                        taken = taken + group[each * len(tones) :]
                    shares[(event.id, tone)].extend(taken)
        return shares

    def note_start(
        self, measure: ET.Element, event: NoteEvent, piece: _Piece, chord: bool = False
    ) -> ET.Element:
        note = _sub(measure, "note")
        meta = _meta(event)
        if meta.get("hidden"):
            note.set("print-object", "no")
        if isinstance(piece.duration, GraceDuration):
            grace = _sub(note, "grace")
            if not piece.duration.on_beat:
                grace.set("slash", "yes")
        elif meta.get("cue"):
            _sub(note, "cue")
        if chord:
            _sub(note, "chord")
        return note

    def note_end(
        self,
        note: ET.Element,
        voice: _Voice,
        event: NoteEvent,
        piece: _Piece,
        tone=None,
        chord_level: bool = False,
        tone_marks: list[tuple[Mark, dict]] = (),  # type: ignore[assignment]
        notehead: str | None = None,
        measure_rest: bool = False,
    ) -> None:
        """The rest of a `<note>` after its pitch: duration, ties, voice,
        type, staff, notations, and for the first note of a chord the chord's
        own notations and lyrics."""
        meta = _meta(event)
        grace = isinstance(piece.duration, GraceDuration)
        if not grace:
            _sub(note, "duration", self.duration_value(piece.length))
        tie_out = tie_in = False
        if tone is not None:
            tie_out = not piece.last or tone in self.ties_out.get(event.id, ())
            tie_in = not piece.first or tone in self.ties_in.get(event.id, ())
            if not meta.get("cue"):
                if tie_in:
                    _sub(note, "tie", type="stop")
                if tie_out:
                    _sub(note, "tie", type="start")
        if meta.get("instrument"):
            _sub(note, "instrument", id=str(meta["instrument"]))
        _sub(note, "voice", voice.number)
        if not measure_rest:
            self.write_type(note, piece.duration.nominal if grace else piece.duration)  # type: ignore[union-attr]
        notehead = notehead or meta.get("notehead")
        if notehead:
            _sub(note, "notehead", notehead)
        if self.multi_staff:
            _sub(note, "staff", voice.staff)
        notations = _Notations()
        if tie_in:
            notations.add(None, _element("tied", type="stop"))
        if tie_out:
            notations.add(None, _element("tied", type="start"))
        if chord_level:
            self.chord_notations(notations, piece)
        for mark, mark_meta in tone_marks:
            self.add_mark(notations, mark, mark_meta)
        if notations.root is not None:
            note.append(notations.root)
        if chord_level and piece.first:
            for event_of_piece in piece.events:
                note.extend(self.lyric_elements(event_of_piece))  # type: ignore[arg-type]

    def write_type(self, note: ET.Element, duration: Duration) -> None:
        if not isinstance(duration, MetricalDuration):
            return
        name = tables.NOTE_TYPE_NAMES.get((duration.numerator, duration.denominator))
        if name is None:
            self.count("durations with no note type, written by length only")
            return
        _sub(note, "type", name)
        for _ in range(duration.dots):
            _sub(note, "dot")
        if duration.ratio is not None:
            note.append(_time_modification(duration.ratio, duration))

    def chord_notations(self, notations: _Notations, piece: _Piece) -> None:
        """What belongs to the chord as a whole: tuplet brackets, slurs, and
        every mark that is not one tone's."""
        main = piece.events[0]
        if piece.first:
            for record in self.tuplets.get(main.id, []):
                if record.get("type") == "start":
                    notations.add(
                        None,
                        _element(
                            "tuplet", **{k.replace("-", "_"): str(v) for k, v in record.items()}
                        ),
                    )
            for event in piece.events:
                for kind, key, span_meta in self.span_starts.get(event.id, []):
                    self.add_span(notations, kind, key, "start", span_meta)
                for mark, mark_meta in self.notations.get(event.id, []):
                    if not tables.is_per_tone(mark):
                        self.add_mark(notations, mark, mark_meta)
            if _meta(main).get("accidental_mark"):
                notations.add(None, _element("accidental-mark", _meta(main)["accidental_mark"]))
        if piece.last:
            for record in self.tuplets.get(main.id, []):
                if record.get("type") == "stop":
                    notations.add(
                        None,
                        _element(
                            "tuplet", **{k.replace("-", "_"): str(v) for k, v in record.items()}
                        ),
                    )
            for event in piece.events:
                for kind, key in self.span_stops.get(event.id, []):
                    self.add_span(notations, kind, key, "stop", {})

    def add_span(
        self, notations: _Notations, kind: str, key: int, kind_of: str, meta: dict
    ) -> None:
        element = _element(kind, type=kind_of, number=self.span_numbers.get(key, "1"))
        if kind_of == "start" and meta.get("text"):
            element.text = meta["text"]
        notations.add("ornaments" if kind == "wavy-line" else None, element)

    def add_mark(self, notations: _Notations, mark: Mark, meta: dict) -> None:
        placed = _notation_element(mark, meta)
        if placed is None:
            self.count(f"marks with no place on a note ({mark.name!r}), left out")
            return
        wrapper, element = placed
        notations.add(wrapper, element)
        if wrapper == "ornaments" and meta.get("accidental_mark"):
            notations.add("ornaments", _element("accidental-mark", meta["accidental_mark"]))

    def lyric_elements(self, event: NoteEvent) -> list[ET.Element]:
        by_line: dict[str, list[LyricSyllable]] = defaultdict(list)
        info: dict[str, tuple[str | None, str | None]] = {}
        for syllable in self.graph._graph.successors(event, LyricSyllable, EdgeType.LYRIC):
            if self.writer.omitted(syllable) or syllable.id not in self.lyric_lines:
                continue
            number, name, language = self.lyric_lines[syllable.id]
            by_line[number].append(syllable)
            info[number] = (name, language)
        elements = []
        for number in sorted(by_line, key=_voice_key):
            syllables = self.in_line_order(by_line[number])
            name, language = info[number]
            lyric = _element("lyric", number=number)
            if name:
                lyric.set("name", name)
            if language:
                lyric.set(XML_LANG, language)
            for i, syllable in enumerate(syllables):
                if i:
                    _sub(lyric, "elision")
                _sub(lyric, "syllabic", _SYLLABIC[syllable.placement])
                _sub(lyric, "text", syllable.text)
            last_meta = _meta(syllables[-1])
            extend = last_meta.get("extend")
            if extend is None and self.melisma_follows(event, syllables[-1], number):
                extend = "start"
            if extend:
                _sub(lyric, "extend", **({} if extend == "start" else {"type": str(extend)}))
            for key, tag in (
                ("laughing", "laughing"),
                ("humming", "humming"),
                ("end_line", "end-line"),
                ("end_paragraph", "end-paragraph"),
            ):
                if last_meta.get(key):
                    _sub(lyric, tag)
            elements.append(lyric)
        return elements

    def in_line_order(self, syllables: list[LyricSyllable]) -> list[LyricSyllable]:
        if len(syllables) == 1:
            return syllables
        ids = {syllable.id for syllable in syllables}

        def starts(syllable: LyricSyllable) -> bool:
            previous = self.graph.get_previous(syllable)
            return previous is None or previous.id not in ids

        ordered = [next((s for s in syllables if starts(s)), syllables[0])]
        while len(ordered) < len(syllables):
            following = self.graph.get_next(ordered[-1])
            if following is None or following.id not in ids or following in ordered:
                break
            ordered.append(following)  # type: ignore[arg-type]
        return ordered + [s for s in syllables if all(s is not o for o in ordered)]

    def melisma_follows(self, event: NoteEvent, syllable: LyricSyllable, number: str) -> bool:
        """Whether a word's last syllable is held over the next sung note,
        one that begins no syllable of its line: what an extender line says."""
        if not syllable.placement.is_ending:
            return False
        following = self.graph.get_next(event)
        while following is not None and _length(following) == 0:
            following = self.graph.get_next(following)
        if not isinstance(following, NoteEvent) or following.is_rest or not following.tones:
            return False
        for other in self.graph._graph.successors(following, LyricSyllable, EdgeType.LYRIC):
            if self.lyric_lines.get(other.id, ("",))[0] == number:
                return False
        return True


class _Notations:
    """A `<notations>` element, grouping articulations, ornaments, technical
    marks and dynamics in their wrappers."""

    def __init__(self) -> None:
        self.root: ET.Element | None = None
        self.wrappers: dict[str, ET.Element] = {}

    def add(self, wrapper: str | None, element: ET.Element) -> None:
        if self.root is None:
            self.root = ET.Element("notations")
        if wrapper is None:
            self.root.append(element)
            return
        if wrapper not in self.wrappers:
            self.wrappers[wrapper] = _sub(self.root, wrapper)
        self.wrappers[wrapper].append(element)


# --- marks -------------------------------------------------------------------------------------


def _fermata_shape(mark: Mark) -> str | None:
    """The `<fermata>` text of a fermata mark ("" for the normal one), else None."""
    entry = tables.NOTATION_ELEMENTS.get(mark)
    if entry is not None and entry[1] == "fermata":
        return entry[2] or ""
    return None


def _is_ready_made(mark: Mark) -> bool:
    """Whether the reader finds `mark` again by its name (a WSMN symbol, not a minted mark)."""
    return tables.WORDS.get(tables.normalize_words(mark.name)) == mark


def _is_dynamic(mark: Mark) -> bool:
    return mark in tables.DYNAMIC_NAMES or mark.kind is MarkType.DYNAMIC


_XML_NAME = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")


def _notation_element(mark: Mark, meta: dict) -> tuple[str | None, ET.Element] | None:
    """The element that writes `mark` inside `<notations>`, with its wrapper
    (`articulations`, `ornaments`, ...), or None for a mark written as a
    `<direction>`. The inverse of the reader's notation tables, minted marks
    included (a mark the reader minted is written as the element it came from)."""
    if meta.get("element") == "other-dynamics":
        return "dynamics", _element("other-dynamics", mark.name)
    entry = tables.NOTATION_ELEMENTS.get(mark)
    if entry is not None:
        wrapper, name, text = entry
        element = _element(name, text)
        if name == "tremolo":
            element.set("type", str(meta.get("tremolo_type") or "single"))
            element.text = str(meta.get("tremolo") or "3")
        if name == "fermata" and meta.get("fermata_type"):
            element.set("type", str(meta["fermata_type"]))
        if meta.get("type") in ("start", "stop"):
            element.set("type", meta["type"])
        return wrapper, element
    if mark in tables.ARPEGGIO_DIRECTIONS:
        direction = tables.ARPEGGIO_DIRECTIONS[mark]
        return None, _element("arpeggiate", **({"direction": direction} if direction else {}))
    if mark is scoring.laissez_vibrer:
        return None, _element("tied", type="let-ring")
    if mark in tables.HARMON_MUTE_STATES:
        element = _element("harmon-mute")
        _sub(element, "harmon-closed", tables.HARMON_MUTE_STATES[mark])
        return "technical", element
    if mark in tables.HOLE_STATES:
        element = _element("hole")
        _sub(element, "hole-closed", tables.HOLE_STATES[mark])
        return "technical", element
    if mark in tables.DYNAMIC_NAMES:
        return "dynamics", _element(tables.DYNAMIC_NAMES[mark])
    match mark.kind:
        case MarkType.DYNAMIC:
            if not _is_ready_made(mark) and set(mark.name) <= _XML_NAME and mark.name[:1].isalpha():
                return "dynamics", _element(mark.name)  # minted by the reader from this element
            return "dynamics", _element("other-dynamics", mark.name)
        case MarkType.ARTICULATION:
            return "articulations", _element("other-articulation", mark.name)
        case MarkType.ORNAMENT:
            return "ornaments", _element("other-ornament", mark.name)
        case MarkType.TECHNIQUE:
            if mark.name == "arrow":
                return "technical", _element("arrow")
            return "technical", _element("other-technical", mark.name)
        case MarkType.FINGERING:
            prefix, _, rest = mark.name.partition(" ")
            if prefix in tables.MINTED_PER_TONE_PREFIXES:
                text = meta.get("fingering", rest) if prefix == "fingering" else rest
                return "technical", _element(prefix, text)
            return "technical", _element("other-technical", mark.name)
        case MarkType.PHRASING if mark.name.startswith("fermata (") and mark.name.endswith(")"):
            return None, _element("fermata", mark.name[len("fermata (") : -1])
        case MarkType.OTHER if meta.get("element") == "other-notation":
            return None, _element("other-notation", mark.name, type="single")
    return None


def _direction_types(mark: Mark, meta: dict) -> list[ET.Element]:
    """The `<direction-type>` contents that say `mark`."""
    if meta.get("element") == "words":
        return [_element("words", meta.get("text") or mark.name)]
    if meta.get("element") == "other-dynamics":
        dynamics = _element("dynamics")
        _sub(dynamics, "other-dynamics", mark.name)
        return [dynamics]
    if _is_dynamic(mark) and mark not in tables.DYNAMIC_NAMES and _is_ready_made(mark):
        return [_element("words", mark.name)]  # "cresc.", "sff": words the reader looks up
    if _is_dynamic(mark):
        placed = _notation_element(mark, {})
        dynamics = _element("dynamics")
        dynamics.append(placed[1] if placed is not None else _element("other-dynamics", mark.name))
        return [dynamics]
    if mark.kind is MarkType.REHEARSAL:
        return [_element("rehearsal", mark.name)]
    for symbol, tag in (
        (scoring.segno, "segno"),
        (scoring.coda, "coda"),
        (scoring.eyeglasses, "eyeglasses"),
        (scoring.damp, "damp"),
        (scoring.damp_all, "damp-all"),
    ):
        if mark is symbol:
            return [_element(tag)]
    if mark is scoring.con_sordino:
        return [_element("string-mute", type="on")]
    if mark is scoring.senza_sordino:
        return [_element("string-mute", type="off")]
    return [_element("words", mark.name)]


def _append_barline_marks(barline: ET.Element, marks: list[Mark]) -> None:
    """Segno, coda and fermatas, in the order a `<barline>` holds them."""
    for symbol, tag in ((scoring.segno, "segno"), (scoring.coda, "coda")):
        if any(mark is symbol for mark in marks):
            _sub(barline, tag)
    for mark in marks:
        shape = _fermata_shape(mark)
        if shape is not None:
            _sub(barline, "fermata", shape or None)


def _left_style(shape) -> tuple[str | None, str | None]:
    if shape is None:
        return None, None
    if shape in (scoring.start_repeat, scoring.double_repeat):
        return "heavy-light", "forward"
    return tables.BAR_STYLE_NAMES.get(shape, "regular"), None


def _shared_tones(start: SequentialEvent, end: SequentialEvent) -> set:
    """The tones a tie joins: those the two notes share (all of both when
    they share none, as for an enharmonic tie)."""
    first = set(getattr(start, "tones", ()))
    second = set(getattr(end, "tones", ()))
    return (first & second) or (first | second)


# --- contexts ---------------------------------------------------------------------------------


def _context_rank(event: ContextEvent) -> int | None:
    """Where a context goes in `<attributes>` (key, time, clef), or None."""
    if isinstance(event, ModalContextEvent):
        return 0
    if isinstance(event, MeterEvent):
        return 1
    if isinstance(event, ClefEvent):
        return 2
    return None


def _same_context(a: ContextEvent, b: ContextEvent) -> bool:
    if isinstance(a, ModalContextEvent) and isinstance(b, ModalContextEvent):
        return a.modal_context == b.modal_context
    if isinstance(a, MeterEvent) and isinstance(b, MeterEvent):
        same_spelling = getattr(a.meter, "presentation", None) == getattr(
            b.meter, "presentation", None
        )
        return a.meter == b.meter and same_spelling and _meta(a) == _meta(b)
    return False


_ATTRIBUTE_ORDER = {
    tag: i
    for i, tag in enumerate(
        (
            "divisions",
            "key",
            "time",
            "staves",
            "part-symbol",
            "instruments",
            "clef",
            "staff-details",
            "transpose",
            "directive",
            "measure-style",
        )
    )
}


def _sort_attributes(attributes: ET.Element) -> None:
    children = sorted(attributes, key=lambda child: _ATTRIBUTE_ORDER.get(child.tag, 99))
    for child in list(attributes):
        attributes.remove(child)
    attributes.extend(children)


def _key_element(context, number: dict) -> ET.Element | None:
    if not isinstance(context, Key):
        return None
    key = ET.Element("key", number)
    if context.signature is None:
        _sub(key, "fifths", 0)
        _sub(key, "mode", "none")
        return key
    try:
        fifths = context.signature.fifths
    except ValueError:
        return None
    _sub(key, "fifths", fifths)
    if context.mode is not None and context.mode in tables.MODE_NAMES:
        _sub(key, "mode", tables.MODE_NAMES[context.mode])
    return key


def _time_element(event: MeterEvent, number: dict) -> ET.Element:
    time = ET.Element("time", number)
    if _meta(event).get("symbol"):
        time.set("symbol", str(_meta(event)["symbol"]))
    if event.meter is None:
        _sub(time, "senza-misura")
        return time
    for beats, beat_type in _time_pairs(event.meter):
        _sub(time, "beats", beats)
        _sub(time, "beat-type", beat_type)
    return time


def _time_pairs(meter: Measurable) -> list[tuple[str, str]]:
    """`<beats>`/`<beat-type>` pairs for a meter: its presentation when it has
    one, else its units grouped by beat, else its length as a fraction."""
    presentation = getattr(meter, "presentation", None)
    groups = _unit_groups(meter)
    if presentation is not None:
        beats, types = presentation
        type_parts = types.split("+")
        if len(type_parts) == 1:
            return [(beats, types)]
        if groups is not None and len(groups) == len(type_parts):
            return [
                ("+".join(str(c) for c in counts), part)
                for (counts, _), part in zip(groups, type_parts, strict=True)
            ]
        beat_parts = beats.split("+")
        if len(beat_parts) == len(type_parts):
            return list(zip(beat_parts, type_parts, strict=True))
        return [(beats, types)]
    if groups is not None:
        return [
            ("+".join(str(c) for c in counts), str(denominator)) for counts, denominator in groups
        ]
    length = meter.rational_length
    return [(str(length.numerator), str(length.denominator))]


def _unit_groups(meter: Measurable) -> list[tuple[list[int], int]] | None:
    """A time signature's units as runs of counts of one plain beat."""
    if not isinstance(meter, TimeSignature):
        return None
    groups: list[tuple[list[int], int]] = []
    for unit in meter.units:
        base = getattr(unit, "base", None)
        plain = (
            isinstance(unit, TemporalUnit)
            and isinstance(base, MetricalDuration)
            and base.numerator == 1
            and not base.dots
            and base.ratio is None
        )
        if not plain:
            return None
        if groups and groups[-1][1] == base.denominator:  # type: ignore[union-attr]
            groups[-1][0].append(unit.count)  # type: ignore[union-attr]
        else:
            groups.append(([unit.count], base.denominator))  # type: ignore[union-attr]
    return groups


def _clef_element(clef, number: dict) -> ET.Element | None:
    if not isinstance(clef, StaffClef) or clef.sign not in tables.CLEF_SIGN_NAMES:
        return None
    element = ET.Element("clef", number)
    _sub(element, "sign", tables.CLEF_SIGN_NAMES[clef.sign])
    if clef.line is not None:
        _sub(element, "line", clef.line)
    if clef.octave_change:
        _sub(element, "clef-octave-change", clef.octave_change)
    return element


def _transpose_element(transposition: TonalVector) -> ET.Element:
    """`<transpose>` for a Stint's transposition (written minus sounding):
    the interval from written to sounding pitch, as diatonic and chromatic
    steps within an octave, and an octave change.

    >>> from openmusickit.systems.wsmn.tonal.symbols import P5
    >>> ET.tostring(_transpose_element(TonalVector((1, 2, 0)))).decode()  # a clarinet in B♭
    '<transpose><diatonic>-1</diatonic><chromatic>-2</chromatic></transpose>'
    >>> ET.tostring(_transpose_element(TonalVector((0, 0, 1)))).decode()  # a guitar
    '<transpose><diatonic>0</diatonic><chromatic>0</chromatic><octave-change>-1</octave-change></transpose>'
    """
    interval = ORIGIN - transposition
    total_diatonic = interval.d + 7 * interval.o
    expected = 12 * (total_diatonic // 7) + tables.STEP_CHROMATIC[total_diatonic % 7]
    total_chromatic = interval.c + 12 * interval.o
    while total_chromatic - expected > 6:
        total_chromatic -= 12
    while expected - total_chromatic > 6:
        total_chromatic += 12
    octave_change = int(total_diatonic / 7)  # toward zero, as transpositions are written
    element = ET.Element("transpose")
    _sub(element, "diatonic", total_diatonic - 7 * octave_change)
    _sub(element, "chromatic", total_chromatic - 12 * octave_change)
    if octave_change:
        _sub(element, "octave-change", octave_change)
    return element


def _metronome_element(tempo: TemporalRatio | None, meta: dict) -> ET.Element | None:
    metronome = ET.Element("metronome")
    if meta.get("parentheses"):
        metronome.set("parentheses", "yes")
    if isinstance(tempo, Tempo) and isinstance(tempo.nominal, TemporalUnit):
        if not _beat_unit(metronome, tempo.nominal.base):
            return None
        _sub(metronome, "per-minute", tempo.nominal.count)
        return metronome
    if tempo is not None:
        if not (_beat_unit(metronome, tempo.contextual) and _beat_unit(metronome, tempo.nominal)):
            return None
        return metronome
    if meta.get("per_minute"):
        _beat_unit(metronome, MetricalDuration(1, 4))
        _sub(metronome, "per-minute", meta["per_minute"])
        return metronome
    return None


def _beat_unit(metronome: ET.Element, beat) -> bool:
    if not isinstance(beat, MetricalDuration):
        return False
    name = tables.NOTE_TYPE_NAMES.get((beat.numerator, beat.denominator))
    if name is None:
        return False
    _sub(metronome, "beat-unit", name)
    for _ in range(beat.dots):
        _sub(metronome, "beat-unit-dot")
    return True


def _decimal(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{float(value):.4f}".rstrip("0").rstrip(".")


# --- notes ------------------------------------------------------------------------------------


def _writable_tone(tone) -> bool:
    return isinstance(tone, PercussionTone) or (isinstance(tone, TonalVector) and tone.has_octave)


def _pitch_key(tone) -> tuple:
    if isinstance(tone, TonalVector) and tone.has_octave:
        return (0, tone.o * 12 + tone.c, tone.d)
    return (1, 0, repr(tone))


def _time_modification(ratio: TemporalRatio, duration: MetricalDuration) -> ET.Element:
    """`<time-modification>`: the counts and base the ratio was built from
    where it has them, else its multiplier in lowest terms."""
    element = ET.Element("time-modification")
    nominal, contextual = ratio.nominal, ratio.contextual
    base = None
    if (
        isinstance(nominal, TemporalUnit)
        and isinstance(contextual, TemporalUnit)
        and nominal.base == contextual.base
    ):
        actual, normal, base = nominal.count, contextual.count, contextual.base
    else:
        multiplier = ratio.multiplier
        actual, normal = multiplier.denominator, multiplier.numerator
    _sub(element, "actual-notes", actual)
    _sub(element, "normal-notes", normal)
    if isinstance(base, MetricalDuration) and (base.numerator, base.denominator, base.dots) != (
        duration.numerator,
        duration.denominator,
        0,
    ):
        name = tables.NOTE_TYPE_NAMES.get((base.numerator, base.denominator))
        if name is not None:
            _sub(element, "normal-type", name)
            for _ in range(base.dots):
                _sub(element, "normal-dot")
    return element


def _insert_offset(element: ET.Element, value: str) -> None:
    """An `<offset>` in its place: before `<staff>` and `<sound>`."""
    offset = _element("offset", value)
    for index, child in enumerate(element):
        if child.tag in ("footnote", "level", "voice", "staff", "sound", "listening"):
            element.insert(index, offset)
            return
    element.append(offset)


# --- chord symbols ----------------------------------------------------------------------------


def _minus(tone: TonalVector, root: TonalVector) -> TonalVector:
    difference = tone - root
    return TonalVector((difference.d, difference.c))


def _alter_of(tone: TonalVector) -> int:
    return (tone.c - tables.STEP_CHROMATIC[tone.d] + 6) % 12 - 6


def _step_alter(tone: TonalVector) -> tuple[str, int]:
    return tables.STEPS[tone.d], _alter_of(tone)


def _kind_and_degrees(
    tones: list[TonalVector], recorded: str | None, name: str | None
) -> tuple[str | None, list[tuple[int, int, str]]]:
    """The MusicXML kind of a chord (its tones measured from the root) and
    the `<degree>`s that make it from that kind: the kind the reader recorded
    when it still fits, else one that fits exactly, else the one needing the
    fewest degrees."""
    best: tuple[str, list[tuple[int, int, str]]] | None = None
    candidates = ([recorded] if recorded in tables.KINDS else []) + list(tables.KINDS)
    for kind in candidates:
        degrees = _degrees_from(list(tables.KINDS[kind]), tones, name if kind == recorded else None)
        if degrees is None:
            continue
        if kind == recorded or not degrees:
            return kind, degrees
        if best is None or len(degrees) < len(best[1]):
            best = (kind, degrees)
    return best if best is not None else (None, [])


def _degrees_from(
    base: list[TonalVector], tones: list[TonalVector], name: str | None
) -> list[tuple[int, int, str]] | None:
    """The degrees (value, alter, type) that turn `base` into `tones` as the
    reader applies them (alter in place, subtract, add at the end), or None.
    The reader's own labels, from the chord type's name, are used when they
    rebuild the same tones."""
    labelled = _recorded_degrees(name)
    if labelled is not None and _apply_degrees(base, labelled) == tones:
        return labelled
    degrees: list[tuple[int, int, str]] = []
    result = list(base)
    by_degree = {tone.d: tone for tone in tones}
    for tone in base:
        if tone.d not in by_degree:
            degrees.append((tone.d + 1, 0, "subtract"))
            result.remove(tone)
        elif by_degree[tone.d] != tone:
            degrees.append((tone.d + 1, _alter_of(by_degree[tone.d]), "alter"))
            result[result.index(tone)] = by_degree[tone.d]
    for tone in tones:
        if tone not in result:
            degrees.append((tone.d + 1 + (7 if tone.d in (1, 3, 5) else 0), _alter_of(tone), "add"))
            result.append(tone)
    return degrees if result == tones else None


def _apply_degrees(
    base: list[TonalVector], degrees: list[tuple[int, int, str]]
) -> list[TonalVector]:
    """`base` with `degrees` applied the way the reader applies them."""
    tones = list(base)
    for value, alter, kind in degrees:
        index = (value - 1) % 7
        tone = TonalVector((index, (tables.STEP_CHROMATIC[index] + alter) % 12))
        if kind == "subtract":
            tones = [t for t in tones if t.d != index]
        elif kind == "alter" and any(t.d == index for t in tones):
            tones = [tone if t.d == index else t for t in tones]
        elif tone not in tones:
            tones.append(tone)
    return tones


def _recorded_degrees(name: str | None) -> list[tuple[int, int, str]] | None:
    """The degrees in the name the reader gives a degree-altered chord type,
    `"dominant (add 9, alter -15)"` (alter, then value), or None."""
    if not name or not name.endswith(")") or " (" not in name:
        return None
    degrees = []
    for label in name[name.rindex(" (") + 2 : -1].split(", "):
        kind, _, rest = label.partition(" ")
        if kind not in ("add", "alter", "subtract") or not rest:
            return None
        if rest[0] in "+-" and rest[1:].isdigit() and len(rest) > 2:
            alter, value = int(rest[:2]), int(rest[2:])
        elif rest.isdigit():
            alter, value = 0, int(rest)
        else:
            return None
        degrees.append((value, alter, kind))
    return degrees
