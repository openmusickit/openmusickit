"""Ready-to-go marks (articulations, dynamics, ornaments, techniques,
expression and navigation words, and the like), tempo terms, and bar lines.
Percussion has its marks here (`ghost`, `buzz_roll`, `choke`,
sticking, beaters, snares) and its tones in `systems.wsmn.percussion.symbols`.

```
from openmusickit.systems.wsmn.scoring.symbols import *
```

Coverage is intended to be a superset of the marks available in LilyPond and
MusicXML. Where the two disagree on naming, the most common American-English
name is used for ``name`` and the alternatives appear in ``aliases``.

A word the table lacks, and every rehearsal mark, is a `Mark` made for the score:
`Marking(mark=Mark(name="A", kind=MarkType.REHEARSAL, attachment_mode=AttachmentMode.SINGLE))`.

Examples
--------

>>> staccato.kind
<MarkType.ARTICULATION: 'articulation'>

>>> piano.aliases
('p',)

>>> slur.attachment_mode
<AttachmentMode.SPAN: 'span'>

>>> crescendo.attachment_mode
<AttachmentMode.EITHER: 'either'>

>>> slur.binds, phrase_mark.binds
(True, False)

>>> dolce.kind
<MarkType.EXPRESSION: 'expression'>

>>> da_capo.aliases
('D.C.',)

>>> allegro.name
'allegro'

>>> end_repeat
BarLineShape(BarLineComponent.DOTS, BarLineComponent.THIN, BarLineComponent.THICK)
"""

from openmusickit.systems.wsmn.scoring.bar_line_shape import BarLineComponent, BarLineShape
from openmusickit.values.scoring.mark import AttachmentMode, Mark, MarkType
from openmusickit.values.scoring.tempo_term import TempoTerm

# =============================================================================
# ARTICULATIONS
# =============================================================================

accent = Mark(
    name="accent",
    description="An accent (>): the note is played with emphasis.",
    kind=MarkType.ARTICULATION,
    attachment_mode=AttachmentMode.SINGLE,
)

marcato = Mark(
    name="marcato",
    description="A marcato (^): a strong, heavily emphasized accent.",
    kind=MarkType.ARTICULATION,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("strong accent", "martellato accent"),
)

staccato = Mark(
    name="staccato",
    description="A staccato dot: the note is played detached and shortened.",
    kind=MarkType.ARTICULATION,
    attachment_mode=AttachmentMode.SINGLE,
)

staccatissimo = Mark(
    name="staccatissimo",
    description="A staccatissimo wedge: the note is played very short and detached.",
    kind=MarkType.ARTICULATION,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("wedge",),
)

tenuto = Mark(
    name="tenuto",
    description="A tenuto line: the note is held for its full value, often with slight emphasis.",
    kind=MarkType.ARTICULATION,
    attachment_mode=AttachmentMode.SINGLE,
)

portato = Mark(
    name="portato",
    description="A portato (tenuto line with staccato dot): notes slightly separated but not fully detached.",
    kind=MarkType.ARTICULATION,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("detached legato", "mezzo-staccato", "louré"),
)

espressivo = Mark(
    name="espressivo",
    description="An espressivo mark (<>): the note is played expressively, with a slight swell.",
    kind=MarkType.ARTICULATION,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("espr.",),
)

soft_accent = Mark(
    name="soft accent",
    description="A soft accent (<>): a gentle swell on a single note (MusicXML soft-accent).",
    kind=MarkType.ARTICULATION,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("messa di voce", "swell"),
)

spiccato = Mark(
    name="spiccato",
    description="A spiccato mark: a bouncing, off-the-string bow stroke.",
    kind=MarkType.ARTICULATION,
    attachment_mode=AttachmentMode.SINGLE,
)

stress = Mark(
    name="stress",
    description="A stress mark: the note receives metric or agogic emphasis.",
    kind=MarkType.ARTICULATION,
    attachment_mode=AttachmentMode.SINGLE,
)

unstress = Mark(
    name="unstress",
    description="An unstress mark: the note is explicitly de-emphasized.",
    kind=MarkType.ARTICULATION,
    attachment_mode=AttachmentMode.SINGLE,
)

ghost = Mark(
    name="ghost",
    description="A ghost note (the head in parentheses): played very softly, felt more than heard.",
    kind=MarkType.ARTICULATION,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("ghost note", "parenthesized", "parenthesised"),
)

# --- jazz / commercial articulations ----------------------------------------

scoop = Mark(
    name="scoop",
    description="A scoop: slide up into the note from below.",
    kind=MarkType.ARTICULATION,
    attachment_mode=AttachmentMode.SINGLE,
)

plop = Mark(
    name="plop",
    description="A plop: slide down into the note from above.",
    kind=MarkType.ARTICULATION,
    attachment_mode=AttachmentMode.SINGLE,
)

doit = Mark(
    name="doit",
    description="A doit: slide upward out of the note.",
    kind=MarkType.ARTICULATION,
    attachment_mode=AttachmentMode.SINGLE,
)

falloff = Mark(
    name="falloff",
    description="A falloff: slide downward out of the note.",
    kind=MarkType.ARTICULATION,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("fall",),
)


# =============================================================================
# DYNAMICS
# =============================================================================

# --- absolute dynamics --------------------------------------------------------

pppppp = Mark(
    name="pppppp",
    description="Six p's: as quiet as possible.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.SINGLE,
)

ppppp = Mark(
    name="ppppp",
    description="Five p's: extremely quiet.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.SINGLE,
)

pppp = Mark(
    name="pppp",
    description="Four p's: extremely quiet.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("pianissississimo",),
)

pianississimo = Mark(
    name="pianississimo",
    description="ppp: very, very quiet.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("ppp",),
)

pianissimo = Mark(
    name="pianissimo",
    description="pp: very quiet.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("pp",),
)

piano = Mark(
    name="piano",
    description="p: quiet.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("p",),
)

mezzo_piano = Mark(
    name="mezzo-piano",
    description="mp: moderately quiet.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("mp",),
)

mezzo_forte = Mark(
    name="mezzo-forte",
    description="mf: moderately loud.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("mf",),
)

forte = Mark(
    name="forte",
    description="f: loud.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("f",),
)

fortissimo = Mark(
    name="fortissimo",
    description="ff: very loud.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("ff",),
)

fortississimo = Mark(
    name="fortississimo",
    description="fff: very, very loud.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("fff",),
)

ffff = Mark(
    name="ffff",
    description="Four f's: extremely loud.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("fortissississimo",),
)

fffff = Mark(
    name="fffff",
    description="Five f's: extremely loud.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.SINGLE,
)

ffffff = Mark(
    name="ffffff",
    description="Six f's: as loud as possible.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.SINGLE,
)

