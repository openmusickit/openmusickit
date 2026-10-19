"""Hypothesis strategies for the OMK property tests.

Each function returns a `SearchStrategy`. Finite domains (pitch classes,
the symbol tables) are sampled from the lists in `tests.domains`; the
infinite ones (lengths, note events, lines, spellings, lyric texts) are
built from Hypothesis primitives. The spelling strategies yield `(text,
expected)` pairs, since the point of a spelling is what it must parse to.
"""

from __future__ import annotations

from fractions import Fraction

from hypothesis import strategies as st

from openmusickit.graph.graph import GraphMeta, OmkGraph
from openmusickit.io.musicxml import tables
from openmusickit.objects.chord_event import ChordEvent
from openmusickit.objects.context_event import ClefEvent, MeterEvent, ModalContextEvent, TempoEvent
from openmusickit.objects.division_event import DivisionEvent
from openmusickit.objects.lyrics import LyricSection, LyricSyllable
from openmusickit.objects.marking import Marking, MarkSpanner
from openmusickit.objects.note_event import NoteEvent, Rest
from openmusickit.objects.part import LineGroup, Part, StackGroup, Stint
from openmusickit.objects.score import Score
from openmusickit.objects.sync_line import SyncLine
from openmusickit.systems.wsmn.percussion.percussion_tone import PercussionTone
from openmusickit.systems.wsmn.scoring import symbols as scoring
from openmusickit.systems.wsmn.scoring.bracket_shape import BracketShape, BracketSymbol
from openmusickit.systems.wsmn.scoring.staff_clef import ClefSign, StaffClef
from openmusickit.systems.wsmn.temporal import symbols as temporal_symbols
from openmusickit.systems.wsmn.temporal.metrical_duration import MetricalDuration
from openmusickit.systems.wsmn.temporal.wsmn import WSMN_TEMPORAL
from openmusickit.systems.wsmn.tonal.constants import ACCIDENTALS, DIATONES, QualityType
from openmusickit.systems.wsmn.tonal.key import Key, KeySignature
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from openmusickit.utils.number_names import ORDINALS
from openmusickit.values.text.word import Word
from openmusickit.values.time.clock_time import Tempo
from openmusickit.values.time.duration import GraceDuration, ZeroDuration
from tests.domains import (
    ABSTRACT_VECTORS,
    ALL_VECTORS,
    PERCUSSION_TONES,
    QUALIFIED_VECTORS,
    distinct,
    symbols_of,
)

DURATION_SYMBOLS = list(distinct(symbols_of(temporal_symbols, MetricalDuration)).values())

# --- tones ----------------------------------------------------------------------


def tonal_vectors(qualified: bool | None = None) -> st.SearchStrategy[TonalVector]:
    """A pitch class (False), an octave-qualified pitch (True), or either (None), from the domain lists."""
    if qualified is None:
        return st.sampled_from(ALL_VECTORS)
    return st.sampled_from(QUALIFIED_VECTORS if qualified else ABSTRACT_VECTORS)


def percussion_tones() -> st.SearchStrategy[PercussionTone]:
    """Any PercussionTone, from the domain list."""
    return st.sampled_from(PERCUSSION_TONES)


# --- durations ----------------------------------------------------------------------


def metrical_durations() -> st.SearchStrategy[MetricalDuration]:
    """A note value: one of the symbols, or a plain value from a whole to a 128th with up to three dots."""
    constructed = st.builds(
        lambda k, dots: MetricalDuration(1, 2**k, dots), st.integers(0, 7), st.integers(0, 3)
    )
    return st.one_of(st.sampled_from(DURATION_SYMBOLS), constructed)


def positive_fractions(max_denominator: int = 64) -> st.SearchStrategy[Fraction]:
    """A positive rational length, up to two maximas long, with a bounded denominator."""
    return st.fractions(min_value=0, max_value=16, max_denominator=max_denominator).filter(
        lambda x: x > 0
    )


