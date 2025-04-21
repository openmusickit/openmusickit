import numpy as np
from pydantic import BaseModel, Field


class ArticulationVector(BaseModel):
    """Vector describing how a note should be played,
    defining it in terms of an array of specific attributes.
    ArticulationVector is used in Articulations, which can be added to a Note,
    and in PercussionTones, which define specific non-pitched percussion hits.
    
    Vector members
    --------------

    `attack_force`     # [-1, 1] Loudness, sharpness, or force of intitial impact
    `attack_time`      # [-1, 1] Time from silence to peak amplitude (impact clarity & speed)
    `decay_time`       # [-1, 1] Time from peak to sustain level (snappiness vs bloom)
    `sustain_time`     # [-1, 1] Duration of steady tone/body (core length of sound)
    `release_time`     # [-1, 1] Time from sustain level to silence (tail, fade-out, reverb)
    `cutoff_force`     # [-1, 1] Loudness or force of cutoff
    `brightness`       # [-1, 1] Perceptual treble energy (sparkle, edge, overtone strength)
    `noise`            # [-1, 1] Degree of noisiness, buzz, or inharmonicity
    `air`              # [-1, 1] Airiness, breathiness, or ethereality.
    `shimmer`          # [-1, 1] Vibrato, tremolo. 
    `inflection`       # [-1, 1] Perceived pitch height.
    `scoop`            # [-1, 1] Pitchbend during attack: down (-1), static (0), up (+1)
    `wetness`          # [-1, 1] Pitch bend during decay: down (-1), static (0), up (+1)
    `hollowness`       # [-1, 1] Resonant cavity quality: dull thud ←→ spacious/hollow ring
    
    For all values, zero (`0`) is considered normal or neutral.
    `-1` : as little as possible
    `1`: as much as possible 


    """
    attack_force: float = Field(0, ge=-1, le=1)
    attack_time: float = Field(0, ge=-1, le=1)
    decay_time: float = Field(0, ge=-1, le=1)
    sustain_time: float = Field(0, ge=-1, le=1)
    release_time: float = Field(0, ge=-1, le=1)
    cutoff_force: float = Field(0, ge=-1, le=1)
    brightness: float = Field(0, ge=-1, le=1)
    noise: float = Field(0, ge=-1, le=1)
    air: float = Field(0, ge=-1, le=1)
    shimmer: float = Field(0, ge=-1, le=1)
    inflection: float = Field(0, ge=-1, le=1)
    scoop: float = Field(0, ge=-1, le=1)
    wetness: float = Field(0, ge=-1, le=1)
    hollowness: float = Field(0, ge=-1, le=1)

    class Config:
        frozen = True

    def __iter__(self):
        yield self.attack_force
        yield self.attack_time
        yield self.decay_time
        yield self.sustain_time
        yield self.release_time
        yield self.cutoff_force
        yield self.brightness
        yield self.noise
        yield self.air
        yield self.shimmer
        yield self.inflection
        yield self.scoop
        yield self.wetness
        yield self.hollowness

    def to_array(self):
        return np.array(list(self))
    
    def __array__(self):
        return self.to_array()