niente = Mark(
    name="niente",
    description="n: nothing; silence, typically as the start or end of a hairpin.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("n",),
)

# --- accented / compound dynamics ---------------------------------------------

sforzando = Mark(
    name="sforzando",
    description="sfz: a sudden, strong accent on a single note or chord.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("sfz", "sforzato"),
)

sf = Mark(
    name="sf",
    description="sf: sforzando, written in its shorter form. Same meaning as sfz, distinct glyph.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.SINGLE,
)

sff = Mark(
    name="sff",
    description="sff: a very strong sudden accent.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.SINGLE,
)

sffz = Mark(
    name="sffz",
    description="sffz: a very strong sforzando.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.SINGLE,
)

sfp = Mark(
    name="sfp",
    description="sfp: sforzando, immediately followed by piano.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("sforzando piano",),
)

sfpp = Mark(
    name="sfpp",
    description="sfpp: sforzando, immediately followed by pianissimo.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.SINGLE,
)

sfzp = Mark(
    name="sfzp",
    description="sfzp: sforzato, immediately followed by piano.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.SINGLE,
)

forte_piano = Mark(
    name="forte-piano",
    description="fp: loud, then immediately quiet.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("fp",),
)

pf = Mark(
    name="pf",
    description="pf: poco forte (somewhat loud), or in some usage piano then forte.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("poco forte",),
)

fz = Mark(
    name="fz",
    description="fz: forzando; a forced, accented note.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("forzando", "forzato"),
)

rinforzando = Mark(
    name="rinforzando",
    description="rfz: a sudden reinforcement of a note or short passage.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("rfz",),
)

rf = Mark(
    name="rf",
    description="rf: rinforzando, written in its shorter form. Same meaning as rfz, distinct glyph.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.SINGLE,
)

subito_piano = Mark(
    name="subito piano",
    description="sp: suddenly quiet.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("sp",),
)

subito_pianissimo = Mark(
    name="subito pianissimo",
    description="spp: suddenly very quiet.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("spp",),
)

# --- gradual dynamics (hairpins and text) -------------------------------------

crescendo = Mark(
    name="crescendo",
    description="A crescendo hairpin (<): gradually louder.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.EITHER,
    aliases=("crescendo hairpin", "hairpin"),
)

decrescendo = Mark(
    name="decrescendo",
    description="A decrescendo hairpin (>): gradually quieter.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.EITHER,
    aliases=("diminuendo", "decrescendo hairpin"),
)

crescendo_dal_niente = Mark(
    name="crescendo dal niente",
    description="A crescendo hairpin beginning from silence, drawn with a circled tip.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.EITHER,
    aliases=("niente hairpin (crescendo)",),
)

decrescendo_al_niente = Mark(
    name="decrescendo al niente",
    description="A decrescendo hairpin ending in silence, drawn with a circled tip.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.EITHER,
    aliases=("diminuendo al niente", "niente hairpin (decrescendo)"),
)

cresc = Mark(
    name="cresc.",
    description="Textual crescendo ('cresc.'), often extended with a dashed line.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.EITHER,
    aliases=("crescendo (text)",),
)

decresc = Mark(
    name="decresc.",
    description="Textual decrescendo ('decresc.' or 'dim.'), often extended with a dashed line.",
    kind=MarkType.DYNAMIC,
    attachment_mode=AttachmentMode.EITHER,
    aliases=("dim.", "diminuendo (text)", "decrescendo (text)"),
)


# =============================================================================
# ORNAMENTS
# =============================================================================

# --- trills -------------------------------------------------------------------

trill = Mark(
    name="trill",
    description="A trill (tr): rapid alternation with the note above. May be extended with a wavy line.",
    kind=MarkType.ORNAMENT,
    attachment_mode=AttachmentMode.EITHER,
    aliases=("tr", "shake (trill)"),
)

wavy_line = Mark(
    name="wavy line",
    description="A wavy extension line without a trill sign, used to prolong a trill or indicate vibrato.",
    kind=MarkType.ORNAMENT,
    attachment_mode=AttachmentMode.SPAN,
    aliases=("trill extension", "trill line"),
)

shake = Mark(
    name="shake",
    description="A shake: a short trill-like ornament (MusicXML shake).",
    kind=MarkType.ORNAMENT,
    attachment_mode=AttachmentMode.SINGLE,
)

# --- turns --------------------------------------------------------------------

turn = Mark(
    name="turn",
    description="A turn: the note above, the main note, the note below, and the main note again.",
    kind=MarkType.ORNAMENT,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("gruppetto",),
)

inverted_turn = Mark(
    name="inverted turn",
    description="An inverted turn (the turn sign with a vertical stroke): below, main, above, main.",
    kind=MarkType.ORNAMENT,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("reverse turn",),
)

delayed_turn = Mark(
    name="delayed turn",
    description="A turn placed between two notes, performed at the end of the first note's value.",
    kind=MarkType.ORNAMENT,
    attachment_mode=AttachmentMode.SINGLE,
)

delayed_inverted_turn = Mark(
    name="delayed inverted turn",
    description="An inverted turn placed between two notes, performed at the end of the first note's value.",
    kind=MarkType.ORNAMENT,
    attachment_mode=AttachmentMode.SINGLE,
)

vertical_turn = Mark(
    name="vertical turn",
    description="A turn sign rotated ninety degrees, indicating an upward turn.",
    kind=MarkType.ORNAMENT,
    attachment_mode=AttachmentMode.SINGLE,
)

inverted_vertical_turn = Mark(
    name="inverted vertical turn",
    description="A vertical turn sign inverted, indicating a downward turn.",
    kind=MarkType.ORNAMENT,
    attachment_mode=AttachmentMode.SINGLE,
)

# --- mordents and pralls ------------------------------------------------------

mordent = Mark(
    name="mordent",
    description="A mordent (short squiggle with a vertical stroke): rapid alternation with the note below.",
    kind=MarkType.ORNAMENT,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("lower mordent",),
)

inverted_mordent = Mark(
    name="inverted mordent",
    description="An inverted mordent (short squiggle, no stroke): rapid alternation with the note above.",
    kind=MarkType.ORNAMENT,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("upper mordent", "prall", "pralltriller", "Schneller"),
)

prallprall = Mark(
    name="prallprall",
    description="An extended prall: a longer squiggle indicating a longer short trill (LilyPond prallprall).",
    kind=MarkType.ORNAMENT,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("extended prall", "double prall"),
)

prall_mordent = Mark(
    name="prall mordent",
    description="A prall combined with a mordent: extended squiggle with a vertical stroke.",
    kind=MarkType.ORNAMENT,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("prallmordent",),
)