# --- events and lines ----------------------------------------------------------------


def note_events(unpitched: bool = False) -> st.SearchStrategy[NoteEvent]:
    """A NoteEvent with zero to three tones and a note value, or, one time in ten, no duration.

    The tones are pitched; with `unpitched=True` percussion tones are mixed
    in, for tests that never transpose."""
    durations = st.integers(0, 9).flatmap(lambda i: st.none() if i == 0 else metrical_durations())
    tone = st.one_of(tonal_vectors(), percussion_tones()) if unpitched else tonal_vectors()
    tones = st.frozensets(tone, max_size=3).map(set)
    return st.builds(NoteEvent, tones=tones, duration=durations)


def lines(
    min_size: int = 1, max_size: int = 6, unpitched: bool = False
) -> st.SearchStrategy[list[NoteEvent]]:
    """A list of fresh note events, ready for `OmkGraph.add_line`."""
    return st.lists(note_events(unpitched), min_size=min_size, max_size=max_size)


# --- spellings ------------------------------------------------------------------------


def _mixed_case(text: str) -> st.SearchStrategy[str]:
    """`text` with each letter's case chosen at random."""
    return st.tuples(*(st.sampled_from([ch.lower(), ch.upper()]) for ch in text)).map("".join)


def _with_whitespace(text: str) -> st.SearchStrategy[str]:
    """`text` with runs of whitespace inserted at random before, between and
    after its characters (the parser strips all of it)."""
    gap = st.sampled_from(["", "", "", " ", "  ", "\t"])
    gaps = st.lists(gap, min_size=len(text) + 1, max_size=len(text) + 1)
    return gaps.map(lambda g: "".join(a + ch for a, ch in zip(g, text, strict=False)) + g[-1])


def _accidental_spellings(offset: int) -> list[str]:
    """ASCII, Unicode, and spelled-out (with and without the space) forms of one accidental."""
    accidental = ACCIDENTALS[offset]
    return [
        accidental.ascii,
        accidental.unicode,
        accidental.name,
        accidental.name.replace(" ", ""),
    ]


def pitch_spellings() -> st.SearchStrategy[tuple[str, TonalVector]]:
    """A letter-name spelling `from_string` must accept (any accidental in any
    of its spellings, joined directly, by a space or by a hyphen, with or
    without an octave number), in random case and whitespace, with the
    TonalVector it must parse to."""

    @st.composite
    def build(draw) -> tuple[str, TonalVector]:
        diatone = draw(st.sampled_from(DIATONES))
        offset = draw(st.sampled_from(sorted(ACCIDENTALS)))
        spelling = draw(st.sampled_from(_accidental_spellings(offset)))
        separator = draw(st.sampled_from(["", " ", "-"])) if spelling else ""
        octave = draw(st.one_of(st.none(), st.integers(-2, 9)))
        text = f"{diatone.letter}{separator}{spelling}" + ("" if octave is None else str(octave))
        c = (diatone.chromatic + offset) % 12
        expected = (
            TonalVector((diatone.degree, c))
            if octave is None
            else TonalVector((diatone.degree, c, octave - 4))
        )
        text = draw(_mixed_case(text))
        text = draw(_with_whitespace(text))
        return text, expected

    return build()


_QUALITY_WORDS = {
    "perfect": ["P", "per", "perfect"],
    "major": ["M", "maj", "major"],
    "minor": ["m", "min", "minor"],
    "augmented": ["aug", "augmented"],
    "diminished": ["dim", "diminished"],
}
_MULTIPLIER_WORDS = {
    1: [""],
    2: ["dbl", "double"],
    3: ["trp", "trpl", "triple"],
    4: ["qua", "quad", "quadruple"],
}
_NUMBER_WORDS = {diatone.degree + 1: diatone.interval_name for diatone in DIATONES}


