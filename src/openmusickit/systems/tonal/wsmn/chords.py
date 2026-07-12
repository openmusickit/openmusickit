from enum import Enum
from typing import Iterable
from openmusickit.harmony.tone_collection import ToneCollection, ToneSequence
from openmusickit.utils.number_names import ordinals
from .tonal_vector import TonalVector

class Quality(Enum):
    MAJ = "major"
    MIN = "minor"
    SUS = "suspended"
    POW = "open/power"
    AUG = "augmented"
    DIM = "diminished"
    DOM = "dominant"
    HDM = "half diminished"

class ChordType(ToneCollection):
    """Chord definition using TonalVectors as intervals from root (0,0).
    Include an octave designations if you want arpeggios and inversions
    to work as expected for extensions (9, 11, 13)"""

    def __init__(self, tones: Iterable[TonalVector],
                 name: str, bass: TonalVector=None, quality: Quality=None):
        
        tones = [tv.conditional_qualify_octave() for tv in tones]
        
        if TonalVector(0, 0, 0) not in tones:
            raise ValueError("Include `TonalVector(0,0)` as root of chord type.")

        super().__init__(tones, root=TonalVector(0,0), name=name)

        self.bass = bass or self.root
        self.quality = quality

    def arpegiate(self):
        s = self - set(self.bass)
        arp = [self.bass] + sorted(list(s))
        return ToneSequence(arp)
    
    # FIX naming
    def inversion(self, inv: int|TonalVector, name: str=None):
        
        if isinstance(inv, TonalVector):
            bass = inv
            try:
                name = name or (self.name + f" - {ordinals[inv]} inversion")
            except TypeError:
                name = None
        if isinstance(inv, int):
            tones = sorted(list(self))
            try:
                bass = tones[inv]
            except IndexError:
                raise IndexError(f"Max inversion is {len(self)-1}.")
        
            try:
                name = name or (self.name + f" / {bass.unqualify_octave().pitch.unicode}")
            except TypeError:
                name = None
            
        return ChordType(self, name, bass, self.quality)
    
    def __call__(self, tv: TonalVector):
        tones = [(t + tv) for t in self.tones]
        root = tv
        bass = self.bass + tv

        return Chord(root, tones, bass)
    
class Chord(ToneCollection):
    
    def __init__(self, root: TonalVector, tones: Iterable[TonalVector], 
                 bass: TonalVector=None, name:str=None):
        

        self.tones = set(tones)





    
        
