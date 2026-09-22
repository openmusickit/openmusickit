import warnings
from collections.abc import Callable
from dataclasses import dataclass, field

from openmusickit.errors import OmkWarning
from openmusickit.objects.omk_object import SequentialEvent, TonalObject
from openmusickit.values.time.duration import Duration, Measurable, TemporalRatio, ZeroDuration
from openmusickit.values.tone.modal_context import ModalContext
from openmusickit.values.tone.tone import Tone


@dataclass(kw_only=True, slots=True)
class ContextEvent(SequentialEvent):
    """An instantaneous event that changes the interpretation
    of subsequent material.

    A ContextEvent always has zero duration; it cannot be given one.

    >>> isinstance(ContextEvent().duration, ZeroDuration)
    True

    >>> ContextEvent(duration=None)
    Traceback (most recent call last):
    ...
    TypeError: ...
    """

    duration: Duration = field(default_factory=ZeroDuration, init=False, repr=False)


@dataclass(kw_only=True, slots=True)
class ModalContextEvent(ContextEvent, TonalObject):
    """Sets the modal context (in WSMN, the key or key signature) for the
    material that follows.

    `None` means undefined or undecided. For WSMN, "no key" is
    `symbols.NoKey` and a bare key signature is `Key.from_signature(...)`;
    the printed signature is reached through the Key
    (`event.modal_context.signature`), never through the event.
    """

    modal_context: ModalContext | None = None

    def transform_tones(self, operation: Callable[..., Tone], *args, **kwargs) -> None:
        """Replaces the modal context, in place, with `modal_context.transform(operation, ...)`.

        An event with no modal context is left as it is, with an `OmkWarning`
        that callers can catch or filter.

        Examples
        --------

        >>> from openmusickit.systems.wsmn.tonal.key import Key, KeySignature
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, M2, m3, P5, Major
        >>> from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector, TonalDirection

        A Key moves to a new tonic, keeping its mode:

        >>> event = ModalContextEvent(modal_context=Key.of(C, Major))
        >>> event.transform_tones(TonalVector.transpose, M2)
        >>> event.modal_context.name, event.modal_context.signature
        ('D Major', KeySignature(c=1, f=1))

        >>> event.transform_tones(TonalVector.transpose, P5, TonalDirection.DOWN)
        >>> event.modal_context.name
        'G Major'

        A bare key signature is transformed letter by letter:

        >>> event = ModalContextEvent(modal_context=Key.from_signature(KeySignature()))
        >>> event.transform_tones(TonalVector.transpose, m3)
        >>> event.modal_context.signature, event.modal_context.tonic
        (KeySignature(e=-1, a=-1, b=-1), None)

        An empty event warns and is unchanged:

        >>> import warnings
        >>> event = ModalContextEvent()
        >>> with warnings.catch_warnings(record=True) as caught:
        ...     warnings.simplefilter("always")
        ...     event.transform_tones(TonalVector.transpose, M2)
        >>> event.modal_context is None, str(caught[0].message)
        (True, 'You are attempting to transform an event with no modal context. Nothing will happen.')
        """
        if self.modal_context is None:
            warnings.warn(
                "You are attempting to transform an event with no modal context. Nothing will happen.",
                OmkWarning,
                stacklevel=2,
            )
            return

        self.modal_context = self.modal_context.transform(operation, *args, **kwargs)