def interval_spellings() -> st.SearchStrategy[tuple[str, TonalVector]]:
    """An interval spelling `from_string` must accept (a quality its degree
    can take, a multiplier for augmented and diminished, the number as
    digits, an ordinal or a word, an optional octave suffix), in random case
    and whitespace, with the TonalVector it must parse to. Bare `M` and `m`
    keep their case, since that is what tells them apart."""

    @st.composite
    def build(draw) -> tuple[str, TonalVector]:
        number = draw(st.integers(1, 13))
        d, octave = (number - 1) % 7, (number - 1) // 7
        diatone = DIATONES[d]
        perfect_type = diatone.quality_type is QualityType.P
        kinds = ["augmented", "diminished"] + (["perfect"] if perfect_type else ["major", "minor"])
        kind = draw(st.sampled_from(kinds))
        times = draw(st.integers(1, 4)) if kind in ("augmented", "diminished") else 1
        if kind == "augmented":
            modifier = times
        elif kind == "diminished":
            modifier = -times if perfect_type else -(times + 1)
        else:
            modifier = -1 if kind == "minor" else 0
        word = draw(st.sampled_from(_QUALITY_WORDS[kind]))
        multiplier = draw(st.sampled_from(_MULTIPLIER_WORDS[times]))
        forms = [str(number), ORDINALS[number]]
        if number in _NUMBER_WORDS:
            forms.append(_NUMBER_WORDS[number])
        number_form = draw(st.sampled_from(forms))
        shift = draw(st.one_of(st.none(), st.integers(-2, 2)))
        suffix = "" if shift is None else f"{shift:+d}"
        c = (diatone.chromatic + modifier) % 12
        if number > 7 or shift is not None:
            expected = TonalVector((d, c, octave + (shift or 0)))
        else:
            expected = TonalVector((d, c))
        if word not in ("M", "m"):
            word = draw(_mixed_case(word))
        multiplier = draw(_mixed_case(multiplier))
        number_form = draw(_mixed_case(number_form))
        text = draw(_with_whitespace(f"{multiplier}{word}{number_form}{suffix}"))
        return text, expected

    return build()


# --- lyrics -------------------------------------------------------------------------------


def lyric_texts() -> st.SearchStrategy[str]:
    """Typed lyrics `parse_lyrics` must accept: words of one to four
    syllables joined by hyphens, at most one syllable per word carrying the
    primary mark and any others a secondary mark, some words ending in
    trailing punctuation, separated by spaces or newlines."""

    @st.composite
    def word(draw) -> str:
        syllables = draw(
            st.lists(
                st.text(alphabet="abcdefghijklmnopqrstuvwxyzé", min_size=1, max_size=5),
                min_size=1,
                max_size=4,
            )
        )
        primary = draw(st.one_of(st.none(), st.integers(0, len(syllables) - 1)))
        marked = []
        for i, syllable in enumerate(syllables):
            if i == primary:
                marked.append("'" + syllable)
            else:
                marked.append(draw(st.sampled_from(["", "", "", ","])) + syllable)
        return "-".join(marked) + draw(st.sampled_from(["", "", ",", ".", "!"]))

    separator = st.sampled_from([" ", " ", "  ", "\n"])
    return st.lists(st.tuples(word(), separator), max_size=6).map(
        lambda pairs: "".join(w + sep for w, sep in pairs).strip()
    )


# --- scores the MusicXML reader could have built --------------------------------------------