up_prall = Mark(
    name="up prall",
    description="A prall preceded by an upward approach from below (LilyPond upprall).",
    kind=MarkType.ORNAMENT,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("upprall",),
)

down_prall = Mark(
    name="down prall",
    description="A prall preceded by a downward approach from above (LilyPond downprall).",
    kind=MarkType.ORNAMENT,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("downprall",),
)

up_mordent = Mark(
    name="up mordent",
    description="A mordent preceded by an upward approach from below (LilyPond upmordent).",
    kind=MarkType.ORNAMENT,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("upmordent",),
)

down_mordent = Mark(
    name="down mordent",
    description="A mordent preceded by a downward approach from above (LilyPond downmordent).",
    kind=MarkType.ORNAMENT,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("downmordent",),
)

prall_down = Mark(
    name="prall down",
    description="A prall ending with a downward hook (LilyPond pralldown).",
    kind=MarkType.ORNAMENT,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("pralldown",),
)

prall_up = Mark(
    name="prall up",
    description="A prall ending with an upward hook (LilyPond prallup).",
    kind=MarkType.ORNAMENT,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("prallup",),
)

line_prall = Mark(
    name="line prall",
    description="A prall preceded by a straight line (LilyPond lineprall).",
    kind=MarkType.ORNAMENT,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("lineprall",),
)

# --- other ornaments ----------------------------------------------------------

schleifer = Mark(
    name="Schleifer",
    description="A Schleifer (slide ornament): two grace notes ascending stepwise into the main note.",
    kind=MarkType.ORNAMENT,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("slide (ornament)",),
)

haydn_ornament = Mark(
    name="Haydn ornament",
    description="The Haydn ornament: a sign used by Haydn, roughly equivalent to an inverted turn.",
    kind=MarkType.ORNAMENT,
    attachment_mode=AttachmentMode.SINGLE,
)

tremolo = Mark(
    name="tremolo",
    description="Tremolo strokes: rapid repetition of one note, or rapid alternation between two notes.",
    kind=MarkType.ORNAMENT,
    attachment_mode=AttachmentMode.EITHER,
    aliases=("trem.",),
)

buzz_roll = Mark(
    name="buzz roll",
    description="A buzz roll (z through the stem): a multiple-bounce roll on a drum.",
    kind=MarkType.ORNAMENT,
    attachment_mode=AttachmentMode.EITHER,
    aliases=("buzz", "press roll", "z"),
)

arpeggio = Mark(
    name="arpeggio",
    description="An arpeggio line: the chord is rolled from the bottom up.",
    kind=MarkType.ORNAMENT,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("arpeggiate", "rolled chord"),
)

arpeggio_up = Mark(
    name="arpeggio up",
    description="An arpeggio line with an upward arrowhead: the chord is rolled from the bottom up.",
    kind=MarkType.ORNAMENT,
    attachment_mode=AttachmentMode.SINGLE,
)

arpeggio_down = Mark(
    name="arpeggio down",
    description="An arpeggio line with a downward arrowhead: the chord is rolled from the top down.",
    kind=MarkType.ORNAMENT,
    attachment_mode=AttachmentMode.SINGLE,
)

non_arpeggio = Mark(
    name="non-arpeggio",
    description="A square bracket beside a chord: the chord is explicitly not to be rolled.",
    kind=MarkType.ORNAMENT,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("arpeggio bracket", "non-arpeggiate"),
)

arpeggio_parenthesis = Mark(
    name="arpeggio parenthesis",
    description="A parenthesis-style arpeggio line beside a chord (LilyPond arpeggioParenthesis).",
    kind=MarkType.ORNAMENT,
    attachment_mode=AttachmentMode.SINGLE,
)


# =============================================================================
# SLURS, TIES, AND PHRASING
# =============================================================================

slur = Mark(
    name="slur",
    description="A slur: the notes under it are played legato.",
    kind=MarkType.PHRASING,
    attachment_mode=AttachmentMode.SPAN,
    aliases=("legato slur",),
    binds=True,
)

phrase_mark = Mark(
    name="phrase mark",
    description="A phrasing slur: a longer arc indicating a musical phrase, drawn above ordinary slurs.",
    kind=MarkType.PHRASING,
    attachment_mode=AttachmentMode.SPAN,
    aliases=("phrasing slur",),
)

tie = Mark(
    name="tie",
    description="A tie: two notes of the same pitch are joined into one sustained duration.",
    kind=MarkType.PHRASING,
    attachment_mode=AttachmentMode.SPAN,
    binds=True,
)

laissez_vibrer = Mark(
    name="laissez vibrer",
    description="A laissez vibrer tie (l.v.): a tie leading nowhere, meaning let the note ring.",
    kind=MarkType.PHRASING,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("l.v.", "let ring", "let vibrate"),
)

repeat_tie = Mark(
    name="repeat tie",
    description="A tie arriving from nowhere, used on the first note after a repeat barline.",
    kind=MarkType.PHRASING,
    attachment_mode=AttachmentMode.SINGLE,
)

glissando = Mark(
    name="glissando",
    description="A glissando line between two notes: slide through the intervening pitches.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SPAN,
    aliases=("gliss.",),
)

portamento = Mark(
    name="portamento",
    description="A portamento line between two notes: a continuous slide in pitch.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SPAN,
    aliases=("port.", "slide"),
)


# =============================================================================
# FERMATAS
# =============================================================================

fermata = Mark(
    name="fermata",
    description="A fermata: the note, chord, or rest is held beyond its written value.",
    kind=MarkType.PHRASING,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("hold", "pause"),
)

short_fermata = Mark(
    name="short fermata",
    description="A short (angled) fermata: a brief hold.",
    kind=MarkType.PHRASING,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("angled fermata",),
)

long_fermata = Mark(
    name="long fermata",
    description="A long (square) fermata: an extended hold.",
    kind=MarkType.PHRASING,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("square fermata",),
)

very_short_fermata = Mark(
    name="very short fermata",
    description="A very short (double-angled) fermata.",
    kind=MarkType.PHRASING,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("double-angled fermata",),
)

very_long_fermata = Mark(
    name="very long fermata",
    description="A very long (double-square) fermata.",
    kind=MarkType.PHRASING,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("double-square fermata",),
)

henze_short_fermata = Mark(
    name="Henze short fermata",
    description="Henze's short fermata, drawn as a half curve.",
    kind=MarkType.PHRASING,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("half-curve fermata",),
)

henze_long_fermata = Mark(
    name="Henze long fermata",
    description="Henze's long fermata, drawn with two dots.",
    kind=MarkType.PHRASING,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("double-dot fermata",),
)

curlew = Mark(
    name="curlew",
    description="Britten's curlew sign: hold until the next cue, independent of the other parts.",
    kind=MarkType.PHRASING,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("curlew fermata",),
)


