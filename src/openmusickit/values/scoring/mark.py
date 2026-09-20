from dataclasses import dataclass
from enum import StrEnum, auto


class MarkType(StrEnum):
    """The type of a Mark."""

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
    NAVIGATION = auto()  # segno, coda, and other signs that direct movement through the score
    TRANSPOSITION = auto()  # 8va, 8vb, 15ma, and similar octave lines
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
    """A mark as it appears in a notation system's vocabulary (a staccato dot,
    a slur, a fermata, `mf`). The thing placed in a score is a `Marking` or a
    `MarkSpanner` holding one of these.

    Most of a Mark is descriptive. The few attributes code acts on are added
    one at a time, named for what the mark means musically rather than for
    the code that reads them: `kind` and `attachment_mode` classify it, and
    `binds` says that the events under a span mark are one articulation
    (one bow, one breath, one syllable), as under a slur or a tie. A mark
    that binds cannot begin a new lyric syllable except on its first note.
    """

    name: str
    description: str | None = None
    kind: MarkType | None = None
    attachment_mode: AttachmentMode | None = None
    aliases: tuple[str, ...] = ()
    binds: bool = False