_BAR_VALUES = (
    temporal_symbols.whole,
    temporal_symbols.dotted_half,
    temporal_symbols.half,
    temporal_symbols.dotted_quarter,
    temporal_symbols.quarter,
    temporal_symbols.eighth,
    temporal_symbols.sixteenth,
    "triplets",  # three eighths of an eighth-note triplet, a quarter's time
)
_METERS = (
    temporal_symbols.two_four,
    temporal_symbols.three_four,
    temporal_symbols.four_four,
    temporal_symbols.six_eight,
    temporal_symbols.two_two,
)
_PLAIN_TONES = [
    t for t in QUALIFIED_VECTORS if -1 <= (t.c - (0, 2, 4, 5, 7, 9, 11)[t.d] + 6) % 12 - 6 <= 1
]
_ROOTS = [
    t for t in ABSTRACT_VECTORS if -1 <= (t.c - (0, 2, 4, 5, 7, 9, 11)[t.d] + 6) % 12 - 6 <= 1
]
# Transpositions (written minus sounding) of real instruments: clarinets in B♭
# and A, horn in F, alto and baritone saxophones, guitar, piccolo.
_TRANSPOSITIONS = [(1, 2, 0), (2, 3, 0), (4, 7, 0), (5, 9, 0), (5, 9, 1), (0, 0, 1), (0, 0, -1)]


