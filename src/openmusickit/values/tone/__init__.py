"""The `tone` package provides the abstract base classes for pitch and interval systems:
`Tone`, `Interval`, their string representations, `SilentTone`, `UnpitchedTone`,
`ToneCollection`, and `ModalContext`.
Concrete systems (for example `systems.wsmn.tonal.TonalVector`) subclass these."""

from . import interval, modal_context, silent_tone, tone, tone_collection, unpitched_tone

__all__ = [
    "interval",
    "modal_context",
    "silent_tone",
    "tone",
    "tone_collection",
    "unpitched_tone",
]
