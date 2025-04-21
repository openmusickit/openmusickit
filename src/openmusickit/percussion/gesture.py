from collections import namedtuple

GestureVector = namedtuple("GestureVector", [
    "sharpness",    # [0–1] Time from silence to peak amplitude (impact clarity & speed)
    "decay",        # [0–1] Time from peak to sustain level (snappiness vs bloom)
    "sustain",      # [0–1] Duration of steady tone/body (core length of sound)
    "release",      # [0–1] Time from sustain level to silence (tail, fade-out, reverb)
    "brightness",   # [0–1] Perceptual treble energy (sparkle, edge, overtone strength)
    "noise",        # [0–1] Degree of noisiness, buzz, or inharmonicity
    "pitch",        # [0–1] Perceived pitch height (relative to instrument class)
    "wetness",      # [-1 to 1] Pitch bend during decay: down (-1), static (0), up (+1)
    "hollowness"    # [0–1] Resonant cavity quality: dull thud ←→ spacious/hollow ring
])