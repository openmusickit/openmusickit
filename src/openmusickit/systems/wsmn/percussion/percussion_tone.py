"""An unpitched sound as Western notation distinguishes it."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum

from openmusickit.systems.wsmn.percussion.wsmn import WSMN_PERCUSSION
from openmusickit.values.tone.tone import TonalSystem
from openmusickit.values.tone.unpitched_tone import UnpitchedTone


class RelativePitch(IntEnum):
    """Which member of a family of like instruments a sound is on:
    the low conga, the high bongo, the second of four toms.
    Ordered low to high; `None` on a `PercussionTone` means the question
    does not arise (a snare drum) or is left open.

    Five members name every pair and trio of hand drums, blocks and bells,
    the four rack toms, and five temple blocks.
    A larger family (ten toms) is split across Parts;
    where a whole setup sits on a staff is an output map's business.

    >>> RelativePitch.LOW < RelativePitch.HIGH_MID < RelativePitch.HIGH
    True
    >>> str(RelativePitch.LOW_MID), f"{RelativePitch.HIGH}"
    ('low-mid', 'high')
    """

    LOW = 1
    LOW_MID = 2
    MID = 3
    HIGH_MID = 4
    HIGH = 5

    def __str__(self) -> str:
        return self.name.lower().replace("_", "-")


class Stroke(StrEnum):
    """How the instrument is struck.

    The values are the display forms.
    A stroke changes which sound one hit makes;
    what changes how a sound or a passage is delivered
    (an accent, a roll, a choke, a change of beater) is a `Mark`,
    and a flam or a drag is a grace note.
    Anything not here ("hit it with a feather duster") is a plain
    `PercussionTone()` with a custom technique Mark.

    >>> Stroke.RIM_SHOT, str(Stroke.RIM_SHOT)
    (<Stroke.RIM_SHOT: 'rim shot'>, 'rim shot')
    """

    # drums, with sticks or mallets
    CENTER = "center"  # centre of the head
    EDGE = "edge"  # near the rim; also the edge of a cymbal or gong
    RIM = "rim"  # the rim alone (rim click)
    RIM_SHOT = "rim shot"  # head and rim at once
    CROSS_STICK = "cross stick"  # stick laid across the head, striking the rim (side stick)
    SHELL = "shell"  # the shell of the drum
    DEAD = "dead"  # pressed stroke, no rebound
    # hand drums
    OPEN = "open"  # open tone, flat hand at the edge; also an open hi-hat, triangle or cuica
    SLAP = "slap"  # slap tone
    BASS = "bass"  # bass tone, palm in the centre
    MUTE = "mute"  # muted or muffled
    PALM = "palm"  # flat palm, a muffled thump
    FINGER = "finger"  # a finger stroke or flick
    FIST = "fist"  # closed fist
    HEEL = "heel"  # heel of the hand, of a heel-toe rocking stroke
    TOE = "toe"  # fingertips, of a heel-toe rocking stroke
    # hi-hat and cymbals
    CLOSED = "closed"  # hi-hat closed
    HALF_OPEN = "half open"  # hi-hat half open
    PEDAL = "pedal"  # hi-hat by the pedal alone
    FOOT_SPLASH = "foot splash"  # hi-hat pedal opened and released
    BELL = "bell"  # the bell of a cymbal
    CRASH = "crash"  # a crash stroke on any cymbal
    # small instruments
    SCRAPE = "scrape"  # guiro, cabasa, the edge of a gong
    SHAKE = "shake"  # one shake of a shaker, maracas or tambourine
    THUMB_ROLL = "thumb roll"  # tambourine friction roll
    # body
    CLAP = "clap"
    SNAP = "snap"
    STOMP = "stomp"


@dataclass(frozen=True, slots=True)
class PercussionTone(UnpitchedTone):
    """An unpitched sound: a relative pitch and a stroke, each optional.

    A PercussionTone abstracts over instruments as a pitch does:
    `PercussionTone(relative_pitch=HIGH, stroke=OPEN)` is the same value
    on congas, bongos or a djembe pair, and the Part says which.
    `PercussionTone()` is a plain hit on whatever the Part is;
    a triangle part or a concert bass drum part is a line of these,
    with a stroke only where it differs.
    The palettes in `symbols` collect the combinations that are
    meaningful for a class of instrument.

    A relative pitch is not a pitch: `pitch` is None, as for any
    unpitched tone, and f-strings give the readable form.

    >>> tone = PercussionTone(relative_pitch=RelativePitch.HIGH, stroke=Stroke.OPEN)
    >>> tone
    PercussionTone(relative_pitch=RelativePitch.HIGH, stroke=Stroke.OPEN)
    >>> f"{tone}", str(PercussionTone(stroke=Stroke.RIM_SHOT)), str(PercussionTone())
    ('high open', 'rim shot', 'hit')
    >>> tone.pitch is None, tone.tonal_system.name
    (True, 'WSMN percussion')
    >>> PercussionTone() == PercussionTone(), PercussionTone() in {tone, PercussionTone()}
    (True, True)
    """

    relative_pitch: RelativePitch | None = None
    stroke: Stroke | None = None

    @property
    def tonal_system(self) -> TonalSystem:
        return WSMN_PERCUSSION

    def __str__(self) -> str:
        parts = [str(part) for part in (self.relative_pitch, self.stroke) if part is not None]
        return " ".join(parts) or "hit"

    def __repr__(self) -> str:
        fields = []
        if self.relative_pitch is not None:
            fields.append(f"relative_pitch=RelativePitch.{self.relative_pitch.name}")
        if self.stroke is not None:
            fields.append(f"stroke=Stroke.{self.stroke.name}")
        return f"{type(self).__name__}({', '.join(fields)})"
