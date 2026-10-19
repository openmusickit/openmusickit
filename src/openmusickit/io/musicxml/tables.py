"""What MusicXML calls things and what WSMN calls them.

Every table maps a MusicXML name (an element name, a `kind`, a `bar-style`,
a `type` of note) to the ready-made OMK symbol, so that the reader and the
writer agree on one spelling in each direction. A name absent from a table
is the reader's cue to warn and mint or skip; the tests pin which of the
WSMN symbols the tables cover.
"""

from __future__ import annotations

from openmusickit.systems.wsmn.scoring import symbols as scoring
from openmusickit.systems.wsmn.scoring.bar_line_shape import BarLineShape
from openmusickit.systems.wsmn.scoring.bracket_shape import BracketSymbol, GroupBarLines
from openmusickit.systems.wsmn.scoring.staff_clef import ClefSign
from openmusickit.systems.wsmn.tonal import symbols as tonal
from openmusickit.systems.wsmn.tonal.chords import ChordType
from openmusickit.systems.wsmn.tonal.key import ModePattern
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from openmusickit.values.scoring.mark import Mark, MarkType
from openmusickit.values.scoring.tempo_term import TempoTerm

# --- pitch and duration ---------------------------------------------------------

STEPS = "CDEFGAB"
STEP_CHROMATIC = (0, 2, 4, 5, 7, 9, 11)

# <type> -> (numerator, denominator) of the plain MetricalDuration
NOTE_TYPES: dict[str, tuple[int, int]] = {
    "1024th": (1, 1024),
    "512th": (1, 512),
    "256th": (1, 256),
    "128th": (1, 128),
    "64th": (1, 64),
    "32nd": (1, 32),
    "16th": (1, 16),
    "eighth": (1, 8),
    "quarter": (1, 4),
    "half": (1, 2),
    "whole": (1, 1),
    "breve": (2, 1),
    "long": (4, 1),
    "maxima": (8, 1),
}


def tone_from_pitch(step: str, alter: int, octave: int) -> TonalVector:
    """The tone a `<pitch>` names: step letter, chromatic alteration, MusicXML octave.

    >>> tone_from_pitch("B", -1, 3)
    TonalVector((6, 10, -1))
    """
    degree = STEPS.index(step.strip().upper())
    return TonalVector((degree, (STEP_CHROMATIC[degree] + alter) % 12, octave - 4))


def pitch_of_tone(tone: TonalVector) -> tuple[str, int, int]:
    """The `<pitch>` of an octave-qualified tone: step, alter, octave.
    Alterations beyond the semitone window read modulo 12, so C♯ is (C, 1) and
    C♭ is (C, -1), whatever octave arithmetic produced them.

    >>> pitch_of_tone(TonalVector((6, 10, -1)))
    ('B', -1, 3)
    >>> pitch_of_tone(tone_from_pitch("C", -1, 4))
    ('C', -1, 4)

    Raises
    ------
    ValueError
        if the tone has no octave.
    """
    if not tone.has_octave:
        raise ValueError(f"{tone!r} has no octave; MusicXML pitches need one.")
    alter = (tone.c - STEP_CHROMATIC[tone.d] + 6) % 12 - 6
    return STEPS[tone.d], alter, tone.o + 4


# --- attributes -------------------------------------------------------------------

CLEF_SIGNS: dict[str, ClefSign] = {
    "G": ClefSign.G,
    "F": ClefSign.F,
    "C": ClefSign.C,
    "percussion": ClefSign.PERCUSSION,
    "TAB": ClefSign.TAB,
    "none": ClefSign.NONE,
}

MODES: dict[str, ModePattern] = {
    "major": tonal.Major,
    "minor": tonal.Minor,
    "ionian": tonal.Ionian,
    "dorian": tonal.Dorian,
    "phrygian": tonal.Phrygian,
    "lydian": tonal.Lydian,
    "mixolydian": tonal.Mixolydian,
    "aeolian": tonal.Aeolian,
    "locrian": tonal.Locrian,
}

