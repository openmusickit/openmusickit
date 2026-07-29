from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, ClassVar

from openmusickit.tone.tone import Tone
from openmusickit.time.duration import Duration
from openmusickit.harmony.tone_collection import ToneCollection
from openmusickit.utils.id import OmkId




@dataclass
class MusicalEvent:
    """A note, chord, gesture or other discreet musical event; 
    the atomic unit of most types of music.

    Examples of a MusicalEvent:

     - A single note in a score.
     - A chord or cluster of notes played together by a single performer
       on a single intrument (such as on a piano),
       which share duration and articulation.
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

    Standard articulations and other types of note annotations
    are not stored as part of the event, but are attached to it as separate nodes.

    Lyrics are not stored as part of the event,
    but are attached to it as separate nodes.

    Descriptions, sketch notes, non-standard instructions, extended techniques, images, 
    and other information which may or may not appear on a final score
    can be stored as `metadata`.

    For scores imported from another format,
    provenance information is stored in `metadata`.
    
    """
    tonal_content: Tone | ToneCollection | None = None
    duration: Duration | None = None
    metadata: dict = dict()
    __id: OmkId = field(default_factory = OmkId.new)

    _transforms: ClassVar[dict[str, str]] = {}

    @property
    def id(self):
        """The stable identity of the musical event, across sessions and storage."""
        return self.__id



    @classmethod
    def register_transform(
        cls,
        name: str,
        *,
        component: str,
    ) -> None:
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