# =============================================================================
# BREATH MARKS AND CAESURAS
# =============================================================================

breath_mark = Mark(
    name="breath mark",
    description="A breath mark (comma): take a breath, or a brief lift, before the next note.",
    kind=MarkType.BREATH,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("comma", "luftpause"),
)

tick_breath_mark = Mark(
    name="tick breath mark",
    description="A breath mark drawn as a short tick.",
    kind=MarkType.BREATH,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("tick",),
)

upbow_breath_mark = Mark(
    name="upbow breath mark",
    description="A breath mark drawn as an up-bow sign, used in some vocal and string editions.",
    kind=MarkType.BREATH,
    attachment_mode=AttachmentMode.SINGLE,
)

salzedo_breath_mark = Mark(
    name="Salzedo breath mark",
    description="The Salzedo breath mark used in harp notation.",
    kind=MarkType.BREATH,
    attachment_mode=AttachmentMode.SINGLE,
)

caesura = Mark(
    name="caesura",
    description="A caesura (//): a brief silence or break in the musical flow.",
    kind=MarkType.BREATH,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("railroad tracks", "grand pause"),
)

thick_caesura = Mark(
    name="thick caesura",
    description="A caesura drawn with thick strokes.",
    kind=MarkType.BREATH,
    attachment_mode=AttachmentMode.SINGLE,
)

short_caesura = Mark(
    name="short caesura",
    description="A caesura drawn with short strokes.",
    kind=MarkType.BREATH,
    attachment_mode=AttachmentMode.SINGLE,
)

curved_caesura = Mark(
    name="curved caesura",
    description="A caesura drawn with curved strokes.",
    kind=MarkType.BREATH,
    attachment_mode=AttachmentMode.SINGLE,
)

single_caesura = Mark(
    name="single caesura",
    description="A caesura drawn as a single stroke.",
    kind=MarkType.BREATH,
    attachment_mode=AttachmentMode.SINGLE,
)


# =============================================================================
# BOWING
# =============================================================================

up_bow = Mark(
    name="up bow",
    description="An up-bow sign (V): the bow moves from tip to frog.",
    kind=MarkType.BOWING,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("upbow",),
)

down_bow = Mark(
    name="down bow",
    description="A down-bow sign: the bow moves from frog to tip.",
    kind=MarkType.BOWING,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("downbow",),
)

arco = Mark(
    name="arco",
    description="arco: resume playing with the bow (cancels pizzicato).",
    kind=MarkType.BOWING,
    attachment_mode=AttachmentMode.EITHER,
)

col_legno = Mark(
    name="col legno",
    description="col legno: play with the wood of the bow.",
    kind=MarkType.BOWING,
    attachment_mode=AttachmentMode.EITHER,
    aliases=("col legno battuto",),
)

col_legno_tratto = Mark(
    name="col legno tratto",
    description="col legno tratto: draw the wood of the bow across the string.",
    kind=MarkType.BOWING,
    attachment_mode=AttachmentMode.EITHER,
)

sul_ponticello = Mark(
    name="sul ponticello",
    description="sul ponticello: bow near the bridge for a glassy, overtone-rich sound.",
    kind=MarkType.BOWING,
    attachment_mode=AttachmentMode.EITHER,
    aliases=("sul pont.", "am Steg"),
)

sul_tasto = Mark(
    name="sul tasto",
    description="sul tasto: bow over the fingerboard for a soft, flute-like sound.",
    kind=MarkType.BOWING,
    attachment_mode=AttachmentMode.EITHER,
    aliases=("flautando", "sur la touche", "am Griffbrett"),
)

martele = Mark(
    name="martelé",
    description="martelé: a hammered, heavily accented on-the-string bow stroke.",
    kind=MarkType.BOWING,
    attachment_mode=AttachmentMode.EITHER,
    aliases=("martellato (bowing)",),
)

ricochet = Mark(
    name="ricochet",
    description="ricochet: the bow is thrown on the string and allowed to bounce for several notes.",
    kind=MarkType.BOWING,
    attachment_mode=AttachmentMode.EITHER,
    aliases=("jeté",),
)


# =============================================================================
# TECHNIQUE
# =============================================================================

# --- strings ------------------------------------------------------------------

pizzicato = Mark(
    name="pizzicato",
    description="pizz.: pluck the string with a finger instead of bowing.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.EITHER,
    aliases=("pizz.",),
)

snap_pizzicato = Mark(
    name="snap pizzicato",
    description="Snap (Bartók) pizzicato: pull the string away and let it snap back against the fingerboard.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("Bartók pizzicato", "Bartók pizz."),
)

harmonic = Mark(
    name="harmonic",
    description="A natural harmonic sign (o): touch the string lightly at a node.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("natural harmonic", "flageolet"),
)

artificial_harmonic = Mark(
    name="artificial harmonic",
    description="An artificial harmonic: a stopped note with a lightly touched node, notated with a diamond.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
)

open_string = Mark(
    name="open string",
    description="An open-string sign (o): play the string unstopped.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
)

stopped = Mark(
    name="stopped",
    description="A stopped sign (+): hand-stopped horn, left-hand pizzicato, or closed hi-hat.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("closed", "left-hand pizzicato"),
)

thumb_position = Mark(
    name="thumb position",
    description="A thumb-position sign for cello and bass.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("thumb",),
)

con_sordino = Mark(
    name="con sordino",
    description="con sord.: play with the mute.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.EITHER,
    aliases=("con sord.", "with mute", "mute on"),
)

senza_sordino = Mark(
    name="senza sordino",
    description="senza sord.: remove the mute.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.EITHER,
    aliases=("senza sord.", "without mute", "mute off"),
)

ordinario = Mark(
    name="ordinario",
    description="ord.: return to the ordinary manner of playing (cancels sul pont., col legno, etc.).",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.EITHER,
    aliases=("ord.", "naturale", "nat.", "normale"),
)

# --- fretted strings ----------------------------------------------------------

hammer_on = Mark(
    name="hammer-on",
    description="A hammer-on (H): sound the next higher note by tapping a finger onto the string.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SPAN,
)

pull_off = Mark(
    name="pull-off",
    description="A pull-off (P): sound the next lower note by pulling a finger off the string.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SPAN,
)

bend = Mark(
    name="bend",
    description="A string bend: raise the pitch by pushing the string sideways.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.EITHER,
)

pre_bend = Mark(
    name="pre-bend",
    description="A pre-bend: bend the string before sounding the note.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
)

bend_release = Mark(
    name="bend release",
    description="A release: return a bent string to its unbent pitch.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.EITHER,
    aliases=("release",),
)