# Steps from the major tonic to the tonic of each mode on the same signature.
MODE_TONIC_DEGREE: dict[str, int] = {
    "major": 0,
    "ionian": 0,
    "dorian": 1,
    "phrygian": 2,
    "lydian": 3,
    "mixolydian": 4,
    "minor": 5,
    "aeolian": 5,
    "locrian": 6,
}

# --- bar lines ------------------------------------------------------------------------

BAR_STYLES: dict[str, BarLineShape] = {
    "regular": scoring.single_bar,
    "dotted": scoring.dotted_bar,
    "dashed": scoring.dashed_bar,
    "heavy": scoring.heavy_bar,
    "light-light": scoring.double_bar,
    "light-heavy": scoring.final_bar,
    "heavy-light": scoring.reverse_final_bar,
    "heavy-heavy": scoring.double_heavy_bar,
    "tick": scoring.tick_bar,
    "short": scoring.short_bar,
    "none": scoring.invisible_bar,
}

# --- part groups ---------------------------------------------------------------------

GROUP_SYMBOLS: dict[str, BracketSymbol | None] = {
    "bracket": BracketSymbol.BRACKET,
    "brace": BracketSymbol.BRACE,
    "line": BracketSymbol.LINE,
    "square": BracketSymbol.SQUARE,
    "none": None,
}

GROUP_BARLINES: dict[str, GroupBarLines] = {
    "yes": GroupBarLines.JOINED,
    "no": GroupBarLines.SEPARATE,
    "Mensurstrich": GroupBarLines.MENSURSTRICH,
}

# --- chord symbols ------------------------------------------------------------------------

KINDS: dict[str, ChordType] = {
    "major": tonal.maj,
    "minor": tonal.min_,
    "augmented": tonal.aug,
    "diminished": tonal.dim,
    "dominant": tonal.dom7,
    "major-seventh": tonal.maj7,
    "minor-seventh": tonal.min7,
    "diminished-seventh": tonal.dim7,
    "augmented-seventh": tonal.dom7_sharp5,
    "half-diminished": tonal.hdim7,
    "major-minor": tonal.min_maj7,
    "major-sixth": tonal.maj6,
    "minor-sixth": tonal.min6,
    "dominant-ninth": tonal.dom9,
    "major-ninth": tonal.maj9,
    "minor-ninth": tonal.min9,
    "dominant-11th": tonal.dom11,
    "major-11th": tonal.maj11,
    "minor-11th": tonal.min11,
    "dominant-13th": tonal.dom13,
    "major-13th": tonal.maj13,
    "minor-13th": tonal.min13,
    "suspended-second": tonal.sus2,
    "suspended-fourth": tonal.sus4,
    "power": tonal.pow5,
}

# --- marks, by the MusicXML element that names them ------------------------------------------------

ARTICULATIONS: dict[str, Mark] = {
    "accent": scoring.accent,
    "strong-accent": scoring.marcato,
    "staccato": scoring.staccato,
    "tenuto": scoring.tenuto,
    "detached-legato": scoring.portato,
    "staccatissimo": scoring.staccatissimo,
    "spiccato": scoring.spiccato,
    "scoop": scoring.scoop,
    "plop": scoring.plop,
    "doit": scoring.doit,
    "falloff": scoring.falloff,
    "breath-mark": scoring.breath_mark,
    "caesura": scoring.caesura,
    "stress": scoring.stress,
    "unstress": scoring.unstress,
    "soft-accent": scoring.soft_accent,
}

# The text of <breath-mark>, when it names the glyph.
BREATH_MARKS: dict[str, Mark] = {
    "comma": scoring.breath_mark,
    "tick": scoring.tick_breath_mark,
    "upbow": scoring.upbow_breath_mark,
    "salzedo": scoring.salzedo_breath_mark,
}

ORNAMENTS: dict[str, Mark] = {
    "trill-mark": scoring.trill,
    "turn": scoring.turn,
    "delayed-turn": scoring.delayed_turn,
    "inverted-turn": scoring.inverted_turn,
    "delayed-inverted-turn": scoring.delayed_inverted_turn,
    "vertical-turn": scoring.vertical_turn,
    "inverted-vertical-turn": scoring.inverted_vertical_turn,
    "shake": scoring.shake,
    "wavy-line": scoring.wavy_line,
    "mordent": scoring.mordent,
    "inverted-mordent": scoring.inverted_mordent,
    "schleifer": scoring.schleifer,
    "tremolo": scoring.tremolo,
    "haydn": scoring.haydn_ornament,
}