@st.composite
def exportable_scores(draw) -> OmkGraph:
    """A graph holding one Score in the form the MusicXML reader builds,
    so that writing and reading it back gives an equivalent graph.

    One to three Parts, each a single line or a two-staff group, all cut
    into the same bars (a pickup sometimes) and filled exactly: notes of one
    to three tones, rests, triplets and grace notes; a division at every bar
    line, the last a final bar; key, meter and clef at the head of every
    line, sometimes a tempo; a second voice under one note, marks from the
    writer's tables, a slur, ties between repeated notes, a verse of whole
    words, a chord line pinned to the first part, and sometimes a
    transposing Stint. Two or more Parts get the reader's bar grid and,
    sometimes, a bracket over them all.
    """
    meter = draw(st.sampled_from(_METERS))
    bar = meter.rational_length
    bars = [bar] * draw(st.integers(1, 3))
    if draw(st.booleans()):
        bars.insert(0, Fraction(1, 4))  # a pickup
    key = Key.from_signature(KeySignature.from_alts(draw(st.integers(-7, 7))))
    tempo = draw(
        st.sampled_from([None, TempoEvent(tempo=Tempo(96, temporal_symbols.quarter)),
                         TempoEvent(term=scoring.allegro)])
    )  # fmt: skip
    note_marks = [scoring.staccato, scoring.accent, scoring.tenuto, scoring.marcato,
                  scoring.fermata, scoring.trill, scoring.mordent, scoring.up_bow,
                  scoring.piano, scoring.forte, scoring.sforzando]  # fmt: skip

    def tone_set() -> set:
        return set(
            draw(st.lists(st.sampled_from(_PLAIN_TONES), min_size=1, max_size=3, unique=True))
        )

    def fill(length: Fraction) -> list:
        """Events filling `length` exactly: notes, rests, triplets, graces."""
        events: list = []
        remaining = length
        while remaining > 0:
            value = draw(st.sampled_from([v for v in _BAR_VALUES if v == "triplets" and remaining >= Fraction(1, 4)
                                          or v != "triplets" and v.rational_length <= remaining]))  # fmt: skip
            if draw(st.integers(0, 9)) == 0:
                events.append(NoteEvent(tones={draw(st.sampled_from(_PLAIN_TONES))},
                                        duration=GraceDuration(temporal_symbols.eighth)))  # fmt: skip
            if value == "triplets":
                events.extend(NoteEvent(tones=tone_set(), duration=temporal_symbols.eighth_in_triplet)
                              for _ in range(3))  # fmt: skip
                remaining -= Fraction(1, 4)
                continue
            rest = draw(st.integers(0, 6)) == 0
            events.append(Rest(value) if rest else NoteEvent(tones=tone_set(), duration=value))
            remaining -= value.rational_length
        return events

    def line(clef: StaffClef) -> list:
        events: list = [
            ModalContextEvent(modal_context=key),
            MeterEvent(meter=meter),
            ClefEvent(clef=clef),
        ]
        if tempo is not None:
            events.append(TempoEvent(tempo=tempo.tempo, term=tempo.term))
        for index, length in enumerate(bars):
            events.extend(fill(length))
            last = index == len(bars) - 1
            events.append(DivisionEvent(shape=scoring.final_bar if last else None))
        return events

    graph = OmkGraph(GraphMeta())
    score = Score(
        title=draw(st.sampled_from([None, "Sketch"])),
        composer=draw(st.sampled_from([None, "Anon."])),
    )
    graph.add_node(score)
    parts: list[Part] = []
    first_lines: list[list] = []
    treble, bass = StaffClef(ClefSign.G, 2), StaffClef(ClefSign.F, 4)
    for number in range(draw(st.integers(1, 3))):
        part = Part(name=f"Part {number + 1}")
        parts.append(part)
        staves = [line(treble), line(bass)] if draw(st.booleans()) else [line(treble)]
        for events in staves:
            graph.add_line(events)
            graph.add_line_to_score(score, events[0])
        graph.add_part_to_score(score, part)
        if len(staves) == 2:
            group = LineGroup(name=part.name)
            graph.add_group(group, [events[0] for events in staves])
            graph.add_stack(events[0] for events in staves)
            graph.add_performs(part, group)
        else:
            transposition = draw(st.sampled_from([None, *_TRANSPOSITIONS]))
            stint = Stint(transposition=TonalVector(transposition) if transposition else None)
            graph.add_stint(part, stint, staves[0][0])
        first_lines.append(staves[0])
        for events in staves:
            _add_attachments(draw, graph, events, note_marks)
    graph.add_stack(parts)
    if len(parts) >= 2 and draw(st.booleans()):
        graph.add_stack_group(
            StackGroup(shape=BracketShape(symbol=BracketSymbol.BRACKET)), parts[0], parts[-1]
        )
    sounding = [e for e in first_lines[0] if isinstance(e, NoteEvent) and e.tones and not e.is_rest
                and not isinstance(e.duration, GraceDuration)]  # fmt: skip
    syllables: list[LyricSyllable] = []
    for text in draw(st.lists(st.lists(st.text("abcdefgh", min_size=1, max_size=4), min_size=1, max_size=3),
                              max_size=3)):  # fmt: skip
        if len(syllables) + len(text) > len(sounding):
            break  # whole words only: the reader closes a word the lyrics leave open
        word = Word(text)
        syllables.extend(LyricSyllable(word=word, index=i) for i in range(len(word)))
    if syllables:
        graph.add_lyrics(syllables, section=LyricSection(section_type="verse", section_number=1))
        for syllable, event in zip(syllables, sounding, strict=False):
            graph.connect_lyric_to_object(syllable, event)
    anchors = (
        sorted(set(draw(st.lists(st.integers(0, max(0, len(sounding) - 1)), max_size=3))))
        if sounding
        else []
    )
    if anchors:
        kinds = list(tables.KINDS.values())
        chords = [
            ChordEvent(chord=draw(st.sampled_from(_ROOTS))(draw(st.sampled_from(kinds))))
            for _ in anchors
        ]
        graph.add_line(chords)
        graph.add_line_to_score(score, chords[0])
        for index, chord in zip(anchors, chords, strict=True):
            graph.add_simultaneous(sounding[index], chord)
    if len(parts) >= 2:
        grid = SyncLine(temporal_system=WSMN_TEMPORAL, name=score.title or "bars")
        graph.add_sync_line_to_score(score, grid)
        for events in first_lines:
            graph.sync_event(events[0], grid, ZeroDuration())
            position = Fraction(0)
            for event in events:
                if isinstance(event, DivisionEvent):
                    graph.sync_event(event, grid, MetricalDuration.from_length(position))
                if isinstance(event.duration, MetricalDuration):
                    position += event.duration.rational_length
    return graph


