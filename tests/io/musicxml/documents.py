"""Builders for the small MusicXML documents the reader tests read,
and short readers for what they become on the graph.

`doc` wraps measure bodies in a valid `<score-partwise>` skeleton,
so a test shows only the element under test;
`note` and `rest` write one `<note>` each;
`read_doc` and `read_with_warnings` read the document straight from memory.
The readers (`main_line`, `notes_of`, `onsets_of`, `markings_on`, ...)
name the parts of the graph the tests assert on.
"""

from __future__ import annotations

import io
import warnings
from collections.abc import Iterable, Mapping, Sequence
from fractions import Fraction

from openmusickit.errors import OmkWarning
from openmusickit.graph.edge import EdgeType
from openmusickit.graph.graph import OmkGraph
from openmusickit.io.musicxml import read
from openmusickit.objects.marking import Marking, MarkSpanner
from openmusickit.objects.note_event import NoteEvent
from openmusickit.objects.omk_object import SequentialEvent
from openmusickit.objects.part import LineGroup, Part, PercussionPart, Stint
from openmusickit.objects.score import Score

DEFAULT_ATTRIBUTES = (
    "<key><fifths>0</fifths></key>"
    "<time><beats>4</beats><beat-type>4</beat-type></time>"
    "<clef><sign>G</sign><line>2</line></clef>"
)

# A measure body may be given as (attributes, body) to replace the default
# `number="n"` on the <measure> element; `measure` builds that pair.
MeasureSpec = str | tuple[str, str]


def measure(body: str, **attrs: str) -> tuple[str, str]:
    """A measure body with its own `<measure>` attributes (`number="0"`, `implicit="yes"`)."""
    attributes = " ".join(f'{key.replace("_", "-")}="{value}"' for key, value in attrs.items())
    return attributes, body


def doc(
    *measures: MeasureSpec | Sequence[MeasureSpec] | Mapping[str, Sequence[MeasureSpec]],
    parts: Sequence[str] = ("P1",),
    part_names: Mapping[str, str] | Sequence[str] | None = None,
    divisions: int = 4,
    attributes: str | None | Mapping[str, str | None] = DEFAULT_ATTRIBUTES,
    header: str = "",
    part_list_extra: Mapping[str, str] | None = None,
    part_list: str | None = None,
) -> bytes:
    """A `<score-partwise>` document around measure bodies.

    One part: `doc(body1, body2, ...)`.
    Several parts: `doc({"P1": [...], "P2": [...]})` or `doc([...], [...], parts=("P1", "P2"))`.
    The first measure of each part gets `<attributes>` with `divisions` and
    `attributes` (a string for every part or a mapping by part id) unless
    `attributes` is None. `header` goes before `<part-list>`;
    `part_list_extra` adds XML inside a part's `<score-part>`;
    `part_list`, if given, is the whole content of `<part-list>`, written by hand.
    """
    if len(measures) == 1 and isinstance(measures[0], Mapping):
        bodies: dict[str, Sequence[MeasureSpec]] = dict(measures[0])
        parts = tuple(bodies)
    elif measures and all(isinstance(m, list) for m in measures):
        bodies = dict(zip(parts, measures, strict=True))  # one list of measures per part
    else:
        bodies = {parts[0]: list(measures)}  # type: ignore[arg-type]
    if part_names is None:
        names = {part: part for part in parts}
    elif isinstance(part_names, Mapping):
        names = dict(part_names)
    else:
        names = dict(zip(parts, part_names, strict=True))
    extra = dict(part_list_extra or {})
    if part_list is None:
        part_list = "".join(
            f'<score-part id="{part}"><part-name>{names[part]}</part-name>{extra.get(part, "")}'
            "</score-part>"
            for part in parts
        )
    part_elements = []
    for part in parts:
        part_attributes = attributes.get(part) if isinstance(attributes, Mapping) else attributes
        part_elements.append(
            f'<part id="{part}">'
            + "".join(
                _measure_xml(index, spec, divisions, part_attributes)
                for index, spec in enumerate(bodies[part])
            )
            + "</part>"
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<score-partwise version="4.0">{header}<part-list>{part_list}</part-list>'
        + "".join(part_elements)
        + "</score-partwise>"
    )
    return xml.encode("utf-8")


def _measure_xml(index: int, spec: MeasureSpec, divisions: int, attributes: str | None) -> str:
    if isinstance(spec, tuple):
        attrs, body = spec
    else:
        attrs, body = f'number="{index + 1}"', spec
    if index == 0 and attributes is not None:
        body = f"<attributes><divisions>{divisions}</divisions>{attributes}</attributes>" + body
    return f"<measure {attrs}>{body}</measure>"