bend_after = Mark(
    name="bend after",
    description="A fall or doit-style bend after the note (LilyPond bendAfter).",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
)

tap = Mark(
    name="tap",
    description="A tap (T): sound the note by tapping the string against the fret with the picking hand.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
)

golpe = Mark(
    name="golpe",
    description="A golpe: tap the guitar body with a finger (flamenco).",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
)

fingernails = Mark(
    name="fingernails",
    description="A fingernails sign: pluck with the fingernails (harp).",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.EITHER,
)

damp = Mark(
    name="damp",
    description="A damp sign: stop the string(s) from ringing (harp).",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("étouffez",),
)

damp_all = Mark(
    name="damp all",
    description="A damp-all sign: stop all strings from ringing (harp).",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
)

# --- winds and brass ----------------------------------------------------------

double_tongue = Mark(
    name="double tongue",
    description="A double-tongue sign: articulate with alternating T-K syllables.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.EITHER,
    aliases=("double tonguing",),
)

triple_tongue = Mark(
    name="triple tongue",
    description="A triple-tongue sign: articulate with T-K-T (or T-T-K) syllables.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.EITHER,
    aliases=("triple tonguing",),
)

flutter_tongue = Mark(
    name="flutter tongue",
    description="flz.: roll the tongue (or growl) while sustaining the note.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.EITHER,
    aliases=("flz.", "Flatterzunge", "flutter tonguing"),
)

open_ = Mark(
    name="open",
    description="An open sign (o): unmuted brass, open hand on horn, or open hi-hat.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("open hi-hat", "unmuted"),
)

half_open = Mark(
    name="half-open",
    description="A half-open sign: a half-open hi-hat.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("half-open hi-hat", "halfopen"),
)

half_muted = Mark(
    name="half-muted",
    description="A half-muted sign (ø): brass played with the hand partly covering the bell.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
)

harmon_mute_closed = Mark(
    name="harmon mute closed",
    description="A Harmon mute with the stem in and the bell closed.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
)

harmon_mute_half = Mark(
    name="harmon mute half",
    description="A Harmon mute half open.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
)

harmon_mute_open = Mark(
    name="harmon mute open",
    description="A Harmon mute with the bell open.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
)

brass_bend = Mark(
    name="brass bend",
    description="A brass bend: lower the pitch with the lip and return.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
)

flip = Mark(
    name="flip",
    description="A flip: a quick upward lip slur before dropping to the next note (jazz brass).",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
)

smear = Mark(
    name="smear",
    description="A smear: a slow, slurred lip bend into the note (jazz brass).",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
)

hole_open = Mark(
    name="hole open",
    description="An open-hole sign for woodwind fingering diagrams.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
)

hole_half = Mark(
    name="hole half",
    description="A half-covered-hole sign for woodwind fingering diagrams.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
)

hole_closed = Mark(
    name="hole closed",
    description="A closed-hole sign for woodwind fingering diagrams.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
)

# --- percussion ---------------------------------------------------------------

choke = Mark(
    name="choke",
    description="Choke: grab the cymbal (or damp the instrument) right after the stroke.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("choked",),
)

with_sticks = Mark(
    name="with sticks",
    description="Play with drumsticks (the drumstick pictogram or the word).",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.EITHER,
    aliases=("sticks",),
)

with_brushes = Mark(
    name="with brushes",
    description="Play with brushes (the brush pictogram or the word).",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.EITHER,
    aliases=("brushes",),
)

with_hands = Mark(
    name="with hands",
    description="Play with the hands.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.EITHER,
    aliases=("hands", "with the hands"),
)

hard_mallets = Mark(
    name="hard mallets",
    description="Play with hard mallets (the filled-circle pictogram).",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.EITHER,
    aliases=("hard mallet", "hard sticks"),
)

soft_mallets = Mark(
    name="soft mallets",
    description="Play with soft mallets (the open-circle pictogram).",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.EITHER,
    aliases=("soft mallet", "soft sticks"),
)

snares_on = Mark(
    name="snares on",
    description="Snares on: engage the snares of a snare drum.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.EITHER,
    aliases=("with snares",),
)

snares_off = Mark(
    name="snares off",
    description="Snares off: release the snares of a snare drum.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.EITHER,
    aliases=("without snares", "senza corde"),
)

# --- keyboard pedaling --------------------------------------------------------

sustain_pedal = Mark(
    name="sustain pedal",
    description="Sustain (damper) pedal: Ped. ... *, or a bracket line with notches for changes.",
    kind=MarkType.PHRASING,
    attachment_mode=AttachmentMode.SPAN,
    aliases=("Ped.", "damper pedal", "pedal"),
)

sostenuto_pedal = Mark(
    name="sostenuto pedal",
    description="Sostenuto (middle) pedal: sustains only the notes held when it is depressed.",
    kind=MarkType.PHRASING,
    attachment_mode=AttachmentMode.SPAN,
    aliases=("Sost. Ped.", "middle pedal"),
)

una_corda = Mark(
    name="una corda",
    description="una corda: depress the soft (left) pedal; released with tre corde.",
    kind=MarkType.PHRASING,
    attachment_mode=AttachmentMode.SPAN,
    aliases=("u.c.", "soft pedal"),
)

tre_corde = Mark(
    name="tre corde",
    description="tre corde: release the soft pedal.",
    kind=MarkType.PHRASING,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("t.c.",),
)

# --- organ pedalboard ---------------------------------------------------------

heel = Mark(
    name="heel",
    description="A heel sign: play the pedal note with the heel.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
)

toe = Mark(
    name="toe",
    description="A toe sign: play the pedal note with the toe.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
)

left_heel = Mark(
    name="left heel",
    description="A left-heel sign for organ pedaling.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("lheel",),
)

right_heel = Mark(
    name="right heel",
    description="A right-heel sign for organ pedaling.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("rheel",),
)

left_toe = Mark(
    name="left toe",
    description="A left-toe sign for organ pedaling.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("ltoe",),
)

right_toe = Mark(
    name="right toe",
    description="A right-toe sign for organ pedaling.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("rtoe",),
)

# --- handbells ----------------------------------------------------------------

belltree = Mark(
    name="belltree",
    description="A belltree sign: play a set of bells arranged as a tree.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
)

handbell_damp = Mark(
    name="handbell damp",
    description="A handbell damp sign: stop the bell from ringing.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
)

echo = Mark(
    name="echo",
    description="A handbell echo: ring, then touch the rim to the table repeatedly.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
)

gyro = Mark(
    name="gyro",
    description="A handbell gyro: ring and rotate the bell in a circle.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
)

hand_martellato = Mark(
    name="hand martellato",
    description="A hand martellato: strike the bell against the padded table while holding it.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
)

