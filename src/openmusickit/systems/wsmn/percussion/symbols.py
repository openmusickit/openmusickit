"""Ready-made percussion tones, and the palettes of tones meaningful for a
class of instrument.

```
from openmusickit.systems.wsmn.percussion.symbols import *
```

A tone abstracts over instruments: `high_open` is the same value on congas,
bongos or a djembe pair, and the `PercussionPart` says which. A palette is a
`ToneCollection`, ordered low to high and then by stroke, with `hit` (a plain
`PercussionTone()`) in every one; it is a curated vocabulary a `PercussionPart`
may carry, not a type, and core never checks a tone against it. The names in
brackets in each palette's gloss are the instruments a Part named that way
would use it for.

Examples
--------

>>> hit
PercussionTone()
>>> high_open, f"{high_open}"
(PercussionTone(relative_pitch=RelativePitch.HIGH, stroke=Stroke.OPEN), 'high open')
>>> open_hat is open_hand      # one tone, two names, for two kinds of instrument
True
>>> hit in hand_drums, high_slap in hand_drums, rim_shot in hand_drums
(True, True, False)
>>> hi_hats.name, len(hi_hats)
('hi-hat', 8)
"""

from openmusickit.systems.wsmn.percussion.percussion_tone import (
    PercussionTone,
    RelativePitch,
    Stroke,
)
from openmusickit.values.tone.tone_collection import ToneCollection

# =============================================================================
# TONES
# =============================================================================

hit = PercussionTone()

# --- relative pitch alone -----------------------------------------------------

low = PercussionTone(relative_pitch=RelativePitch.LOW)
low_mid = PercussionTone(relative_pitch=RelativePitch.LOW_MID)
mid = PercussionTone(relative_pitch=RelativePitch.MID)
high_mid = PercussionTone(relative_pitch=RelativePitch.HIGH_MID)
high = PercussionTone(relative_pitch=RelativePitch.HIGH)

# --- strokes alone ------------------------------------------------------------

center = PercussionTone(stroke=Stroke.CENTER)
edge = PercussionTone(stroke=Stroke.EDGE)
rim = PercussionTone(stroke=Stroke.RIM)
rim_shot = PercussionTone(stroke=Stroke.RIM_SHOT)
cross_stick = PercussionTone(stroke=Stroke.CROSS_STICK)
shell = PercussionTone(stroke=Stroke.SHELL)
dead = PercussionTone(stroke=Stroke.DEAD)
open_hat = PercussionTone(stroke=Stroke.OPEN)  # an open hi-hat (or triangle, or cuica)
open_hand = open_hat  # an open tone on a hand drum: the same tone, named for its context
slap = PercussionTone(stroke=Stroke.SLAP)
bass = PercussionTone(stroke=Stroke.BASS)
mute = PercussionTone(stroke=Stroke.MUTE)
palm = PercussionTone(stroke=Stroke.PALM)
finger = PercussionTone(stroke=Stroke.FINGER)
fist = PercussionTone(stroke=Stroke.FIST)
heel = PercussionTone(stroke=Stroke.HEEL)
toe = PercussionTone(stroke=Stroke.TOE)
closed = PercussionTone(stroke=Stroke.CLOSED)
half_open = PercussionTone(stroke=Stroke.HALF_OPEN)
pedal = PercussionTone(stroke=Stroke.PEDAL)
foot_splash = PercussionTone(stroke=Stroke.FOOT_SPLASH)
bell = PercussionTone(stroke=Stroke.BELL)
crash = PercussionTone(stroke=Stroke.CRASH)
scrape = PercussionTone(stroke=Stroke.SCRAPE)
shake = PercussionTone(stroke=Stroke.SHAKE)
thumb_roll = PercussionTone(stroke=Stroke.THUMB_ROLL)
clap = PercussionTone(stroke=Stroke.CLAP)
snap = PercussionTone(stroke=Stroke.SNAP)
stomp = PercussionTone(stroke=Stroke.STOMP)

# --- the hand-drum pairs used most --------------------------------------------

