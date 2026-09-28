"""Default labels for the nodes of a visualization,
and the HTML-like building blocks that `layout` places:
the sync bar's blocks, the title block, the spanner markers.

Everything here produces text.
A label that starts with `<` and ends with `>` is an HTML-like Graphviz label
(`dot.is_html_label`);
`default_label` writes one when it needs a superscript or a second font size,
and plain text otherwise.
Text that goes into an HTML-like label passes through `escape`.

No musical system is imported.
A duration is asked for `numerator`, `denominator`, `dots` and `ratio`
(WSMN's `MetricalDuration` has them),
a clef for its `sign`, a chord for its `str()`,
so a system the core does not know still gets a readable label,
and a system it does know gets a glyph.

The sizes and glyph tables are module constants, meant to be tuned.
"""

from __future__ import annotations

import html
import re
from collections.abc import Iterable

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
from openmusickit.objects.omk_object import OmkObject
from openmusickit.objects.part import LineGroup, Part, Stint
from openmusickit.objects.score import Score
from openmusickit.objects.sync_line import SyncLine, SyncPoint
from openmusickit.values.time.clock_time import ClockDuration
from openmusickit.values.time.duration import Duration, GraceDuration, Measurable
from openmusickit.values.tone.tone import Tone

OCTAVE_POINT_SIZE = 6
GLYPH_POINT_SIZE = 14
CLEF_POINT_SIZE = 16
SMALL_POINT_SIZE = 8
DESCRIPTION_POINT_SIZE = 7
DESCRIPTION_COLOR = "#606060"

# Note and rest glyphs by (numerator, denominator) of a whole note.
NOTE_GLYPHS = {
    (2, 1): "𝅜",
    (1, 1): "𝅝",
    (1, 2): "𝅗𝅥",
    (1, 4): "♩",
    (1, 8): "♪",
    (1, 16): "𝅘𝅥𝅯",
    (1, 32): "𝅘𝅥𝅰",
    (1, 64): "𝅘𝅥𝅱",
}
REST_GLYPHS = {
    (1, 1): "𝄻",
    (1, 2): "𝄼",
    (1, 4): "𝄽",
    (1, 8): "𝄾",
    (1, 16): "𝄿",
    (1, 32): "𝅀",
    (1, 64): "𝅁",
}
AUGMENTATION_DOT = "."
TIE = "‿"

# Clef glyphs by the string form of the clef's sign (WSMN's `ClefSign` values).
CLEF_GLYPHS = {"g": "𝄞", "f": "𝄢", "c": "𝄡", "percussion": "𝄥", "tab": "TAB"}

SPANNER_BRACKETS = {"above": ("⌈", "⌉"), "below": ("⌊", "⌋")}

_TRAILING_OCTAVE = re.compile(r"^(.*?)(-?\d+)$")


def escape(text: str) -> str:
    """`text` made safe inside an HTML-like label.

    >>> escape("R&B <3")
    'R&amp;B &lt;3'
    """
    return html.escape(text, quote=False)


def html_label(inner: str) -> str:
    """An HTML-like label around `inner`."""
    return f"<{inner}>"


def sized(text: str, point_size: float) -> str:
    """`text` at `point_size` inside an HTML-like label."""
    return f'<FONT POINT-SIZE="{point_size:g}">{text}</FONT>'


# --- durations ---------------------------------------------------------------------


def _metrical_parts(duration: object) -> tuple[int, int, int, object] | None:
    """(numerator, denominator, dots, ratio) of a duration that has them, else None."""
    try:
        return (
            duration.numerator,  # type: ignore[attr-defined]
            duration.denominator,  # type: ignore[attr-defined]
            duration.dots,  # type: ignore[attr-defined]
            duration.ratio,  # type: ignore[attr-defined]
        )
    except AttributeError:
        return None


def _glyph(duration: Duration | None, table: dict[tuple[int, int], str]) -> str | None:
    if duration is None:
        return None
    if isinstance(duration, GraceDuration):
        base = _glyph(duration.nominal, table)
        return None if base is None else f"grace {base}"
    members = getattr(duration, "members", None)
    if members is not None:
        parts = [_glyph(member, table) for member in members]
        return None if any(part is None for part in parts) else TIE.join(parts)  # type: ignore[arg-type]
    parts = _metrical_parts(duration)
    if parts is None:
        return None
    numerator, denominator, dots, ratio = parts
    glyph = table.get((numerator, denominator))
    if glyph is None:
        return None
    glyph += AUGMENTATION_DOT * dots
    if ratio is not None:
        glyph += f" {ratio.nominal.count}:{ratio.contextual.count}"
    return glyph