@dataclass(kw_only=True, slots=True)
class TemporalContextEvent(ContextEvent):
    """Sets how the time of the material that follows is read:
    the meter it is organized by (`MeterEvent`),
    or the rate at which its durations pass (`TempoEvent`).

    A temporal context belongs to the line it is in, as a division does,
    and governs what follows it there until the next one of its kind.
    A meter and a tempo are independent
    (a tempo change is not a meter change, and neither implies the other),
    so each is its own event,
    and a passage that opens with both has two nodes in its NEXT chain.
    Like every ContextEvent it has zero duration,
    so timing along the line passes straight through it:

    >>> from openmusickit.graph.graph import GraphMeta, OmkGraph
    >>> from openmusickit.objects.note_event import NoteEvent
    >>> from openmusickit.systems.wsmn.temporal.symbols import four_four, quarter
    >>> from openmusickit.systems.wsmn.tonal.symbols import C, D
    >>> from openmusickit.values.time.clock_time import Tempo
    >>> meter, tempo = MeterEvent(meter=four_four), TempoEvent(tempo=Tempo(120, quarter))
    >>> c, d = NoteEvent(tones={C}, duration=quarter), NoteEvent(tones={D}, duration=quarter)
    >>> graph = OmkGraph(GraphMeta())
    >>> graph.add_line([meter, tempo, c, d])
    >>> graph.relative_onset(meter, d)
    MetricalDuration(1, 4)

    Whether a line with no context of its own is read by the context of a
    line it is pinned or grouped with, or by an app's default,
    is not decided here: absence of a context is absence of information.
    """


@dataclass(kw_only=True, slots=True)
class MeterEvent(TemporalContextEvent):
    """Sets the meter (in WSMN, the time signature) for the material that follows.

    A meter is a `Measurable`: a length of musical time that recurs,
    and against which the material is organized.
    In WSMN it is a `TimeSignature`, one bar with the numbers as printed;
    a bare `TemporalUnit` (three quarters), a `CompoundTemporalUnit`
    for an additive cycle (the vibhags of a tala, the strokes of a gong cycle),
    or any other Measurable of a system will do.
    Music whose time is not measured (chant) has no meter;
    `None` means undefined or undecided.

    A meter does not place divisions:
    `DivisionEvent`s do, wherever the author puts them,
    and a renderer that derives the missing ones from the meter
    warns where an explicit one disagrees.

    >>> from openmusickit.systems.wsmn.temporal.symbols import four_four, two_two, quarter
    >>> from openmusickit.values.time.duration import TemporalUnit
    >>> MeterEvent(meter=four_four)
    MeterEvent(meter=TimeSignature([TemporalUnit(4, MetricalDuration(1, 4))], ('4', '4')))
    >>> MeterEvent(meter=TemporalUnit(3, quarter)).meter.rational_length
    Fraction(3, 4)
    >>> MeterEvent().meter is None
    True

    Events compare by their meters, and Measurables compare by length,
    so two events whose time signatures have the same length are equal:

    >>> MeterEvent(meter=four_four) == MeterEvent(meter=two_two)
    True
    """

    meter: Measurable | None = None


@dataclass(kw_only=True, slots=True)
class TempoEvent(TemporalContextEvent):
    """Sets the tempo for the material that follows:
    the rate at which its durations pass, as a `TemporalRatio`.

    The ratio's nominal side is in the units of the line's own system;
    its contextual side is what those units are measured against from here on.
    That is clock time for a metronome marking, which is a `Tempo`;
    the units of the material before for a metric modulation
    (or a proportion, in mensural notation),
    which says how the new note values relate to the old
    and nothing about clock time;
    or the units of another system, when one line is paced against another
    (one puntum of chant to one quarter note).
    `None` means undefined or undecided.

    >>> from openmusickit.systems.wsmn.temporal.symbols import dotted_quarter, quarter
    >>> from openmusickit.values.time.clock_time import Tempo
    >>> TempoEvent(tempo=Tempo(120, quarter))
    TempoEvent(tempo=Tempo(120, MetricalDuration(1, 4)))
    >>> TempoEvent().tempo is None
    True

    A metric modulation written "quarter = dotted quarter"
    (the new dotted quarter lasts as long as the quarter before it)
    has the new value on the nominal side and the old on the contextual:

    >>> modulation = TempoEvent(tempo=TemporalRatio(dotted_quarter, quarter))
    >>> modulation
    TempoEvent(tempo=TemporalRatio(MetricalDuration(1, 4, dots=1), MetricalDuration(1, 4)))
    >>> modulation.tempo.multiplier
    Fraction(2, 3)
    """

    tempo: TemporalRatio | None = None
