from dataclasses import dataclass
from enum import StrEnum, auto


class MarkType(StrEnum):
    """The type of a Mark.

    Text in a score is a Mark too.
    Words that shape how the material is delivered (dolce, cantabile, legato) are EXPRESSION;
    the words that direct movement through the score (D.C. al Fine, To Coda)
    are NAVIGATION, beside the signs;
    a boxed rehearsal letter or number is REHEARSAL,
    whose `name` is the label, made for the score;
    instructions to the players (solo, tutti, divisi) are OTHER.
    A word the vocabulary lacks is a Mark made for the score,
    as `TempoTerm` allows for tempo words.
    """

    ARTICULATION = auto()
    DYNAMIC = auto()
    ORNAMENT = auto()
    TECHNIQUE = auto()
    FINGERING = auto()
    BOWING = auto()
    BREATH = auto()
    FICTA = auto()
    PHRASING = (
        auto()
    )  # slurs, ties, pedaling, fermatas: marks that shape how events connect and are sustained
    NAVIGATION = (
        auto()
    )  # segno, coda, D.C., D.S., fine: signs and words that direct movement through the score
    TRANSPOSITION = auto()  # 8va, 8vb, 15ma, and similar octave lines
    EXPRESSION = (
        auto()
    )  # dolce, cantabile, legato, simile: words that shape how the material is delivered
    REHEARSAL = (
        auto()
    )  # a boxed rehearsal letter or number; the label is the mark's name, made per score
    OTHER = auto()


class AttachmentMode(StrEnum):
    """The attachment mode of a Mark.

    SINGLE: A mark that is attached to a single note or event.
    SPAN: A mark that is attached to a span of notes or events.
    EITHER: A mark that can be attached to either a single event or a span.

    This is not enforced at the OmkGraph level,
    but may be used in validation or rendering to determine how a mark should be applied,
    or whether/why a rendering may fail or produce unexpected results.

    """

    SINGLE = auto()  # A mark that is attached to a single note or event.
    SPAN = auto()  # A mark that is attached to a span of notes or events.
    EITHER = (
        auto()
    )  # A mark that can be attached to either a single note or event, or a span of notes or events.


@dataclass(frozen=True, slots=True)
class Mark:
    """A mark as it appears in a notation system's vocabulary
    (a staccato dot, a slur, a fermata, `mf`).
    The thing placed in a score is a `Marking` or a `MarkSpanner` holding one of these.

    Most of a Mark is descriptive.
    The few attributes code acts on are added one at a time,
    named for what the mark means musically rather than for the code that reads them:
    `kind` and `attachment_mode` classify it,
    and `binds` says that the events under a span mark are one articulation
    (one bow, one breath, one syllable), as under a slur or a tie.
    A mark that binds cannot begin a new lyric syllable except on its first note.
    """

    name: str
    description: str | None = None
    kind: MarkType | None = None
    attachment_mode: AttachmentMode | None = None
    aliases: tuple[str, ...] = ()
    binds: bool = False

    def __repr__(self) -> str:
        """The constructor call that builds this mark back,
        with the fields at their defaults left out,
        so a mark made for one score prints as it was written.

        >>> Mark(name="dolce")
        Mark(name='dolce')
        >>> Mark(name="A", kind=MarkType.OTHER, attachment_mode=AttachmentMode.SINGLE)
        Mark(name='A', kind=MarkType.OTHER, attachment_mode=AttachmentMode.SINGLE)
        >>> from openmusickit.systems.wsmn.scoring.symbols import staccato
        >>> staccato
        Mark(name='staccato', description='A staccato dot: the note is played detached and shortened.', kind=MarkType.ARTICULATION, attachment_mode=AttachmentMode.SINGLE)
        """
        parts = [f"name={self.name!r}"]
        if self.description is not None:
            parts.append(f"description={self.description!r}")
        if self.kind is not None:
            parts.append(f"kind=MarkType.{self.kind.name}")
        if self.attachment_mode is not None:
            parts.append(f"attachment_mode=AttachmentMode.{self.attachment_mode.name}")
        if self.aliases:
            parts.append(f"aliases={self.aliases!r}")
        if self.binds:
            parts.append("binds=True")
        return f"{type(self).__name__}({', '.join(parts)})"
