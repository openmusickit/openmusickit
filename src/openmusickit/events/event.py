from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, ClassVar

from openmusickit.data_types.tone.tone import Tone
from openmusickit.data_types.time.duration import Duration
from openmusickit.data_types.tone.tone_collection import ToneCollection
from openmusickit.utils.omk_object import OmkObject




@dataclass
class MusicalEvent(OmkObject):
    """A note, chord, gesture or other discrete musical event,
    actually written into a score or other representation of a piece of music; 
    the atomic unit of most types of music.

    Examples of a MusicalEvent:

     - A single note in a score.
     - A rest. (Use SilentTone as the `tonal_content`.)
     - A chord or cluster of notes played together by a single performer
       on a single intrument (such as on a piano),
       which share duration and articulation.
     - A bass note and its figures in a figured bass line.
     - A single unpitched rhythmic notation,
       such as would be found in a comping chart.
     - A durationless pitch in a melodic or harmonic sketch.
     - An unrealized idea for an event in a score sketch
       ("big horn blast here!") which does not yet have
       defined `tonal_content` or `duration`.
     - A movement, gesture, or other event which may appear in a score,
       and which is treated as a single event.
    
    A MusicalEvent does not need to be fully realized
    (that is, it can be "missing" `tonal_content` and/or `duration`).

    ## In graph-based score representations

    Standard articulations and other types of note annotations
    are not stored as part of the event, but are attached to it as separate nodes.

    Lyrics are not stored as part of the event,
    but are attached to it as separate nodes.

    Descriptions, sketch notes, non-standard instructions, extended techniques, images, 
    and other information which may or may not appear on a final score
    can be stored as `metadata`.

    For scores imported from another format,
    provenance information is stored in `metadata`.

    Generally, information which connects the `MusicalEvent` to other nodes
    (for example, "copied from" or "realizes")
    should not be stored in `metadata`, but should be connection edges.

    (In other words,
    any data about the event which *can* be represented as part of the graph,
    *should* be represented as part of the graph.)

    ## In sequence based score representations

    OMK provides a sequence-based score representation
    for simple musical examples and as an intermediate exchange format.

    Lyrics, articulations, annotations, and similar objects
    which would normally be additional nodes in a graph representation
    should be stored as meta-data on the event.
    
    """
    tonal_content: Tone | ToneCollection | None = None
    duration: Duration | None = None
    metadata: dict = dict()


    _transforms: ClassVar[dict[str, str]] = {}


    @classmethod
    def register_transform(
        cls,
        name: str,
        *,
        component: str,
    ) -> None:
        """Registers a transformation method on `tonal_content` or `duration`.
        
        Temporal transformations (such as scaling, diminution, augmentation) and
        tonal tranformations (such as transposition and inversion)
        can be registered against MusicalEvent.

        When called, these transformations replace the `tonal_content` or `duration`
        with the return value of the same call to the component.

        (For this reason, Tones and Durations in all tonal and temporal systems
        should be immutable values, and any transform methods
        should return new instances.)
        """
        if name in cls._transforms:
            raise ValueError(
                f"Transform {name!r} is already registered"
            )

        cls._transforms[name] = component

    def __getattr__(self, name: str) -> Callable[..., None]:
        try:
            component_name = self._transforms[name]
        except KeyError:
            raise AttributeError(
                f"{type(self).__name__!s} has no attribute {name!r}"
            ) from None

        def transform(*args, **kwargs) -> None:
            component = getattr(self, component_name)

            if component is None:
                raise ValueError(
                    f"Cannot apply {name!r}: "
                    f"{component_name!r} is unspecified"
                )

            component_method = getattr(component, name, None)

            if not callable(component_method):
                raise TypeError(
                    f"{type(component).__name__} does not support "
                    f"the {name!r} transformation"
                )

            transformed = component_method(*args, **kwargs)
            setattr(self, component_name, transformed)

        return transform