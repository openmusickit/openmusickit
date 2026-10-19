"""Comparing MusicXML documents for the music they hold, not how they spell it.

`canonicalize` reduces a `<score-partwise>` to a canonical form, and
`compare` lists the `Difference`s between two canonical forms. Two exports
of one score by different programs, or a file and the writer's version of
what the reader made of it, differ in a hundred ways that say nothing about
the music: the order of voices in a measure, `<divisions>`, numbering, where
a direction sits among the notes. Those are normalized away, in this order:

1. Presentation is dropped: the elements `_plans/musicxml.md` §5.10 lists
   (`<defaults>`, `<print>`, layouts, `<appearance>`, `<credit>`, MIDI
   devices, `<bookmark>`, `<link>`, `<figured-bass>`), `<sound>`,
   `<encoding>`, positions, fonts, colours, `placement`, `<stem>`, `<beam>`,
   `<accidental>`, noteheads other than slash, and ids.
2. Each measure becomes a flat list of items, each at an explicit position:
   its distance from the measure's start in whole notes, folding in any
   `<offset>`. So `<backup>`, `<forward>` and `<divisions>` disappear, and a
   `<forward>` and a hidden rest are alike: both leave nothing.
3. Voices are renumbered per staff by first appearance; measures by their
   index (`implicit` dropped); parts P1, P2, ... in order; numbered spans
   (slurs, hairpins, pedals, part groups) lose their numbers.
4. A key, time or transposition with no `number` stands for each staff;
   `<tie>` and `<tied>` are one item; a `<dynamics>` inside `<notations>` is
   the same item as one in a `<direction>` at the note; the notes of a chord
   take the first note's duration, as the reader does.
5. A rest keeps only its length (its `<type>` is conventional: a whole rest
   in a 3/4 bar), and adjacent rests of a voice are one silence;
   `<harmony>` keeps root, kind, bass and degrees; `<lyric>` number,
   syllabic, text, extend and elision; text is trimmed, and words are
   compared in lower case.
6. What the reader reads as one thing is one item: a mark of a whole chord
   repeated on each of its notes, a tone written twice in one chord, a
   hidden staff (for the whole part, wherever the file hid it). What it
   reads across a bar line goes where it puts it: a direction or a grace
   note at a measure's end is at the next one's start, and a stop at a
   measure's start ends the measure before.
7. Drawing is dropped where it hides in musical elements: a fermata's
   "normal" shape (the default), an accent's up or down, a pedal's line or
   sign, a percussion clef's line, a `normal-type` equal to the note's type.

The item tags are the `kind`s a `Difference` can have, with four more for
what is not in a measure: "header", "part-list", "parts" and "measures".

>>> import io
>>> from openmusickit.io.musicxml.container import load
>>> one = load(io.BytesIO(b'''<score-partwise><part-list><score-part id="A"><part-name>Fl</part-name>
...   </score-part></part-list><part id="A"><measure number="1"><attributes><divisions>1</divisions>
...   </attributes><note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration>
...   <voice>1</voice><type>whole</type><stem>up</stem></note></measure></part></score-partwise>'''))
>>> two = load(io.BytesIO(b'''<score-partwise><part-list><score-part id="X"><part-name>Fl</part-name>
...   </score-part></part-list><part id="X"><measure number="0" implicit="yes"><attributes>
...   <divisions>4</divisions></attributes><note><pitch><step>C</step><octave>4</octave></pitch>
...   <duration>16</duration><voice>3</voice><type>whole</type></note></measure></part></score-partwise>'''))
>>> compare(canonicalize(one), canonicalize(two))
[]
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction

from openmusickit.io.musicxml import tables

# The canonical form keeps only what it reads out of a document, so everything
# else (§5.10's presentation, <sound>, <encoding>, numbers) is dropped by omission.
NOTE_ITEMS = frozenset({"note", "tie", "notation", "lyric", "extend"})
STOPS = ("stop", "discontinue")
DIRECTION_ITEMS = frozenset(
    {"words", "dynamics", "metronome", "rehearsal", "segno", "coda", "eyeglasses", "damp",
     "damp-all", "wedge", "dashes", "bracket", "pedal", "octave-shift", "string-mute", "harmony"}
)  # fmt: skip


@dataclass(frozen=True, slots=True)
class Difference:
    """One thing two canonical documents disagree on: its `kind` (an item
    tag, or "header", "part-list", "parts", "measures"), the measure index
    and part where it is (None outside a measure), and the item itself,
    prefixed "-" when only the first document has it and "+" when only
    the second does."""

    kind: str
    measure: int | None
    part: str | None
    detail: str


def canonicalize(root: ET.Element) -> ET.Element:
    """The canonical form of a `<score-partwise>` element (see the module docstring).

    Raises
    ------
    ValueError
        if `root` is not a `<score-partwise>`.
    """
    if root.tag != "score-partwise":
        raise ValueError(f"Not a partwise score: the root element is <{root.tag}>.")
    canonical = ET.Element("score")
    canonical.append(_header(root))
    ids: dict[str, str] = {}
    instruments: dict[str, int] = {}
    part_list = root.find("part-list")
    canonical_list = ET.SubElement(canonical, "part-list")
    if part_list is not None:
        for child in part_list:
            if child.tag == "score-part":
                ids[child.get("id")] = f"P{len(ids) + 1}"
                instruments[child.get("id")] = len(child.findall("score-instrument"))
                canonical_list.append(_score_part(child, ids[child.get("id")]))
            elif child.tag == "part-group":
                canonical_list.append(_part_group(child))
    for part in root.findall("part"):
        part_id = part.get("id")
        canonical.append(_Part(part, ids.get(part_id, "?"), instruments.get(part_id, 0)).build())
    return canonical


def compare(a: ET.Element, b: ET.Element) -> list[Difference]:
    """The differences between two canonical forms (from `canonicalize`):
    the header, the part list, and measure by measure the items only one
    of them has.

    >>> import io
    >>> from openmusickit.io.musicxml.container import load
    >>> def score(step: bytes):
    ...     return canonicalize(load(io.BytesIO(b'<score-partwise><part-list><score-part id="P1">'
    ...         b'<part-name>Fl</part-name></score-part></part-list><part id="P1"><measure number="1">'
    ...         b'<attributes><divisions>1</divisions></attributes><note><pitch><step>' + step
    ...         + b'</step><octave>4</octave></pitch><duration>4</duration><type>whole</type></note>'
    ...         b'</measure></part></score-partwise>')))
    >>> [(d.kind, d.measure, d.detail) for d in compare(score(b"C"), score(b"D"))]
    [('note', 1, '- <note at="0" staff="1" voice="1" pitch="C4" duration="1" type="whole" />'), ('note', 1, '+ <note at="0" staff="1" voice="1" pitch="D4" duration="1" type="whole" />')]
    """
    differences: list[Difference] = []
    for kind in ("header", "part-list"):
        differences += _diff(kind, None, None, list(a.find(kind)), list(b.find(kind)))
    parts_a, parts_b = a.findall("part"), b.findall("part")
    if len(parts_a) != len(parts_b):
        differences.append(
            Difference("parts", None, None, f"{len(parts_a)} parts against {len(parts_b)}")
        )
    for part_a, part_b in zip(parts_a, parts_b, strict=False):
        name = part_a.get("id")
        measures_a, measures_b = part_a.findall("measure"), part_b.findall("measure")
        if len(measures_a) != len(measures_b):
            detail = f"{len(measures_a)} measures against {len(measures_b)}"
            differences.append(Difference("measures", None, name, detail))
        for index, (measure_a, measure_b) in enumerate(
            zip(measures_a, measures_b, strict=False), 1
        ):
            differences += _diff(None, index, name, list(measure_a), list(measure_b))
    return differences


def _diff(
    kind: str | None,
    measure: int | None,
    part: str | None,
    a: list[ET.Element],
    b: list[ET.Element],
) -> list[Difference]:
    """The items of `a` and `b` that the other lacks, as a multiset difference."""
    left = Counter(_render(item) for item in a)
    right = Counter(_render(item) for item in b)
    tags = {_render(item): item.tag for item in [*a, *b]}
    found = []
    for rendered in sorted((left - right).elements()):
        found.append(Difference(kind or tags[rendered], measure, part, "- " + rendered))
    for rendered in sorted((right - left).elements()):
        found.append(Difference(kind or tags[rendered], measure, part, "+ " + rendered))
    return found


def _render(item: ET.Element) -> str:
    return ET.tostring(item, encoding="unicode").strip()


def _text(text: str | None) -> str:
    return " ".join((text or "").split())


def _fraction(value: Fraction) -> str:
    return str(value)


# --- the header and the part list ------------------------------------------------------------


def _header(root: ET.Element) -> ET.Element:
    header = ET.Element("header")
    work = root.find("work")
    title = _text(work.findtext("work-title")) if work is not None else ""
    movement = _text(root.findtext("movement-title"))
    if title or movement:
        ET.SubElement(header, "title").text = title or movement
    if title and movement:
        ET.SubElement(header, "movement-title").text = movement
    for path, tag in (("work/work-number", "work-number"), ("movement-number", "movement-number")):
        if _text(root.findtext(path)):
            ET.SubElement(header, tag).text = _text(root.findtext(path))
    identification = root.find("identification")
    if identification is not None:
        for creator in identification.findall("creator"):
            if _text(creator.text):
                ET.SubElement(header, "creator", type=creator.get("type", "")).text = _text(
                    creator.text
                )
        for rights in identification.findall("rights"):
            if _text(rights.text):
                ET.SubElement(header, "rights").text = _text(rights.text)
        if _text(identification.findtext("source")):
            ET.SubElement(header, "source").text = _text(identification.findtext("source"))
    return header


def _score_part(score_part: ET.Element, part_id: str) -> ET.Element:
    element = ET.Element("score-part", id=part_id, name=_text(score_part.findtext("part-name")))
    if score_part.find("part-abbreviation") is not None:
        element.set("abbreviation", _text(score_part.findtext("part-abbreviation")))
    instruments = [
        _text(i.findtext("instrument-name")) for i in score_part.findall("score-instrument")
    ]
    if instruments:
        element.set("instruments", " | ".join(instruments))
    return element


def _part_group(group: ET.Element) -> ET.Element:
    element = ET.Element("part-group", type=group.get("type", ""))
    for tag in ("group-name", "group-abbreviation", "group-symbol", "group-barline"):
        if group.find(tag) is not None:
            element.set(tag, _text(group.findtext(tag)))
    if element.get("type") == "start":
        element.set("group-barline", element.get("group-barline", "no"))  # the reader's default
    return element


# --- one part ---------------------------------------------------------------------------------


class _Part:
    def __init__(self, part: ET.Element, part_id: str, instruments: int):
        self.part = part
        self.id = part_id
        self.instruments = instruments  # an <instrument> on a note matters only among several
        self.divisions = 1
        self.staves = 1
        self.voices: dict[tuple[str, str], str] = {}  # (staff, voice) -> canonical voice
        self.items: list[tuple[int, Fraction, str, str, ET.Element]] = []

    def build(self) -> ET.Element:
        canonical = ET.Element("part", id=self.id)
        measures = [self.read_measure(i, m) for i, m in enumerate(self.part.findall("measure"), 1)]
        self.across_bar_lines(measures)
        bars = [items for items, _ in measures]
        hidden = [item for items in bars for item in items if item.tag == "staff-details"]
        for items in bars:  # a hidden staff is hidden for the whole part, as the reader has it
            items[:] = [item for item in items if item.tag != "staff-details"]
        for item in hidden:
            item.set("at", "0")
            if bars and not any(_render(item) == _render(other) for other in bars[0]):
                bars[0].append(item)
        for items in bars:
            _merge_rests(items)
            _once_per_chord(items)
        self.renumber_voices()
        for index, items in enumerate(bars, 1):
            element = ET.SubElement(canonical, "measure", index=str(index))
            element.extend(sorted(items, key=_sort_key))
        return canonical

    def across_bar_lines(self, measures: list[tuple[list[ET.Element], Fraction]]) -> None:
        """What sits on a bar line belongs where the reader puts it: a direction
        or a grace note at a measure's end is at the next measure's start, and
        a stop at a measure's start ends the measure before."""
        for index in range(len(measures) - 1):
            items, length = measures[index]
            if length == 0:
                continue
            graces = {
                (i.get("staff"), i.get("voice"))
                for i in items
                if i.tag == "note" and i.get("grace") and Fraction(i.get("at")) == length
            }
            for item in list(items):
                if Fraction(item.get("at", "-1")) != length:
                    continue
                direction = item.tag in DIRECTION_ITEMS and item.get("type") not in STOPS
                grace = item.tag in NOTE_ITEMS and (item.get("staff"), item.get("voice")) in graces
                if direction or grace:
                    items.remove(item)
                    item.set("at", "0")
                    measures[index + 1][0].append(item)
        for index in range(1, len(measures)):
            items, _ = measures[index]
            previous, length = measures[index - 1]
            for item in list(items):
                if (
                    item.tag in DIRECTION_ITEMS
                    and item.get("type") in STOPS
                    and item.get("at") == "0"
                ):
                    items.remove(item)
                    item.set("at", _fraction(length))
                    previous.append(item)

    def renumber_voices(self) -> None:
        """Voices per staff, numbered by first appearance (measure, position, number)."""
        firsts: dict[tuple[str, str], tuple] = {}
        for measure, at, staff, voice, _ in self.items:
            key = (staff, voice)
            here = (measure, at, _voice_key(voice))
            if key not in firsts or here < firsts[key]:
                firsts[key] = here
        per_staff: dict[str, list[tuple[tuple, str]]] = {}
        for (staff, voice), first in firsts.items():
            per_staff.setdefault(staff, []).append((first, voice))
        for staff, voices in per_staff.items():
            for number, (_, voice) in enumerate(sorted(voices), 1):
                self.voices[(staff, voice)] = str(number)
        for _, _, staff, voice, item in self.items:
            item.set("voice", self.voices[(staff, voice)])

    def item(
        self, tag: str, at: Fraction, staff: str, voice: str | None = None, **attributes
    ) -> ET.Element:
        element = ET.Element(tag)
        element.set("at", _fraction(at))
        element.set("staff", staff)
        if voice is not None:
            element.set("voice", voice)
        for key, value in attributes.items():
            if value not in (None, ""):
                element.set(key.replace("_", "-"), str(value))
        return element

    def read_measure(self, index: int, measure: ET.Element) -> tuple[list[ET.Element], Fraction]:
        """The measure's items, and its length: the furthest any voice reaches."""
        items: list[ET.Element] = []
        cursor = longest = Fraction(0)
        chord_at = Fraction(0)
        chord_duration: dict = {}
        for child in measure:
            match child.tag:
                case "attributes":
                    items += self.attributes(child, cursor)
                case "note":
                    staff = child.findtext("staff") or "1"
                    voice = (child.findtext("voice") or "1").strip()
                    grace = child.find("grace") is not None
                    if child.find("chord") is not None:
                        at = chord_at
                    else:
                        at = cursor
                        chord_at = at
                        chord_duration = self.duration_of(child)
                        if not grace:
                            cursor += self.length(child)
                    for element in self.note(child, at, staff, voice, chord_duration):
                        if "voice" in element.attrib:
                            self.items.append((index, at, staff, voice, element))
                        items.append(element)
                case "backup":
                    cursor -= self.length(child)
                case "forward":
                    cursor += self.length(child)
                case "direction":
                    items += self.direction(child, cursor + self.offset(child))
                case "harmony":
                    items.append(self.harmony(child, cursor + self.offset(child)))
                case "barline":
                    items.append(self.barline(child))
                case _:
                    pass  # print, sound, figured-bass, bookmark, link, grouping, listening
            longest = max(longest, cursor)
        return items, longest

    def length(self, element: ET.Element) -> Fraction:
        text = element.findtext("duration")
        return (
            Fraction(int(text.strip()), 4 * self.divisions)
            if text and text.strip()
            else Fraction(0)
        )

    def offset(self, element: ET.Element) -> Fraction:
        text = element.findtext("offset")
        if not text or not text.strip():
            return Fraction(0)
        return Fraction(int(Fraction(text.strip())), 4 * self.divisions)

    # attributes

    def attributes(self, attributes: ET.Element, at: Fraction) -> list[ET.Element]:
        items = []
        if attributes.findtext("divisions"):
            self.divisions = int(attributes.findtext("divisions"))
        if attributes.findtext("staves"):
            self.staves = int(attributes.findtext("staves"))
            if self.staves > 1:
                items.append(self.item("staves", at, "0", count=self.staves))
        for child in attributes:
            staves = (
                [child.get("number")]
                if child.get("number")
                else [str(s) for s in range(1, self.staves + 1)]
            )
            match child.tag:
                case "key":
                    for staff in staves:
                        items.append(self.item("key", at, staff, fifths=_text(child.findtext("fifths")),
                                               mode=_text(child.findtext("mode"))))  # fmt: skip
                case "time":
                    beats = "+".join(_text(b.text) for b in child.findall("beats"))
                    types = "+".join(_text(t.text) for t in child.findall("beat-type"))
                    senza = "yes" if child.find("senza-misura") is not None else None
                    for staff in staves:
                        items.append(self.item("time", at, staff, beats=beats, beat_type=types,
                                               symbol=child.get("symbol"), senza_misura=senza))  # fmt: skip
                case "clef":
                    staff = child.get("number") or "1"
                    sign = _text(child.findtext("sign"))
                    line = _text(child.findtext("line")) if sign in ("G", "F", "C") else None
                    items.append(self.item("clef", at, staff, sign=sign, line=line,
                                           octave_change=_text(child.findtext("clef-octave-change"))))  # fmt: skip
                case "transpose":
                    for staff in staves:
                        items.append(self.item("transpose", at, staff,
                                               diatonic=_text(child.findtext("diatonic")) or "0",
                                               chromatic=_text(child.findtext("chromatic")) or "0",
                                               octave_change=_text(child.findtext("octave-change"))))  # fmt: skip
                case "staff-details":
                    if child.get("print-object") == "no":
                        items.append(
                            self.item("staff-details", at, child.get("number") or "1", hidden="yes")
                        )
                case "measure-style":
                    for style in child:
                        items.append(self.item(style.tag, at, child.get("number") or "1",
                                               type=style.get("type"), value=_text(style.text),
                                               slashes=style.get("slashes")))  # fmt: skip
                case _:
                    pass  # divisions (rescaled), staves (above), instruments, part-symbol, directive
        return items

    # notes

    def duration_of(self, note: ET.Element) -> dict:
        """What a note says about its value: length, type, dots, tuplet."""
        modification = note.find("time-modification")
        tuplet = None
        if modification is not None:
            normal_type = _text(modification.findtext("normal-type"))
            normal_dots = "." * len(modification.findall("normal-dot"))
            if normal_type == _text(note.findtext("type")) and not normal_dots:
                normal_type = ""  # the note's own type, said again
            tuplet = ":".join(
                filter(None, [_text(modification.findtext("actual-notes")),
                              _text(modification.findtext("normal-notes")),
                              normal_type, normal_dots])
            )  # fmt: skip
        return {
            "duration": _fraction(self.length(note)) if note.find("grace") is None else None,
            "type": _text(note.findtext("type")) or None,
            "dots": str(len(note.findall("dot"))) if note.findall("dot") else None,
            "tuplet": tuplet,
        }

    def note(
        self, note: ET.Element, at: Fraction, staff: str, voice: str, chord: dict
    ) -> list[ET.Element]:
        rest = note.find("rest")
        hidden = note.get("print-object") == "no"
        if rest is not None and hidden:
            return []  # a hidden rest is a gap, as a <forward> is
        attributes: dict = {}
        pitch, unpitched = note.find("pitch"), note.find("unpitched")
        if pitch is not None:
            alter = _text(pitch.findtext("alter"))
            alter = "" if alter in ("", "0") else alter
            attributes["pitch"] = (
                f"{_text(pitch.findtext('step'))}{alter}{_text(pitch.findtext('octave'))}"
            )
        elif unpitched is not None:
            attributes["unpitched"] = (
                f"{_text(unpitched.findtext('display-step'))}{_text(unpitched.findtext('display-octave'))}"
            )
        grace = note.find("grace")
        if rest is not None:
            attributes["duration"] = chord["duration"]
        else:
            attributes.update(chord)
        if grace is not None:
            attributes["grace"] = "slash" if grace.get("slash") == "yes" else "yes"
        if note.find("cue") is not None:
            attributes["cue"] = "yes"
        if hidden:
            attributes["hidden"] = "yes"
        notehead = _text(note.findtext("notehead"))
        if notehead == "slash":
            attributes["notehead"] = "slash"
        instrument = note.find("instrument")
        if instrument is not None and self.instruments > 1:
            attributes["instrument"] = instrument.get("id")
        items = [self.item("rest" if rest is not None else "note", at, staff, voice, **attributes)]
        tone = attributes.get("pitch") or attributes.get("unpitched") or ""
        ties = {tie.get("type") for tie in note.findall("tie")}
        for notations in note.findall("notations"):
            ties |= {
                tied.get("type")
                for tied in notations.findall("tied")
                if tied.get("type") != "let-ring"
            }
        for kind in sorted(t for t in ties if t):
            items.append(self.item("tie", at, staff, voice, pitch=tone, type=kind))
        for notations in note.findall("notations"):
            items += self.notations(notations, at, staff, voice, tone)
        for lyric in note.findall("lyric"):
            items += self.lyric(lyric, at, staff, voice)
        return items

    def notations(
        self, notations: ET.Element, at: Fraction, staff: str, voice: str, tone: str
    ) -> list[ET.Element]:
        items = []
        for child in notations:
            if child.tag == "tied" and child.get("type") != "let-ring":
                continue  # with <tie>, above
            if child.tag == "dynamics":
                items += [self.dynamics_item(item, at, staff) for item in child]
                continue
            if child.tag in ("articulations", "ornaments", "technical"):
                for item in child:
                    per_tone = tone if child.tag == "technical" else None
                    items.append(self.notation(item, at, staff, voice, per_tone))
                continue
            items.append(self.notation(child, at, staff, voice, None))
        return items

    def notation(
        self, element: ET.Element, at: Fraction, staff: str, voice: str, tone: str | None
    ) -> ET.Element:
        attributes = {
            "name": element.tag,
            "type": element.get("type"),
            "direction": element.get("direction"),
        }
        text = _text(element.text)
        if element.tag == "fermata" and text == "normal":
            text = ""  # the default shape
        if element.tag in tables.ARTICULATIONS:
            attributes["type"] = None  # an accent's up or down is how it is drawn
        if element.tag in ("harmon-mute", "hole"):
            text = _text(element.findtext("harmon-closed") or element.findtext("hole-closed"))
        if element.tag != "tuplet":
            attributes["text"] = text
        if tone is not None:
            attributes["pitch"] = tone
        return self.item("notation", at, staff, voice, **attributes)

    def dynamics_item(
        self, item: ET.Element, at: Fraction, staff: str, hidden: bool = False
    ) -> ET.Element:
        value = _text(item.text) if item.tag == "other-dynamics" else item.tag
        return self.item("dynamics", at, staff, value=value, hidden="yes" if hidden else None)

    def lyric(self, lyric: ET.Element, at: Fraction, staff: str, voice: str) -> list[ET.Element]:
        number = lyric.get("number") or "1"
        items = []
        syllabic = None
        index = 0
        for child in lyric:
            if child.tag == "syllabic":
                syllabic = _text(child.text)
            elif child.tag == "text":
                if _text(child.text):
                    items.append(self.item("lyric", at, staff, voice, number=number, index=index,
                                           syllabic=syllabic, text=_text(child.text)))  # fmt: skip
                    index += 1
                syllabic = None
            elif child.tag == "extend":
                items.append(
                    self.item("extend", at, staff, voice, number=number, type=child.get("type"))
                )
        return items

    # directions, harmony, bar lines

    def direction(self, direction: ET.Element, at: Fraction) -> list[ET.Element]:
        staff = _text(direction.findtext("staff")) or "1"
        hidden = "yes" if direction.get("print-object") == "no" else None
        items = []
        for direction_type in direction.findall("direction-type"):
            for child in direction_type:
                match child.tag:
                    case "words":
                        if _text(child.text):
                            items.append(
                                self.item(
                                    "words",
                                    at,
                                    staff,
                                    text=tables.normalize_words(child.text),
                                    hidden=hidden,
                                )
                            )
                    case "dynamics":
                        items += [
                            self.dynamics_item(item, at, staff, bool(hidden)) for item in child
                        ]
                    case "metronome":
                        units = [_text(u.text) for u in child.findall("beat-unit")]
                        dots = len(child.findall("beat-unit-dot"))
                        items.append(self.item("metronome", at, staff, beat_unit="+".join(units),
                                               dots=dots or None, per_minute=_text(child.findtext("per-minute")),
                                               hidden=hidden))  # fmt: skip
                    case "rehearsal" | "segno" | "coda" | "eyeglasses" | "damp" | "damp-all":
                        items.append(
                            self.item(child.tag, at, staff, text=_text(child.text), hidden=hidden)
                        )
                    case "other-direction":
                        pass
                    case _:
                        attributes = {
                            k: v
                            for k, v in child.attrib.items()
                            if k in ("type", "size", "niente")  # a pedal's line or sign is drawing
                        }
                        items.append(self.item(child.tag, at, staff, hidden=hidden, **attributes))
        return items

    def harmony(self, harmony: ET.Element, at: Fraction) -> ET.Element:
        def tone(prefix: str) -> str:
            element = harmony.find(prefix)
            if element is None:
                return ""
            alter = _text(element.findtext(f"{prefix}-alter"))
            alter = "" if alter in ("", "0") else alter
            return _text(element.findtext(f"{prefix}-step")) + alter

        degrees = [
            f"{_text(d.findtext('degree-type'))}{_text(d.findtext('degree-alter')) or '0'}:"
            f"{_text(d.findtext('degree-value'))}"
            for d in harmony.findall("degree")
        ]
        return self.item("harmony", at, _text(harmony.findtext("staff")) or "1", root=tone("root"),
                         kind=_text(harmony.findtext("kind")), bass=tone("bass"),
                         degrees=" ".join(degrees))  # fmt: skip

    def barline(self, barline: ET.Element) -> ET.Element:
        element = ET.Element("barline", location=barline.get("location", "right"))
        if barline.findtext("bar-style"):
            element.set("style", _text(barline.findtext("bar-style")))
        repeat = barline.find("repeat")
        if repeat is not None:
            element.set("repeat", repeat.get("direction", ""))
        ending = barline.find("ending")
        if ending is not None:
            element.set("ending", f"{ending.get('number', '')}:{ending.get('type', '')}")
        for tag in ("segno", "coda"):
            if barline.find(tag) is not None:
                element.set(tag, "yes")
        fermatas = [_text(f.text) or "normal" for f in barline.findall("fermata")]
        if fermatas:
            element.set("fermata", " ".join(fermatas))
        return element


