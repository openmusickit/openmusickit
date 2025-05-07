from itertools import combinations
from typing import Iterable, List
from openmusickit.tone.tone import Tone

class ToneCollection(set):
    """An unordered collection of tones, with an optional root and optional name."""

    def __init__(self, tones: Iterable[Tone], root: Tone= None, name: str=None):
        super().__init__(tones)
        self.add(root)
        self.root = root
        self.name = name

    def combinations(self, k):
        return [ToneCollection(c) for c in combinations(self, k)]

class ToneSequence(list):
    """An ordered collection of non-repeated tones,
    with an optional name and optional reversed form and name.
    
    DO NOT include the octave tone. This will break things.
    If you need a ToneSequence that specifies an octave tone,
    subclass this and re-implement `__getitem__` and probably `chords`."""

    def __init__(self, tones: List[Tone], rev: List[Tone]=None, name: str=None, rev_name=None):
        super().__init__(tones)
        self.name = name
        
        if rev_name is None:
            if name:
                rev_name = name + "-reversed"
            else:
                rev_name = None

        if rev:
            self.reversed = ToneSequence(rev, name=rev_name)
        else:
            self.reversed = ToneSequence(list(reversed(tones)), name=rev_name)
        self.reversed.reversed = self
    
    def combinations(self, k):
        return [ToneCollection(c) for c in combinations(self, k)]
    
    def all_combinations(self, k):
        s = set(self).union(set(self.reversed))
        return [ToneCollection(c) for c in combinations(s, k)]
    
    def chords(self, k, skip):
        """Returns a collection of ToneCollections of size k,
        built on each tone of the sequence,
        with `skip` number of sequential tones between each tone in the collection.
        
        For example, to get all triads of a 7-note diatonic scale:

        ```
        diatonic_scale.chords(3, 1)
        ```
        """

        chords = []
        for i, tone in enumerate(self):
            root = tone
            chord = []
            for ct in range(k):
                j = ((skip + 1) * ct) + i
                chord.append(self[j])
            chords.append(ToneCollection(chord, root))
        return chords
                


    def __getitem__(self, index):
        if isinstance(index, int):
            return super().__getitem__(index % len(self))
        
        elif isinstance(index, slice):
            # Normalize slice values
            start = index.start or 0
            stop = index.stop if index.stop is not None else start + len(self)
            step = index.step or 1

            # Generate wrapped indices
            return [self[i % len(self)] for i in range(start, stop, step)]
        
        return super().__getitem__(index)  # fallback for unexpected types
    