def note(
    step: str,
    octave: int,
    duration: int,
    type_name: str,
    *,
    alter: int | None = None,
    voice: int | str = 1,
    staff: int | None = None,
    chord: bool = False,
    dots: int = 0,
    tie: str | None = None,
    grace: bool | str = False,
    time_modification: str = "",
    notehead: str | None = None,
    extra: str = "",
    attrs: str = "",
) -> str:
    """One `<note>` with a pitch. `tie` is "start", "stop" or "continue"
    and writes both `<tie>` and `<notations><tied>`; `grace` may be True or
    "slash"; `extra` (notations, lyrics, instrument) goes at the end."""
    parts = [f"<note {attrs}>" if attrs else "<note>"]
    if grace:
        parts.append('<grace slash="yes"/>' if grace == "slash" else "<grace/>")
    if chord:
        parts.append("<chord/>")
    alter_xml = f"<alter>{alter}</alter>" if alter is not None else ""
    parts.append(f"<pitch><step>{step}</step>{alter_xml}<octave>{octave}</octave></pitch>")
    if not grace:
        parts.append(f"<duration>{duration}</duration>")
    if tie:
        parts.append(f'<tie type="{tie}"/>')
    parts.append(f"<voice>{voice}</voice><type>{type_name}</type>")
    parts.append("<dot/>" * dots)
    parts.append(time_modification)
    if notehead:
        parts.append(f"<notehead>{notehead}</notehead>")
    if staff is not None:
        parts.append(f"<staff>{staff}</staff>")
    if tie:
        parts.append(f'<notations><tied type="{tie}"/></notations>')
    parts.append(extra)
    parts.append("</note>")
    return "".join(parts)


def rest(
    duration: int,
    type_name: str | None = None,
    *,
    voice: int | str = 1,
    staff: int | None = None,
    dots: int = 0,
    whole_measure: bool = False,
    extra: str = "",
    attrs: str = "",
) -> str:
    """One `<rest>` note; `whole_measure` writes `<rest measure="yes"/>`."""
    parts = [f"<note {attrs}>" if attrs else "<note>"]
    parts.append('<rest measure="yes"/>' if whole_measure else "<rest/>")
    parts.append(f"<duration>{duration}</duration><voice>{voice}</voice>")
    if type_name:
        parts.append(f"<type>{type_name}</type>")
    parts.append("<dot/>" * dots)
    if staff is not None:
        parts.append(f"<staff>{staff}</staff>")
    parts.append(extra)
    parts.append("</note>")
    return "".join(parts)


def tuplet_of(actual: int, normal: int, normal_type: str | None = None) -> str:
    """A `<time-modification>` element."""
    base = f"<normal-type>{normal_type}</normal-type>" if normal_type else ""
    return (
        f"<time-modification><actual-notes>{actual}</actual-notes>"
        f"<normal-notes>{normal}</normal-notes>{base}</time-modification>"
    )


def direction(
    *types: str, staff: int | None = None, offset: int | None = None, sound: str = ""
) -> str:
    """A `<direction>` holding one `<direction-type>` per item of `types`."""
    inner = "".join(f"<direction-type>{item}</direction-type>" for item in types)
    if offset is not None:
        inner += f"<offset>{offset}</offset>"
    if staff is not None:
        inner += f"<staff>{staff}</staff>"
    return f"<direction>{inner}{sound}</direction>"


def lyric(text: str, syllabic: str | None = None, number: int | str = 1, extra: str = "") -> str:
    """A `<lyric>` with one `<text>`, and a `<syllabic>` flag when given."""
    flag = f"<syllabic>{syllabic}</syllabic>" if syllabic else ""
    return f'<lyric number="{number}">{flag}<text>{text}</text>{extra}</lyric>'


# --- reading ---------------------------------------------------------------------


def read_bytes(data: bytes) -> OmkGraph:
    """The graph read from an in-memory document."""
    return read(io.BytesIO(data))


def read_doc(*args, **kwargs) -> OmkGraph:
    """`read` of `doc(*args, **kwargs)`, with warnings left to pytest."""
    return read_bytes(doc(*args, **kwargs))


def read_with_warnings(*args, **kwargs) -> tuple[OmkGraph, list[str]]:
    """`read_doc` plus the messages of every `OmkWarning` it raised, in order."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        graph = read_doc(*args, **kwargs)
    messages = [str(w.message) for w in caught if issubclass(w.category, OmkWarning)]
    return graph, messages


# --- reading the graph back --------------------------------------------------------


def score_of(graph: OmkGraph) -> Score:
    """The graph's one Score."""
    (score,) = graph.nodes(Score)
    return score