def _merge_rests(items: list[ET.Element]) -> None:
    """Adjacent rests of one voice are one silence: their spelling is notation."""
    rests = sorted(
        (item for item in items if item.tag == "rest"),
        key=lambda r: (r.get("staff"), r.get("voice"), Fraction(r.get("at"))),
    )
    previous = None
    for rest in rests:
        if (
            previous is not None
            and (previous.get("staff"), previous.get("voice"))
            == (rest.get("staff"), rest.get("voice"))
            and Fraction(previous.get("at")) + Fraction(previous.get("duration"))
            == Fraction(rest.get("at"))
            and {k: v for k, v in previous.attrib.items() if k not in ("at", "duration")}
            == {k: v for k, v in rest.attrib.items() if k not in ("at", "duration")}
        ):
            previous.set(
                "duration",
                _fraction(Fraction(previous.get("duration")) + Fraction(rest.get("duration"))),
            )
            items.remove(rest)
            continue
        previous = rest


def _once_per_chord(items: list[ET.Element]) -> None:
    """A mark of the whole chord counts once, on whichever note of it the
    file put it (some programs repeat an arpeggio on every note), and so
    does a tone written twice in one chord (a unison: the reader's tones
    are a set)."""
    seen: set[str] = set()
    for item in list(items):
        chord_mark = item.tag == "notation" and "pitch" not in item.attrib
        if not (chord_mark or item.tag in ("note", "tie")):
            continue
        rendered = _render(item)
        if rendered in seen:
            items.remove(item)
        seen.add(rendered)


def _voice_key(voice: str) -> tuple[int, str]:
    return (int(voice), "") if voice.isdigit() else (10**6, voice)


def _sort_key(item: ET.Element) -> tuple:
    return (
        Fraction(item.get("at", "-1")),
        item.get("staff", ""),
        item.get("voice", ""),
        item.tag,
        _render(item),
    )
