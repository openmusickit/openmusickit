"""The `tone` package provides the abstract base classes for pitch and interval systems:
`Tone`, `Interval`, their string representations, `SilentTone`, `UnpitchedTone`,
`ToneCollection`, and `ModalContext`.
Concrete systems (for example `systems.wsmn.tonal.TonalVector`) subclass these."""

from . import interval, modal_context, silent_tone, tone, tone_collection, unpitched_tone
from .interval import Interval, IntervalRepresentation
from .modal_context import ModalContext
from .silent_tone import SilentTone
from .tone import ANY_TONAL_SYSTEM, PitchRepresentation, TonalSystem, Tone
from .tone_collection import ToneCollection, apply_tone_operation
from .unpitched_tone import UnpitchedTone

__all__ = [
    "interval",
    "modal_context",
    "silent_tone",
    "tone",
    "tone_collection",
    "unpitched_tone",
    "ANY_TONAL_SYSTEM",
    "Interval",
    "IntervalRepresentation",
    "ModalContext",
    "PitchRepresentation",
    "SilentTone",
    "TonalSystem",
    "Tone",
    "ToneCollection",
    "UnpitchedTone",
    "apply_tone_operation",
]