def stack_of(graph: OmkGraph) -> list[Part | LineGroup]:
    """The Score's stack, top to bottom: each `<score-part>`'s Part, or a drum kit's group."""
    member = next(iter(graph.score_parts(score_of(graph))))
    if isinstance(member, PercussionPart):
        (head,) = lines_of_part(graph, member)
        (member,) = graph.groups_of(head)
    while (above := graph.stacked_above(member)) is not None:
        member = above
    return list(graph.walk_stack(member))


def parts_of(graph: OmkGraph) -> list[Part]:
    """The Score's Parts in part-list order (its stack), drum kits left out."""
    return [member for member in stack_of(graph) if isinstance(member, Part)]


def lines_of_part(graph: OmkGraph, part: Part) -> list[SequentialEvent]:
    """The heads of the top-level lines `part` performs, staff order first:
    the start of each stint, or every member of each performed group."""
    heads: list[SequentialEvent] = []
    for stint in graph.stints(part):
        heads.extend(graph._graph.successors(stint, SequentialEvent, EdgeType.STARTS_AT))
    for group in graph.groups(part):
        heads.extend(graph.group_members(group))
    return sorted(heads, key=lambda head: head.meta.get("musicxml", {}).get("staff", 1))


def main_line(graph: OmkGraph, part_index: int = 0, staff: int = 1) -> SequentialEvent:
    """The head of the main line of `staff` in the part at `part_index`."""
    part = parts_of(graph)[part_index]
    for head in lines_of_part(graph, part):
        if head.meta.get("musicxml", {}).get("staff", 1) == staff:
            return head
    raise LookupError(f"part {part.name!r} has no staff {staff}")


def events_of(graph: OmkGraph, head: SequentialEvent) -> list[SequentialEvent]:
    """The events of the line from `head`, in order."""
    return list(graph.walk_line(head))


def notes_of(graph: OmkGraph, head: SequentialEvent) -> list[NoteEvent]:
    """The NoteEvents (notes, rests and fillers) of the line from `head`."""
    return [event for event in graph.walk_line(head) if isinstance(event, NoteEvent)]


def kinds_of(events: Iterable[SequentialEvent]) -> list[str]:
    """The class name of each event."""
    return [type(event).__name__ for event in events]


def names_of(events: Iterable[NoteEvent]) -> list[str]:
    """Each event's tones as pitch names (`'C4'`, `'C4+E4'`), `'rest'` for a
    rest and `''` for an event with no tones."""
    return [
        "rest" if event.is_rest else "+".join(sorted(format(tone) for tone in event.tones))
        for event in events
    ]


def onsets_of(graph: OmkGraph, head: SequentialEvent) -> list[Fraction]:
    """The onset of each event of the line from `head`, in whole notes."""
    onsets = graph.onsets(head)
    return [onsets[event.id].rational_length for event in graph.walk_line(head)]


def onset_of(graph: OmkGraph, reference: SequentialEvent, event: SequentialEvent) -> Fraction:
    """How far after `reference` the `event` starts, in whole notes."""
    return graph.relative_onset(reference, event).rational_length


def branches(
    graph: OmkGraph, head: SequentialEvent
) -> list[tuple[SequentialEvent, SequentialEvent]]:
    """(parent, branched head) for every branch off the line from `head`."""
    found = []
    for event in graph.walk_line(head):
        for branch in graph.branches_from(event):
            found.append((event, branch))
    return found


def markings_on(graph: OmkGraph, event: SequentialEvent) -> list[Marking]:
    """The Markings placed on `event`."""
    return list(graph._graph.predecessors(event, Marking, EdgeType.MARKS))


def mark_names_on(graph: OmkGraph, event: SequentialEvent) -> list[str]:
    """The names of the marks on `event`, sorted."""
    return sorted(marking.mark.name for marking in markings_on(graph, event))


def spanners_named(graph: OmkGraph, name: str) -> list[MarkSpanner]:
    """Every MarkSpanner on the graph whose mark has `name`."""
    return [spanner for spanner in graph.nodes(MarkSpanner) if spanner.mark.name == name]


def xml_meta_of(node) -> dict:
    """`node.meta["musicxml"]`, or an empty dict when the reader left none."""
    return node.meta.get("musicxml", {})


def groups_of_score(graph: OmkGraph) -> list[LineGroup]:
    return list(graph.nodes(LineGroup))


def stint_of(graph: OmkGraph, part: Part) -> Stint:
    (stint,) = graph.stints(part)
    return stint