def duration_glyph(duration: Duration | None) -> str | None:
    """The note glyph for a duration, or None where there is none.

    A duration with `numerator`, `denominator`, `dots` and `ratio`
    (WSMN's `MetricalDuration`) whose value is a power-of-two fraction of a
    whole note gets its glyph, a dot per augmentation dot, and a tuplet ratio
    as text after it; a tied duration its members joined by a tie; a grace
    duration the word `grace` and its nominal glyph.

    >>> from openmusickit.systems.wsmn.temporal.symbols import quarter, dotted_half, eighth, eighth_in_triplet
    >>> from openmusickit.systems.wsmn.temporal.metrical_duration import MetricalDuration, TiedDuration
    >>> duration_glyph(quarter), duration_glyph(dotted_half), duration_glyph(eighth_in_triplet)
    ('♩', '𝅗𝅥.', '♪ 3:2')
    >>> duration_glyph(TiedDuration((quarter, eighth))), duration_glyph(MetricalDuration(1, 128))
    ('♩‿♪', None)
    >>> from openmusickit.values.time.duration import GraceDuration
    >>> duration_glyph(GraceDuration(eighth)), duration_glyph(None)
    ('grace ♪', None)
    """
    return _glyph(duration, NOTE_GLYPHS)


def rest_glyph(duration: Duration | None) -> str | None:
    """The rest glyph for a duration, or None where there is none.

    >>> from openmusickit.systems.wsmn.temporal.symbols import quarter, half
    >>> rest_glyph(quarter), rest_glyph(half), rest_glyph(None)
    ('𝄽', '𝄼', None)
    """
    return _glyph(duration, REST_GLYPHS)


def clock_label(duration: ClockDuration) -> str:
    """A clock duration as `HH:MM:SS.ffff`.

    >>> clock_label(ClockDuration.from_seconds(5)), clock_label(ClockDuration(3_723_456_789))
    ('00:00:05.0000', '01:02:03.4568')
    """
    total = int(round(duration.microseconds / 100))  # tenths of a millisecond
    sign = "-" if total < 0 else ""
    total = abs(total)
    hours, remainder = divmod(total, 36_000_000)
    minutes, remainder = divmod(remainder, 600_000)
    seconds, fraction = divmod(remainder, 10_000)
    return f"{sign}{hours:02d}:{minutes:02d}:{seconds:02d}.{fraction:04d}"


def duration_label(duration: Duration | None, rest: bool = False) -> str:
    """A duration as text: its glyph where it has one, a clock time, a fraction
    of a whole note, or nothing for an unknown duration.

    >>> from openmusickit.systems.wsmn.temporal.symbols import quarter
    >>> from openmusickit.systems.wsmn.temporal.metrical_duration import MetricalDuration
    >>> duration_label(quarter), duration_label(quarter, rest=True), duration_label(None)
    ('♩', '𝄽', '')
    >>> duration_label(MetricalDuration(1, 128)), duration_label(ClockDuration.from_seconds(90))
    ('1/128', '00:01:30.0000')
    """
    if duration is None:
        return ""
    glyph = rest_glyph(duration) if rest else duration_glyph(duration)
    if glyph is not None:
        return glyph
    if isinstance(duration, ClockDuration):
        return clock_label(duration)
    if isinstance(duration, Measurable):
        return str(duration.rational_length)
    return repr(duration)


# --- tones and clefs ----------------------------------------------------------------


def tone_label(tone: Tone) -> str:
    """A tone's display form as an HTML-like fragment, a trailing octave
    number as a small superscript.

    >>> from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
    >>> from openmusickit.systems.wsmn.tonal.symbols import Eb
    >>> tone_label(TonalVector.from_string("C#4"))
    'C♯<SUP><FONT POINT-SIZE="6">4</FONT></SUP>'
    >>> tone_label(Eb)
    'E♭'
    """
    text = format(tone)
    match = _TRAILING_OCTAVE.match(text)
    if match is None:
        return escape(text)
    return escape(match.group(1)) + f"<SUP>{sized(escape(match.group(2)), OCTAVE_POINT_SIZE)}</SUP>"


def sorted_tones(tones: Iterable[Tone]) -> list[Tone]:
    """Tones lowest first where they compare, else by display form."""
    try:
        return sorted(tones)  # type: ignore[type-var]
    except TypeError:
        return sorted(tones, key=format)