low_open = PercussionTone(relative_pitch=RelativePitch.LOW, stroke=Stroke.OPEN)
high_open = PercussionTone(relative_pitch=RelativePitch.HIGH, stroke=Stroke.OPEN)
low_slap = PercussionTone(relative_pitch=RelativePitch.LOW, stroke=Stroke.SLAP)
high_slap = PercussionTone(relative_pitch=RelativePitch.HIGH, stroke=Stroke.SLAP)
low_bass = PercussionTone(relative_pitch=RelativePitch.LOW, stroke=Stroke.BASS)
high_bass = PercussionTone(relative_pitch=RelativePitch.HIGH, stroke=Stroke.BASS)
low_mute = PercussionTone(relative_pitch=RelativePitch.LOW, stroke=Stroke.MUTE)
high_mute = PercussionTone(relative_pitch=RelativePitch.HIGH, stroke=Stroke.MUTE)


# =============================================================================
# PALETTES
# =============================================================================


def _palette(
    name: str,
    strokes: tuple[Stroke, ...] = (),
    pitches: tuple[RelativePitch, ...] = (),
) -> ToneCollection:
    """`hit`, then every relative pitch (or none) with every stroke (or none),
    low to high and then by stroke."""
    tones = [hit]
    for pitch in (None, *pitches):
        for stroke in (None, *strokes):
            tone = PercussionTone(relative_pitch=pitch, stroke=stroke)
            if tone != hit:
                tones.append(tone)
    return ToneCollection(tones, name=name)


_PAIR = (RelativePitch.LOW, RelativePitch.HIGH)
_TRIO = (RelativePitch.LOW, RelativePitch.MID, RelativePitch.HIGH)
_FIVE = tuple(RelativePitch)

hand_drums = _palette(  # congas, bongos, djembe, cajon, frame drums
    "hand drum",
    (
        Stroke.OPEN,
        Stroke.SLAP,
        Stroke.BASS,
        Stroke.MUTE,
        Stroke.PALM,
        Stroke.FINGER,
        Stroke.FIST,
        Stroke.HEEL,
        Stroke.TOE,
    ),
    _TRIO,
)
snare_drums = _palette(  # snare, field drum, tenor drum
    "snare drum",
    (
        Stroke.RIM_SHOT,
        Stroke.CROSS_STICK,
        Stroke.RIM,
        Stroke.CENTER,
        Stroke.EDGE,
        Stroke.SHELL,
        Stroke.DEAD,
    ),
)
bass_drums = _palette(  # kick, concert bass drum; a pair for a double kick
    "bass drum", (Stroke.CENTER, Stroke.EDGE, Stroke.MUTE), _PAIR
)
toms = _palette(  # rack and floor toms
    "tom", (Stroke.RIM_SHOT, Stroke.RIM, Stroke.CENTER, Stroke.EDGE, Stroke.DEAD), _FIVE
)
hi_hats = _palette(
    "hi-hat",
    (
        Stroke.CLOSED,
        Stroke.OPEN,
        Stroke.HALF_OPEN,
        Stroke.PEDAL,
        Stroke.FOOT_SPLASH,
        Stroke.BELL,
        Stroke.EDGE,
    ),
)
cymbals = _palette(  # crash, ride, china, splash, suspended; bowed is the `arco` mark
    "cymbal", (Stroke.BELL, Stroke.EDGE, Stroke.CRASH, Stroke.DEAD)
)
gongs = _palette("gong", (Stroke.CENTER, Stroke.EDGE, Stroke.SCRAPE, Stroke.MUTE))  # tam-tam, gong
bells = _palette("bell", (Stroke.OPEN, Stroke.MUTE, Stroke.EDGE), _PAIR)  # cowbell, agogo
blocks = _palette("block", (), _FIVE)  # wood block, temple blocks, claves, castanets, log drum
shakers = _palette("shaker", (Stroke.SHAKE, Stroke.SCRAPE, Stroke.MUTE))  # shaker, maracas, cabasa
tambourines = _palette("tambourine", (Stroke.SHAKE, Stroke.THUMB_ROLL, Stroke.MUTE, Stroke.FIST))
triangles = _palette("triangle", (Stroke.OPEN, Stroke.MUTE, Stroke.SCRAPE))
scrapers = _palette("scraper", (Stroke.SCRAPE,))  # guiro, ratchet, washboard
cuicas = _palette("cuica", (Stroke.OPEN, Stroke.MUTE))
body = _palette("body", (Stroke.CLAP, Stroke.SNAP, Stroke.STOMP, Stroke.SLAP))  # body percussion
single_hit = _palette("single hit")  # whip, anvil, brake drum, vibraslap, whistle, wind machine