TECHNICAL: dict[str, Mark] = {
    "up-bow": scoring.up_bow,
    "down-bow": scoring.down_bow,
    "harmonic": scoring.harmonic,
    "open-string": scoring.open_string,
    "thumb-position": scoring.thumb_position,
    "double-tongue": scoring.double_tongue,
    "triple-tongue": scoring.triple_tongue,
    "stopped": scoring.stopped,
    "snap-pizzicato": scoring.snap_pizzicato,
    "hammer-on": scoring.hammer_on,
    "pull-off": scoring.pull_off,
    "bend": scoring.bend,
    "tap": scoring.tap,
    "heel": scoring.heel,
    "toe": scoring.toe,
    "fingernails": scoring.fingernails,
    "brass-bend": scoring.brass_bend,
    "flip": scoring.flip,
    "smear": scoring.smear,
    "open": scoring.open_,
    "half-muted": scoring.half_muted,
    "golpe": scoring.golpe,
}

# <technical> children whose text picks the mark.
FINGERINGS: dict[str, Mark] = {str(i): getattr(scoring, f"fingering_{i}") for i in range(6)}
STRINGS: dict[str, Mark] = {str(i): getattr(scoring, f"string_{i}") for i in range(1, 7)}
PLUCKS: dict[str, Mark] = {
    "p": scoring.pluck_p,
    "i": scoring.pluck_i,
    "m": scoring.pluck_m,
    "a": scoring.pluck_a,
    "c": scoring.pluck_c,
}
HANDBELLS: dict[str, Mark] = {
    "belltree": scoring.belltree,
    "damp": scoring.handbell_damp,
    "echo": scoring.echo,
    "gyro": scoring.gyro,
    "hand martellato": scoring.hand_martellato,
    "mallet lift": scoring.mallet_lift,
    "mallet table": scoring.mallet_table,
    "martellato": scoring.martellato,
    "martellato lift": scoring.martellato_lift,
    "muted martellato": scoring.muted_martellato,
    "pluck lift": scoring.pluck_lift,
    "swing": scoring.swing,
}
HARMON_MUTES: dict[str, Mark] = {  # by <harmon-closed>
    "yes": scoring.harmon_mute_closed,
    "no": scoring.harmon_mute_open,
    "half": scoring.harmon_mute_half,
}
HOLES: dict[str, Mark] = {  # by <hole-closed>
    "yes": scoring.hole_closed,
    "no": scoring.hole_open,
    "half": scoring.hole_half,
}

# Those <technical> children that belong to one tone of a chord rather than
# to the chord (a fingering on one note, a harmonic on one string); the
# reader splits a chord whose tones differ in these (decision 9 of the plan).
PER_TONE_TECHNICAL = frozenset(
    {
        "fingering",
        "string",
        "fret",
        "pluck",
        "harmonic",
        "open-string",
        "stopped",
        "thumb-position",
        "hammer-on",
        "pull-off",
        "bend",
        "tap",
        "hole",
    }
)

DYNAMICS: dict[str, Mark] = {
    "p": scoring.piano,
    "pp": scoring.pianissimo,
    "ppp": scoring.pianississimo,
    "pppp": scoring.pppp,
    "ppppp": scoring.ppppp,
    "pppppp": scoring.pppppp,
    "f": scoring.forte,
    "ff": scoring.fortissimo,
    "fff": scoring.fortississimo,
    "ffff": scoring.ffff,
    "fffff": scoring.fffff,
    "ffffff": scoring.ffffff,
    "mp": scoring.mezzo_piano,
    "mf": scoring.mezzo_forte,
    "sf": scoring.sf,
    "sfp": scoring.sfp,
    "sfpp": scoring.sfpp,
    "fp": scoring.forte_piano,
    "rf": scoring.rf,
    "rfz": scoring.rinforzando,
    "sfz": scoring.sforzando,
    "sffz": scoring.sffz,
    "fz": scoring.fz,
    "n": scoring.niente,
    "pf": scoring.pf,
    "sfzp": scoring.sfzp,
}