mallet_lift = Mark(
    name="mallet lift",
    description="A mallet lift: strike the bell with a mallet while lifting it from the table.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
)

mallet_table = Mark(
    name="mallet table",
    description="A mallet table: strike the bell with a mallet while it rests on the table.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
)

martellato = Mark(
    name="martellato",
    description="A martellato: strike the bell against the padded table.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
)

martellato_lift = Mark(
    name="martellato lift",
    description="A martellato lift: strike the bell against the table and lift it to ring.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
)

muted_martellato = Mark(
    name="muted martellato",
    description="A muted martellato: strike the bell against the table and keep it there.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
)

pluck_lift = Mark(
    name="pluck lift",
    description="A pluck lift: pluck the clapper while lifting the bell from the table.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
)

swing = Mark(
    name="swing",
    description="A handbell swing: ring the bell and swing it in an arc.",
    kind=MarkType.TECHNIQUE,
    attachment_mode=AttachmentMode.SINGLE,
)


# =============================================================================
# FINGERING
# =============================================================================

fingering_0 = Mark(
    name="fingering 0",
    description="Fingering 0: open string.",
    kind=MarkType.FINGERING,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("0",),
)

fingering_1 = Mark(
    name="fingering 1",
    description="Fingering 1: thumb (keyboard) or index finger (strings).",
    kind=MarkType.FINGERING,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("1",),
)

fingering_2 = Mark(
    name="fingering 2",
    description="Fingering 2: index finger (keyboard) or middle finger (strings).",
    kind=MarkType.FINGERING,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("2",),
)

fingering_3 = Mark(
    name="fingering 3",
    description="Fingering 3: middle finger (keyboard) or ring finger (strings).",
    kind=MarkType.FINGERING,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("3",),
)

fingering_4 = Mark(
    name="fingering 4",
    description="Fingering 4: ring finger (keyboard) or little finger (strings).",
    kind=MarkType.FINGERING,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("4",),
)

fingering_5 = Mark(
    name="fingering 5",
    description="Fingering 5: little finger (keyboard).",
    kind=MarkType.FINGERING,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("5",),
)

# --- sticking -----------------------------------------------------------------

stick_right = Mark(
    name="stick right",
    description="Sticking R: play this stroke with the right hand.",
    kind=MarkType.FINGERING,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("R", "right hand"),
)

stick_left = Mark(
    name="stick left",
    description="Sticking L: play this stroke with the left hand.",
    kind=MarkType.FINGERING,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("L", "left hand"),
)

# --- plucking-hand fingering (guitar, harp) -----------------------------------

pluck_p = Mark(
    name="pluck p",
    description="Right-hand fingering p: thumb (pulgar).",
    kind=MarkType.FINGERING,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("pulgar",),
)

pluck_i = Mark(
    name="pluck i",
    description="Right-hand fingering i: index finger (índice).",
    kind=MarkType.FINGERING,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("índice",),
)

pluck_m = Mark(
    name="pluck m",
    description="Right-hand fingering m: middle finger (medio).",
    kind=MarkType.FINGERING,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("medio",),
)

pluck_a = Mark(
    name="pluck a",
    description="Right-hand fingering a: ring finger (anular).",
    kind=MarkType.FINGERING,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("anular",),
)

pluck_c = Mark(
    name="pluck c",
    description="Right-hand fingering c: little finger (chico); also written e or x.",
    kind=MarkType.FINGERING,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("chico", "e", "x"),
)

# --- string numbers -----------------------------------------------------------

string_1 = Mark(
    name="string 1",
    description="String number 1 (circled): play on the highest string.",
    kind=MarkType.FINGERING,
    attachment_mode=AttachmentMode.EITHER,
)

string_2 = Mark(
    name="string 2",
    description="String number 2 (circled).",
    kind=MarkType.FINGERING,
    attachment_mode=AttachmentMode.EITHER,
)

string_3 = Mark(
    name="string 3",
    description="String number 3 (circled).",
    kind=MarkType.FINGERING,
    attachment_mode=AttachmentMode.EITHER,
)

string_4 = Mark(
    name="string 4",
    description="String number 4 (circled).",
    kind=MarkType.FINGERING,
    attachment_mode=AttachmentMode.EITHER,
)

string_5 = Mark(
    name="string 5",
    description="String number 5 (circled).",
    kind=MarkType.FINGERING,
    attachment_mode=AttachmentMode.EITHER,
)

string_6 = Mark(
    name="string 6",
    description="String number 6 (circled).",
    kind=MarkType.FINGERING,
    attachment_mode=AttachmentMode.EITHER,
)

sul_g = Mark(
    name="sul G",
    description="sul G: play the passage on the G string (violin); by extension, any named string.",
    kind=MarkType.FINGERING,
    attachment_mode=AttachmentMode.EITHER,
)


# =============================================================================
# FICTA
# =============================================================================

ficta_sharp = Mark(
    name="ficta sharp",
    description="A musica ficta sharp: an editorial sharp placed above the note.",
    kind=MarkType.FICTA,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("editorial sharp", "suggested sharp"),
)

ficta_flat = Mark(
    name="ficta flat",
    description="A musica ficta flat: an editorial flat placed above the note.",
    kind=MarkType.FICTA,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("editorial flat", "suggested flat"),
)

ficta_natural = Mark(
    name="ficta natural",
    description="A musica ficta natural: an editorial natural placed above the note.",
    kind=MarkType.FICTA,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("editorial natural", "suggested natural"),
)

ficta_double_sharp = Mark(
    name="ficta double sharp",
    description="A musica ficta double sharp: an editorial double sharp placed above the note.",
    kind=MarkType.FICTA,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("editorial double sharp",),
)

ficta_double_flat = Mark(
    name="ficta double flat",
    description="A musica ficta double flat: an editorial double flat placed above the note.",
    kind=MarkType.FICTA,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("editorial double flat",),
)


# =============================================================================
# EXPRESSION
# =============================================================================
# Words that shape delivery. Any of them may carry a dashed extension over a
# stretch (LilyPond's text spanner, MusicXML <words> with <dashes>), so every
# one is EITHER. Tempo words are TempoTerms, not marks, and are further down.

dolce = Mark(
    name="dolce",
    description="Dolce: sweetly, softly.",
    kind=MarkType.EXPRESSION,
    attachment_mode=AttachmentMode.EITHER,
)

cantabile = Mark(
    name="cantabile",
    description="Cantabile: in a singing style.",
    kind=MarkType.EXPRESSION,
    attachment_mode=AttachmentMode.EITHER,
)

legato = Mark(
    name="legato",
    description="Legato: smoothly, the notes connected; the word, where a score writes it instead of a slur.",
    kind=MarkType.EXPRESSION,
    attachment_mode=AttachmentMode.EITHER,
)