def clef_glyph(clef: object) -> str | None:
    """The glyph for a clef whose `sign` is one the table knows, with its
    octave change as a small number above or below; None otherwise.

    >>> from openmusickit.systems.wsmn.scoring.symbols import treble_clef, bass_clef, bass_clef_8vb
    >>> clef_glyph(treble_clef), clef_glyph(bass_clef), clef_glyph(bass_clef_8vb), clef_glyph(None)
    ('𝄞', '𝄢', '𝄢<SUB>8</SUB>', None)
    """
    sign = getattr(clef, "sign", None)
    if sign is None:
        return None
    glyph = CLEF_GLYPHS.get(str(sign))
    if glyph is None:
        return None
    change = getattr(clef, "octave_change", 0) or 0
    if change:
        number = {1: "8", 2: "15"}.get(abs(change), str(abs(change)))
        glyph += f"<SUP>{number}</SUP>" if change > 0 else f"<SUB>{number}</SUB>"
    return glyph


# --- the default label ----------------------------------------------------------------


def _section_text(section: LyricSection) -> str:
    if section.section_name:
        return section.section_name
    parts = [section.section_type, str(section.section_number) if section.section_number else None]
    return " ".join(part for part in parts if part) or "section"


def default_label(obj: OmkObject) -> str:
    """A concise label for any object: its content where it has a display
    form, its class name otherwise.

    >>> from openmusickit.systems.wsmn.temporal.symbols import quarter
    >>> from openmusickit.systems.wsmn.tonal.symbols import C, maj
    >>> from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
    >>> default_label(NoteEvent(tones={TonalVector.from_string("C4")}, duration=quarter))
    '<C<SUP><FONT POINT-SIZE="6">4</FONT></SUP> <FONT POINT-SIZE="14">♩</FONT>>'
    >>> default_label(ChordEvent(chord=C(maj), duration=quarter))
    '<C <FONT POINT-SIZE="14">♩</FONT>>'
    >>> default_label(Part(name="Flute")), default_label(OmkObject())
    ('Flute', 'OmkObject')
    """
    if isinstance(obj, NoteEvent):
        if obj.is_rest:
            glyph = rest_glyph(obj.duration)
            if glyph is None:
                return f"rest {duration_label(obj.duration)}".rstrip()
            return html_label(sized(glyph, GLYPH_POINT_SIZE))
        tones = " ".join(tone_label(tone) for tone in sorted_tones(obj.tones))
        duration = duration_label(obj.duration)
        if duration:
            tones = f"{tones} {sized(escape(duration), GLYPH_POINT_SIZE)}".strip()
        return html_label(tones)
    if isinstance(obj, ChordEvent):
        text = escape(str(obj.chord))
        duration = duration_label(obj.duration)
        if duration:
            text = f"{text} {sized(escape(duration), GLYPH_POINT_SIZE)}"
        return html_label(text)
    if isinstance(obj, LyricSyllable):
        return str(obj)
    if isinstance(obj, ClefEvent):
        glyph = clef_glyph(obj.clef)
        if glyph is not None:
            return html_label(sized(glyph, CLEF_POINT_SIZE))
        return "clef" if obj.clef is None else f"clef {obj.clef!r}"
    if isinstance(obj, MeterEvent):
        if obj.meter is None:
            return "meter"
        presentation = getattr(obj.meter, "presentation", None)
        if presentation:
            return "/".join(presentation)
        return f"meter {obj.meter.rational_length}"
    if isinstance(obj, TempoEvent):
        if obj.term is not None:
            return obj.term.name
        return "tempo"
    if isinstance(obj, ModalContextEvent):
        name = getattr(obj.modal_context, "name", None)
        return f"key {name}" if name else "key"
    if isinstance(obj, DivisionEvent):
        components = getattr(obj.shape, "components", None)
        return " ".join(str(component) for component in components) if components else "division"
    if isinstance(obj, Marking | MarkSpanner):
        return obj.mark.name
    if isinstance(obj, LyricSection):
        return _section_text(obj)
    if isinstance(obj, Stint):
        if obj.transposition is None:
            return "stint"
        representation = getattr(obj.transposition, "interval", None)
        spelled = getattr(representation, "unicode", None) or str(obj.transposition)
        return f"stint {spelled}"
    if isinstance(obj, Part):
        return obj.name
    if isinstance(obj, LineGroup):
        return obj.name or "group"
    if isinstance(obj, Score):
        return obj.title or "score"
    if isinstance(obj, SyncLine):
        return obj.name or "sync line"
    if isinstance(obj, SyncPoint):
        return obj.name or duration_label(obj.offset)
    return type(obj).__name__


# --- blocks placed by the layout ----------------------------------------------------------


def spanner_markers(text: str, side: str) -> tuple[str, str]:
    """The start and end marker labels of a spanner: `text` with an opening
    bracket before it and a closing bracket after it, the brackets' shape
    saying which side of the line the spanner sits on (`"above"` or `"below"`).

    >>> spanner_markers("slur", "above"), spanner_markers("verse 1", "below")
    (('⌈slur', 'slur⌉'), ('⌊verse 1', 'verse 1⌋'))
    """
    opening, closing = SPANNER_BRACKETS[side]
    return f"{opening}{text}", f"{text}{closing}"


