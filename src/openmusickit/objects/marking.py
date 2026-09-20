from abc import ABC, abstractmethod
from dataclasses import dataclass

from openmusickit.objects.omk_object import OmkObject, Spanner
from openmusickit.values.scoring.mark import AttachmentMode, Mark


class Marked(ABC):
    """Mixin for objects that carry a `Mark`: the `isinstance` target for
    "is this a mark in the score", whatever it is attached to."""

    __slots__ = ()

    @property
    @abstractmethod
    def mark(self) -> Mark: ...


@dataclass(kw_only=True, slots=True)
class Marking(OmkObject, Marked):
    """A mark placed on a single event (a staccato dot on this note, a
    fermata on that rest), attached with a MARKS edge.

    A mark whose `attachment_mode` is SPAN belongs on a `MarkSpanner`:

    >>> from openmusickit.systems.wsmn.scoring.symbols import staccato, slur
    >>> Marking(mark=staccato)
    Marking(mark=Mark(name='staccato', ...))
    >>> Marking(mark=slur)
    Traceback (most recent call last):
    ...
    ValueError: 'slur' is a span mark; place it with a MarkSpanner.
    """

    mark: Mark

    def __post_init__(self):
        if self.mark.attachment_mode is AttachmentMode.SPAN:
            raise ValueError(f"{self.mark.name!r} is a span mark; place it with a MarkSpanner.")

    def __repr__(self):
        return f"{type(self).__name__}(mark=Mark(name={self.mark.name!r}, ...))"


@dataclass(kw_only=True, slots=True)
class MarkSpanner(Spanner, Marked):
    """A mark that extends over a run of events (a slur, a hairpin, an
    octave line), attached with STARTS_AT and ENDS_AT edges.

    The spanner *is* the mark in the score, so a passage under both a slur
    and a hairpin has two MarkSpanners. Whether the events under it are
    bound into one articulation is the mark's business (`mark.binds`).

    A mark whose `attachment_mode` is SINGLE belongs on a `Marking`:

    >>> from openmusickit.systems.wsmn.scoring.symbols import slur, staccato
    >>> MarkSpanner(mark=slur)
    MarkSpanner(mark=Mark(name='slur', ...))
    >>> MarkSpanner(mark=staccato)
    Traceback (most recent call last):
    ...
    ValueError: 'staccato' is a single-event mark; place it with a Marking.
    """

    mark: Mark

    def __post_init__(self):
        if self.mark.attachment_mode is AttachmentMode.SINGLE:
            raise ValueError(f"{self.mark.name!r} is a single-event mark; place it with a Marking.")

    def __repr__(self):
        return f"{type(self).__name__}(mark=Mark(name={self.mark.name!r}, ...))"