simile = Mark(
    name="simile",
    description="Simile: continue in the same manner (articulation, pedaling, pattern) as just written.",
    kind=MarkType.EXPRESSION,
    attachment_mode=AttachmentMode.EITHER,
    aliases=("sim.",),
)

sotto_voce = Mark(
    name="sotto voce",
    description="Sotto voce: in an undertone, subdued.",
    kind=MarkType.EXPRESSION,
    attachment_mode=AttachmentMode.EITHER,
)

agitato = Mark(
    name="agitato",
    description="Agitato: agitated, restless.",
    kind=MarkType.EXPRESSION,
    attachment_mode=AttachmentMode.EITHER,
)

tranquillo = Mark(
    name="tranquillo",
    description="Tranquillo: calm, tranquil.",
    kind=MarkType.EXPRESSION,
    attachment_mode=AttachmentMode.EITHER,
)

pesante = Mark(
    name="pesante",
    description="Pesante: heavy, weighty.",
    kind=MarkType.EXPRESSION,
    attachment_mode=AttachmentMode.EITHER,
)

leggiero = Mark(
    name="leggiero",
    description="Leggiero: light, nimble.",
    kind=MarkType.EXPRESSION,
    attachment_mode=AttachmentMode.EITHER,
    aliases=("leggero",),
)

grazioso = Mark(
    name="grazioso",
    description="Grazioso: graceful.",
    kind=MarkType.EXPRESSION,
    attachment_mode=AttachmentMode.EITHER,
)

maestoso = Mark(
    name="maestoso",
    description="Maestoso: majestic, stately.",
    kind=MarkType.EXPRESSION,
    attachment_mode=AttachmentMode.EITHER,
)

# =============================================================================
# OTHER
# =============================================================================

# --- octave transposition -----------------------------------------------------

ottava_alta = Mark(
    name="ottava alta",
    description="8va: play an octave higher than written.",
    kind=MarkType.TRANSPOSITION,
    attachment_mode=AttachmentMode.SPAN,
    aliases=("8va", "ottava"),
)

ottava_bassa = Mark(
    name="ottava bassa",
    description="8vb: play an octave lower than written.",
    kind=MarkType.TRANSPOSITION,
    attachment_mode=AttachmentMode.SPAN,
    aliases=("8vb", "8va bassa"),
)

quindicesima_alta = Mark(
    name="quindicesima alta",
    description="15ma: play two octaves higher than written.",
    kind=MarkType.TRANSPOSITION,
    attachment_mode=AttachmentMode.SPAN,
    aliases=("15ma",),
)

quindicesima_bassa = Mark(
    name="quindicesima bassa",
    description="15mb: play two octaves lower than written.",
    kind=MarkType.TRANSPOSITION,
    attachment_mode=AttachmentMode.SPAN,
    aliases=("15mb",),
)

# --- navigation ---------------------------------------------------------------

segno = Mark(
    name="segno",
    description="A segno sign: the target of a dal segno instruction.",
    kind=MarkType.NAVIGATION,
    attachment_mode=AttachmentMode.SINGLE,
)

coda = Mark(
    name="coda",
    description="A coda sign: marks the coda; the words at the jump are `to_coda`.",
    kind=MarkType.NAVIGATION,
    attachment_mode=AttachmentMode.SINGLE,
)

varcoda = Mark(
    name="varcoda",
    description="A variant (square) coda sign.",
    kind=MarkType.NAVIGATION,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("variant coda",),
)

fine = Mark(
    name="fine",
    description="Fine: the end, where a da capo or dal segno finishes. The jump itself is control flow, which a future module owns; the word here is what is printed.",
    kind=MarkType.NAVIGATION,
    attachment_mode=AttachmentMode.SINGLE,
)

da_capo = Mark(
    name="da capo",
    description="D.C.: go back to the beginning. The jump itself is control flow, which a future module owns; the word here is what is printed.",
    kind=MarkType.NAVIGATION,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("D.C.",),
)

dal_segno = Mark(
    name="dal segno",
    description="D.S.: go back to the segno. The jump itself is control flow, which a future module owns; the word here is what is printed.",
    kind=MarkType.NAVIGATION,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("D.S.",),
)

da_capo_al_fine = Mark(
    name="da capo al fine",
    description="D.C. al Fine: go back to the beginning and play to the fine. The jump itself is control flow, which a future module owns; the word here is what is printed.",
    kind=MarkType.NAVIGATION,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("D.C. al Fine",),
)

dal_segno_al_fine = Mark(
    name="dal segno al fine",
    description="D.S. al Fine: go back to the segno and play to the fine. The jump itself is control flow, which a future module owns; the word here is what is printed.",
    kind=MarkType.NAVIGATION,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("D.S. al Fine",),
)

da_capo_al_coda = Mark(
    name="da capo al coda",
    description="D.C. al Coda: go back to the beginning and play to the coda jump. The jump itself is control flow, which a future module owns; the word here is what is printed.",
    kind=MarkType.NAVIGATION,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("D.C. al Coda",),
)

dal_segno_al_coda = Mark(
    name="dal segno al coda",
    description="D.S. al Coda: go back to the segno and play to the coda jump. The jump itself is control flow, which a future module owns; the word here is what is printed.",
    kind=MarkType.NAVIGATION,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("D.S. al Coda",),
)

to_coda = Mark(
    name="to coda",
    description="To Coda: on the last time through, jump to the coda from here. The jump itself is control flow, which a future module owns; the word here is what is printed.",
    kind=MarkType.NAVIGATION,
    attachment_mode=AttachmentMode.SINGLE,
)

# --- miscellaneous ------------------------------------------------------------

signum_congruentiae = Mark(
    name="signum congruentiae",
    description="A signum congruentiae: a sign in early music marking a point of coincidence between voices.",
    kind=MarkType.OTHER,
    attachment_mode=AttachmentMode.SINGLE,
)

eyeglasses = Mark(
    name="eyeglasses",
    description="An eyeglasses sign: watch the conductor.",
    kind=MarkType.OTHER,
    attachment_mode=AttachmentMode.SINGLE,
)

# --- instructions to the players ------------------------------------------------
# Each states a condition in force until the next word, so they sit at a
# point; a fill is marked at a point or drawn over a stretch.

solo = Mark(
    name="solo",
    description="Solo: one player, or the featured line, alone, until countermanded.",
    kind=MarkType.OTHER,
    attachment_mode=AttachmentMode.SINGLE,
)

tutti = Mark(
    name="tutti",
    description="Tutti: everyone; cancels solo or divisi.",
    kind=MarkType.OTHER,
    attachment_mode=AttachmentMode.SINGLE,
)