FERMATAS: dict[str, Mark] = {  # by the element's text (the shape); empty is the normal one
    "": scoring.fermata,
    "normal": scoring.fermata,
    "angled": scoring.short_fermata,
    "square": scoring.long_fermata,
    "double-angled": scoring.very_short_fermata,
    "double-square": scoring.very_long_fermata,
    "double-dot": scoring.henze_long_fermata,
    "half-curve": scoring.henze_short_fermata,
    "curlew": scoring.curlew,
}

ARPEGGIOS: dict[str | None, Mark] = {  # by <arpeggiate direction>
    None: scoring.arpeggio,
    "up": scoring.arpeggio_up,
    "down": scoring.arpeggio_down,
}

WEDGES: dict[tuple[str, bool], Mark] = {  # (type, niente)
    ("crescendo", False): scoring.crescendo,
    ("diminuendo", False): scoring.decrescendo,
    ("crescendo", True): scoring.crescendo_dal_niente,
    ("diminuendo", True): scoring.decrescendo_al_niente,
}

# <octave-shift>: "down" shifts the written notes down from where they sound,
# which is what an 8va line over the staff says.
OCTAVE_SHIFTS: dict[tuple[str, int], Mark] = {
    ("down", 8): scoring.ottava_alta,
    ("up", 8): scoring.ottava_bassa,
    ("down", 15): scoring.quindicesima_alta,
    ("up", 15): scoring.quindicesima_bassa,
}

PEDALS: dict[str, Mark] = {"sustain": scoring.sustain_pedal, "sostenuto": scoring.sostenuto_pedal}

NOTATION_SPANS: dict[str, Mark] = {  # numbered start/stop pairs inside <notations>
    "slur": scoring.slur,
    "glissando": scoring.glissando,
    "slide": scoring.portamento,
}


def _by_name(cls: type) -> dict[str, object]:
    """Every ready-made symbol of `cls`, keyed by its name and each alias, in lower case."""
    table: dict[str, object] = {}
    for value in vars(scoring).values():
        if isinstance(value, cls):
            table.setdefault(value.name.lower(), value)
            for alias in value.aliases:
                table.setdefault(alias.lower(), value)
    return table


# Free text (<words>, <other-dynamics>, <other-articulation>, ...) that names
# a ready-made mark or tempo term, by its name or an alias, case-folded.
WORDS: dict[str, Mark] = _by_name(Mark)  # type: ignore[assignment]
TEMPO_TERMS: dict[str, TempoTerm] = _by_name(TempoTerm)  # type: ignore[assignment]

# Words for a gradual change of tempo. They have no mark yet (pre-plan P3);
# the reader records them as text and warns that the span has no end.
GRADUAL_TEMPO_WORDS = frozenset(
    {
        "rit",
        "rit.",
        "ritard",
        "ritard.",
        "ritardando",
        "riten",
        "riten.",
        "ritenuto",
        "rall",
        "rall.",
        "rallentando",
        "accel",
        "accel.",
        "accelerando",
        "calando",
        "stringendo",
        "string.",
        "allargando",
        "morendo",
        "smorzando",
        "smorz.",
        "slentando",
        "più mosso",
        "piu mosso",
        "meno mosso",
        "stretto",
    }
)
GRADUAL_TEMPO_PREFIXES = ("poco a poco ", "poco ", "molto ", "un poco ", "sempre ")


def normalize_words(text: str) -> str:
    """Free text as the tables key it: trimmed, lower case, one space between words."""
    return " ".join(text.split()).lower()


def is_gradual_tempo(text: str) -> bool:
    """Whether `text` asks for a gradual change of tempo (`rit.`, `poco a poco accel.`).

    >>> is_gradual_tempo("poco rit."), is_gradual_tempo("a tempo"), is_gradual_tempo("Rallentando")
    (True, False, True)
    """
    words = normalize_words(text)
    for prefix in GRADUAL_TEMPO_PREFIXES:
        if words.startswith(prefix):
            words = words[len(prefix) :]
    return words in GRADUAL_TEMPO_WORDS