def _add_attachments(draw, graph, events: list, note_marks: list) -> None:
    """Marks, a slur, ties and a second voice on one line of `exportable_scores`."""
    notes = [(i, e) for i, e in enumerate(events) if isinstance(e, NoteEvent)
             and not isinstance(e.duration, GraceDuration)]  # fmt: skip
    pitched = [(i, e) for i, e in notes if not e.is_rest]
    for _, event in (
        draw(st.lists(st.sampled_from(notes), max_size=3, unique_by=lambda n: n[0]))
        if notes
        else []
    ):
        choices = [scoring.fermata] if event.is_rest else note_marks
        for mark in draw(st.lists(st.sampled_from(choices), min_size=1, max_size=2, unique=True)):
            graph.add_articulation(Marking(mark=mark), event)
    if len(pitched) >= 2 and draw(st.booleans()):
        first, last = sorted(draw(st.lists(st.sampled_from(pitched), min_size=2, max_size=2,
                                           unique_by=lambda n: n[0])), key=lambda n: n[0])  # fmt: skip
        graph.add_spanner(MarkSpanner(mark=scoring.slur), first[1], last[1])
    # ties: a single-tone note followed directly (across a bar line, perhaps) by a note of its pitch
    for (i, event), (j, following) in zip(pitched, pitched[1:], strict=False):
        between = events[i + 1 : j]
        if (
            all(isinstance(e, DivisionEvent) for e in between)
            and len(event.tones) == 1
            and draw(st.integers(0, 3)) == 0
        ):
            following.tones = set(event.tones)
            graph.add_spanner(MarkSpanner(mark=scoring.tie), event, following)
    # a second voice under one note, within its bar
    if notes and draw(st.booleans()):
        index, parent = draw(st.sampled_from(notes))
        position, room = Fraction(0), Fraction(0)
        for k, e in enumerate(events):
            if k == index:
                start = position
            if isinstance(e.duration, MetricalDuration):
                position += e.duration.rational_length
            if isinstance(e, DivisionEvent) and k > index:
                room = position - start
                break
        values = [
            v
            for v in (temporal_symbols.quarter, temporal_symbols.eighth)
            if v.rational_length <= room
        ]
        if values:
            value = draw(st.sampled_from(values))
            count = draw(st.integers(1, int(room / value.rational_length)))
            voice = [Rest(value) if draw(st.integers(0, 4)) == 0
                     else NoteEvent(tones={draw(st.sampled_from(_PLAIN_TONES))}, duration=value)
                     for _ in range(min(count, 2))]  # fmt: skip
            graph.add_line(voice)
            graph.add_branch(parent, voice[0])


# --- MusicXML documents ---------------------------------------------------------------------

_DIVISIONS = 12  # per quarter: room for sixteenths (3) and eighth-note triplets (4)
_DOCUMENT_VALUES = [
    ("half", 24, 0),
    ("quarter", 12, 0),
    ("quarter", 18, 1),
    ("eighth", 6, 0),
    ("16th", 3, 0),
]


def _pitch_xml(step: str, alter: int, octave: int) -> str:
    alter_xml = f"<alter>{alter}</alter>" if alter else ""
    return f"<pitch><step>{step}</step>{alter_xml}<octave>{octave}</octave></pitch>"