divisi = Mark(
    name="divisi",
    description="Divisi: a section divides to cover the parts written.",
    kind=MarkType.OTHER,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("div.",),
)

unisono = Mark(
    name="unisono",
    description="Unisono: a divided section rejoins in unison.",
    kind=MarkType.OTHER,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("unis.",),
)

a_2 = Mark(
    name="a 2",
    description="A 2: both players of a pair play the one line.",
    kind=MarkType.OTHER,
    attachment_mode=AttachmentMode.SINGLE,
    aliases=("a due",),
)

fill = Mark(
    name="fill",
    description="Fill: the player (a drummer, in a chart) improvises over the marked stretch.",
    kind=MarkType.OTHER,
    attachment_mode=AttachmentMode.EITHER,
)

# =============================================================================
# TEMPO TERMS
# =============================================================================
# Words a TempoEvent may carry (`TempoEvent(term=allegro)`), beside a ratio or
# alone. The beats-per-minute ranges in the descriptions are the conventional
# modern ones (the commonly reproduced table, as on Wikipedia's "Tempo" page),
# and mean beats of whatever value the meter's beat is written as; they are
# description only, a term has no range field. Gradual changes (rit., accel.)
# are not tempo terms and are not here.

# --- rate words, slowest to fastest ------------------------------------------

larghissimo = TempoTerm(
    name="larghissimo",
    description="Very, very slow: about 24 beats per minute or fewer.",
)

grave = TempoTerm(
    name="grave",
    description="Very slow and solemn: about 25 to 45 beats per minute.",
)

largo = TempoTerm(
    name="largo",
    description="Slow and broad: about 40 to 60 beats per minute.",
)

lento = TempoTerm(
    name="lento",
    description="Slow: about 45 to 60 beats per minute.",
)

larghetto = TempoTerm(
    name="larghetto",
    description="Rather slow and broad: about 60 to 66 beats per minute.",
)

adagio = TempoTerm(
    name="adagio",
    description="Slow and expressive: about 66 to 76 beats per minute.",
)

adagietto = TempoTerm(
    name="adagietto",
    description="Slightly faster than adagio: about 70 to 80 beats per minute.",
)

andante = TempoTerm(
    name="andante",
    description="At a walking pace: about 76 to 108 beats per minute.",
)

andantino = TempoTerm(
    name="andantino",
    description="Slightly faster than andante (though sometimes read as slightly slower): about 80 to 108 beats per minute.",
)

andante_moderato = TempoTerm(
    name="andante moderato",
    description="Between andante and moderato: about 92 to 112 beats per minute.",
)

moderato = TempoTerm(
    name="moderato",
    description="At a moderate speed: about 108 to 120 beats per minute.",
)

allegretto = TempoTerm(
    name="allegretto",
    description="Moderately fast: about 112 to 120 beats per minute.",
)

allegro_moderato = TempoTerm(
    name="allegro moderato",
    description="Close to, but not quite, allegro: about 116 to 120 beats per minute.",
)

allegro = TempoTerm(
    name="allegro",
    description="Fast and bright: about 120 to 156 beats per minute.",
)

allegro_vivace = TempoTerm(
    name="allegro vivace",
    description="Faster and livelier than allegro: about 124 to 156 beats per minute.",
    aliases=("molto allegro",),
)

vivace = TempoTerm(
    name="vivace",
    description="Lively and fast: about 156 to 176 beats per minute.",
)

vivacissimo = TempoTerm(
    name="vivacissimo",
    description="Very fast and lively: about 172 to 176 beats per minute.",
)

allegrissimo = TempoTerm(
    name="allegrissimo",
    description="Very fast: about 172 to 176 beats per minute.",
)

presto = TempoTerm(
    name="presto",
    description="Very, very fast: about 168 to 200 beats per minute.",
)

prestissimo = TempoTerm(
    name="prestissimo",
    description="Faster than presto: about 200 beats per minute or more.",
)

# --- restorers and free tempo: words with no range of their own --------------

a_tempo = TempoTerm(
    name="a tempo",
    description="Back to the tempo in force before the last departure from it (a ritardando, an accelerando, a rubato passage).",
)

tempo_primo = TempoTerm(
    name="tempo primo",
    description="Back to the first tempo of the piece or movement.",
    aliases=("Tempo I",),
)

listesso_tempo = TempoTerm(
    name="l'istesso tempo",
    description="The same tempo: the beat keeps its speed across a change of meter or of note value.",
    aliases=("lo stesso tempo",),
)

rubato = TempoTerm(
    name="rubato",
    description="Freely: the beat is stretched and pressed at the performer's discretion, the overall pace kept.",
    aliases=("tempo rubato",),
)

ad_libitum = TempoTerm(
    name="ad libitum",
    description="At will: the tempo of the passage is left to the performer.",
    aliases=("ad lib.",),
)

# =============================================================================
# BAR LINES
# =============================================================================
# A BarLineShape lists its components in time order (LilyPond's `\bar`
# string order). The MusicXML bar-style / LilyPond glyph each one renders as
# is noted beside it; repeat dots are MusicXML's <repeat> element.

single_bar = BarLineShape(BarLineComponent.THIN)  # regular / "|"
double_bar = BarLineShape(BarLineComponent.THIN, BarLineComponent.THIN)  # light-light / "||"
final_bar = BarLineShape(BarLineComponent.THIN, BarLineComponent.THICK)  # light-heavy / "|."
reverse_final_bar = BarLineShape(
    BarLineComponent.THICK, BarLineComponent.THIN
)  # heavy-light / ".|"
heavy_bar = BarLineShape(BarLineComponent.THICK)  # heavy / "."
double_heavy_bar = BarLineShape(
    BarLineComponent.THICK, BarLineComponent.THICK
)  # heavy-heavy / ".."
dashed_bar = BarLineShape(BarLineComponent.DASHED)  # dashed / "!"
dotted_bar = BarLineShape(BarLineComponent.DOTTED)  # dotted / ";"
short_bar = BarLineShape(BarLineComponent.SHORT)  # short / ","
tick_bar = BarLineShape(BarLineComponent.TICK)  # tick / "'"
invisible_bar = BarLineShape()  # none / ""
start_repeat = BarLineShape(
    BarLineComponent.THICK, BarLineComponent.THIN, BarLineComponent.DOTS
)  # heavy-light + forward repeat / ".|:"
end_repeat = BarLineShape(
    BarLineComponent.DOTS, BarLineComponent.THIN, BarLineComponent.THICK
)  # light-heavy + backward repeat / ":|."
double_repeat = BarLineShape(
    BarLineComponent.DOTS,
    BarLineComponent.THIN,
    BarLineComponent.THICK,
    BarLineComponent.THIN,
    BarLineComponent.DOTS,
)  # ":|.|:"