def title_block(score: Score, border_color: str) -> str:
    """The score's title block: a bordered table with the title in bold and
    whichever of subtitle, composer, lyricist, arranger, opus and dedication are set.

    >>> print(title_block(Score(title="Twinkle", lyricist="Jane Taylor"), "#303030"))  # doctest: +NORMALIZE_WHITESPACE
    <<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4" COLOR="#303030">
    <TR><TD ALIGN="LEFT"><B>Twinkle</B></TD></TR>
    <TR><TD ALIGN="LEFT"><FONT POINT-SIZE="8">lyrics: Jane Taylor</FONT></TD></TR></TABLE>>
    """
    rows = [f'<TR><TD ALIGN="LEFT"><B>{escape(score.title or "score")}</B></TD></TR>']
    lines = [
        score.subtitle,
        f"music: {score.composer}" if score.composer else None,
        f"lyrics: {score.lyricist}" if score.lyricist else None,
        f"arranged: {score.arranger}" if score.arranger else None,
        score.opus,
        score.dedication,
    ]
    for line in lines:
        if line:
            rows.append(f'<TR><TD ALIGN="LEFT">{sized(escape(line), SMALL_POINT_SIZE)}</TD></TR>')
    table = (
        f'<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4" COLOR="{border_color}">\n'
        + "\n".join(rows)
        + "</TABLE>"
    )
    return html_label(table)


_BLOCK_ROW_HEIGHT = 12


def _bar_cell(color: str, width: float, horizontal: bool, span: int) -> str:
    if horizontal:
        return (
            f'<TD PORT="bar" COLSPAN="{span}" HEIGHT="{width:g}" '
            f'BGCOLOR="{color}" CELLPADDING="0"></TD>'
        )
    return f'<TD PORT="bar" ROWSPAN="3" WIDTH="{width:g}" BGCOLOR="{color}" CELLPADDING="0"></TD>'


def sync_block(
    time: str,
    name: str | None,
    description: str | None,
    *,
    bar_color: str,
    bar_width: float,
    horizontal: bool,
    dot: bool = True,
) -> str:
    """A block of a sync bar: a dot resting on the bar with `time` beside it,
    `name` and `description` on the lines after the bar. Every block has the
    same number of rows, so the bar stays level from block to block.

    In a horizontal layout the bar is a filled row under the dot and the
    time; in a vertical one it is a filled first column that runs down
    beside them. The head block (`dot=False`, the line's name as `time`) and
    the end block (nothing at all) use the same skeleton.

    >>> block = sync_block("00:00:05.0000", "cue", None, bar_color="#b0b0b0", bar_width=4, horizontal=True)
    >>> block.startswith("<<TABLE"), "PORT=\\"bar\\"" in block, "cue" in block
    (True, True, True)
    """
    mark = sized("●", 10) if dot else ""
    first = sized(escape(time), SMALL_POINT_SIZE) if time else ""
    second = sized(escape(name), SMALL_POINT_SIZE) if name else ""
    third = (
        f'<FONT POINT-SIZE="{DESCRIPTION_POINT_SIZE}" COLOR="{DESCRIPTION_COLOR}">'
        f"{escape(description)}</FONT>"
        if description
        else ""
    )
    h = _BLOCK_ROW_HEIGHT
    if horizontal:
        rows = [
            f'<TR><TD VALIGN="BOTTOM" HEIGHT="{h}" WIDTH="8">{mark}</TD>'
            f'<TD ALIGN="LEFT" HEIGHT="{h}">{first}</TD></TR>',
            f"<TR>{_bar_cell(bar_color, bar_width, True, 2)}</TR>",
            f'<TR><TD></TD><TD ALIGN="LEFT" HEIGHT="{h}">{second}</TD></TR>',
            f'<TR><TD></TD><TD ALIGN="LEFT" HEIGHT="{h}">{third}</TD></TR>',
        ]
    else:
        rows = [
            f"<TR>{_bar_cell(bar_color, bar_width, False, 1)}"
            f'<TD WIDTH="10">{mark}</TD><TD ALIGN="LEFT" HEIGHT="{h}">{first}</TD></TR>',
            f'<TR><TD></TD><TD ALIGN="LEFT" HEIGHT="{h}">{second}</TD></TR>',
            f'<TR><TD></TD><TD ALIGN="LEFT" HEIGHT="{h}">{third}</TD></TR>',
        ]
    table = (
        '<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="1">'
        + "".join(rows)
        + "</TABLE>"
    )
    return html_label(table)