@st.composite
def musicxml_documents(draw) -> bytes:
    """A small `<score-partwise>` in the subset the reader reads without loss
    and the writer writes back as it was: one or two parts of one to three
    measures in 3/4 or 4/4, a first voice filling every measure with notes,
    chords, rests and eighth-note triplets (bracketed, as exporters write
    them), ties between repeated notes, dynamics before notes, and sometimes
    a second voice in a measure."""
    beats = draw(st.sampled_from([3, 4]))
    bar = beats * _DIVISIONS
    pitches = st.tuples(
        st.sampled_from("CDEFGAB"), st.sampled_from([-1, 0, 0, 1]), st.integers(3, 5)
    )

    def note_xml(pitch, duration, type_name, dots, voice, chord=False, extra="", tie=None, tm=""):
        parts = [
            "<note>",
            "<chord/>" if chord else "",
            _pitch_xml(*pitch),
            f"<duration>{duration}</duration>",
        ]
        if tie:
            parts.append("".join(f'<tie type="{t}"/>' for t in tie))
        parts += [f"<voice>{voice}</voice><type>{type_name}</type>", "<dot/>" * dots, tm]
        notations = "".join(f'<tied type="{t}"/>' for t in tie or ()) + extra
        if notations:
            parts.append(f"<notations>{notations}</notations>")
        parts.append("</note>")
        return "".join(parts)

    def voice_xml(length: int, voice: int, ties: bool) -> str:
        out: list[str] = []
        remaining = length
        last = None  # (index in `out`, pitch) of the last single note, which a tie may start from
        while remaining > 0:
            choice = draw(st.integers(0, 9))
            if choice == 0 and remaining >= _DIVISIONS:  # a bracketed eighth-note triplet
                tm = (
                    "<time-modification><actual-notes>3</actual-notes>"
                    "<normal-notes>2</normal-notes></time-modification>"
                )
                for bracket in ['<tuplet type="start"/>', "", '<tuplet type="stop"/>']:
                    out.append(note_xml(draw(pitches), 4, "eighth", 0, voice, extra=bracket, tm=tm))
                remaining -= _DIVISIONS
                last = None
                continue
            type_name, duration, dots = draw(
                st.sampled_from([v for v in _DOCUMENT_VALUES if v[1] <= remaining])
            )
            remaining -= duration
            if choice == 1:
                out.append(
                    f"<note><rest/><duration>{duration}</duration><voice>{voice}</voice>"
                    f"<type>{type_name}</type>{'<dot/>' * dots}</note>"
                )
                last = None
                continue
            tied = ties and last is not None and draw(st.booleans())
            if tied:
                index, pitch = last
                out[index] = (
                    out[index]
                    .replace("<voice>", '<tie type="start"/><voice>', 1)
                    .replace("</note>", '<notations><tied type="start"/></notations></note>', 1)
                )
            else:
                pitch = draw(pitches)
            if voice == 1 and draw(st.integers(0, 4)) == 0:
                dynamic = draw(st.sampled_from(["p", "f", "mf", "sfz"]))
                out.append(
                    f"<direction><direction-type><dynamics><{dynamic}/></dynamics></direction-type></direction>"
                )
            out.append(
                note_xml(pitch, duration, type_name, dots, voice, tie=("stop",) if tied else None)
            )
            chord = (
                []
                if tied
                else [p for p in draw(st.lists(pitches, max_size=2, unique=True)) if p != pitch]
            )
            for other in chord:
                out.append(note_xml(other, duration, type_name, dots, voice, chord=True))
            last = None if chord or tied else (len(out) - 1, pitch)
        return "".join(out)

    parts = draw(st.integers(1, 2))
    measures = draw(st.integers(1, 3))
    part_list = "".join(
        f'<score-part id="P{i}"><part-name>Part {i}</part-name></score-part>'
        for i in range(1, parts + 1)
    )
    bodies = []
    for i in range(1, parts + 1):
        body = []
        for m in range(1, measures + 1):
            attributes = (
                f"<attributes><divisions>{_DIVISIONS}</divisions><key><fifths>0</fifths></key>"
                f"<time><beats>{beats}</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>"
                if m == 1
                else ""
            )
            content = voice_xml(bar, 1, ties=True)
            if draw(st.integers(0, 3)) == 0:
                content += f"<backup><duration>{bar}</duration></backup>" + voice_xml(
                    bar, 2, ties=False
                )
            body.append(f'<measure number="{m}">{attributes}{content}</measure>')
        bodies.append(f'<part id="P{i}">{"".join(body)}</part>')
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?><score-partwise version="4.0">'
        f"<part-list>{part_list}</part-list>{''.join(bodies)}</score-partwise>"
    )
    return xml.encode("utf-8")