# --- the tables backwards, for the writer ------------------------------------------------


def inverse[K, V](table: dict[K, V]) -> dict[V, K]:
    """`table` the other way round; where several names share a symbol, the first is kept.

    >>> inverse(FERMATAS)[scoring.fermata]
    ''
    """
    backwards: dict[V, K] = {}
    for key, value in table.items():
        backwards.setdefault(value, key)
    return backwards


NOTE_TYPE_NAMES = inverse(NOTE_TYPES)  # (numerator, denominator) -> <type>
CLEF_SIGN_NAMES = inverse(CLEF_SIGNS)
BAR_STYLE_NAMES = inverse(BAR_STYLES)
GROUP_SYMBOL_NAMES = inverse(GROUP_SYMBOLS)
GROUP_BARLINE_NAMES = inverse(GROUP_BARLINES)
KIND_NAMES = inverse(KINDS)
MODE_NAMES = inverse(MODES)

# A mark's element inside <notations>: (the wrapping element or None, the element, its text).
NOTATION_ELEMENTS: dict[Mark, tuple[str | None, str, str | None]] = {}
for _wrapper, _table in (
    ("articulations", ARTICULATIONS),
    ("ornaments", ORNAMENTS),
    ("technical", TECHNICAL),
):
    for _name, _mark in _table.items():
        NOTATION_ELEMENTS.setdefault(_mark, (_wrapper, _name, None))
for _text, _mark in BREATH_MARKS.items():
    if _mark is not scoring.breath_mark:
        NOTATION_ELEMENTS.setdefault(_mark, ("articulations", "breath-mark", _text))
for _element, _table in (
    ("fingering", FINGERINGS),
    ("string", STRINGS),
    ("pluck", PLUCKS),
    ("handbell", HANDBELLS),
):
    for _text, _mark in _table.items():
        NOTATION_ELEMENTS.setdefault(_mark, ("technical", _element, _text))
for _text, _mark in FERMATAS.items():
    NOTATION_ELEMENTS.setdefault(_mark, (None, "fermata", _text or None))
NOTATION_ELEMENTS[scoring.non_arpeggio] = (None, "non-arpeggiate", None)

# <harmon-mute> and <hole> say which mark they are by a child element.
HARMON_MUTE_STATES = inverse(HARMON_MUTES)
HOLE_STATES = inverse(HOLES)
ARPEGGIO_DIRECTIONS = inverse(ARPEGGIOS)
DYNAMIC_NAMES = inverse(DYNAMICS)
WEDGE_TYPES = inverse(WEDGES)
OCTAVE_SHIFT_TYPES = inverse(OCTAVE_SHIFTS)
NOTATION_SPAN_NAMES = inverse(NOTATION_SPANS)

# The marks the reader takes from a <technical> child that belongs to one tone
# (PER_TONE_TECHNICAL), so that the writer puts them back on that tone's <note>.
PER_TONE_MARKS = frozenset(
    [
        *FINGERINGS.values(),
        *STRINGS.values(),
        *PLUCKS.values(),
        *HOLES.values(),
        *(TECHNICAL[name] for name in PER_TONE_TECHNICAL if name in TECHNICAL),
    ]
)
# A mark the reader mints for an unlisted fingering, string, fret or pluck is
# named for its element: "fret 3", "string 7".
MINTED_PER_TONE_PREFIXES = ("fingering", "string", "fret", "pluck")


def is_per_tone(mark: Mark) -> bool:
    """Whether `mark` belongs to one tone of a chord, as a fingering does,
    rather than to the chord, as a staccato does.

    >>> is_per_tone(scoring.fingering_2), is_per_tone(scoring.staccato)
    (True, False)
    >>> is_per_tone(Mark(name="fret 3", kind=MarkType.FINGERING))
    True
    """
    if mark in PER_TONE_MARKS:
        return True
    return mark.kind is MarkType.FINGERING and mark.name.split(" ")[0] in MINTED_PER_TONE_PREFIXES
