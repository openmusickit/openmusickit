from __future__ import annotations
from itertools import combinations
from typing import Iterable, List
from .tone import Tone

class ToneCollection(frozenset):
    """An unordered collection of tones, with an optional root and optional name.
    
    Note that `name` can be a formattable string including `{root}`,
    which allows chord names to update automatically in the case of transposition."""

    def __new__(
        cls,
        tones: Iterable[Tone] = (),
        root: Tone | None = None,
        name: str | None = None,
    ):
        obj = super().__new__(cls, tones)
        obj.root = root
        obj._name_template = name
        return obj

    @property
    def name(self) -> str | None:
        if self._name_template is None:
            return None

        return self._name_template.format(root=self.root)

    def combinations(self, k) -> list[ToneCollection]:
        """Returns a list of all ToneCollection subsets of k members."""
        return [ToneCollection(c) for c in combinations(self, k)]
    
    def all_combinations(self) -> list[ToneCollection]:
        """Returns a list of all ToneCollection subsets of length `2` through `len(self)-1`."""
        combos = []
        for k in range(2, len(self)):
            for c in combinations(self, k):
                combos.append(ToneCollection(c))
        return combos

    def __getattr__(self, name):
        """Delegates method calls to the members of the collection (and its root),
        returning a new ToneCollection.
        Used for tonal transformations such as transposition and inversion.

        This is only invoked for attributes that are not found through normal
        means (i.e. not defined on ToneCollection, set, or an instance's own
        __dict__). It assumes `name` refers to a method defined on the Tone
        members of this collection, and returns a wrapper function that,
        when called:

        - Calls the method (with whatever args/kwargs are passed) on every
          member of the set, collecting the results into a new iterable.
        - Calls the method on `self.root` (if a root is set), collecting
          the result as the new root.
        - Returns a new ToneCollection built from those results, sharing
          the original collection's `name_template`.

        The original ToneCollection is left unmodified.

        Raises:
            AttributeError: if a member (or the root) does not implement
                `name`.
        """

        # Avoid interfering with dunder/special attribute lookups
        # (e.g. pickling, copying, repr helpers, etc.)
        if name.startswith('__') and name.endswith('__'):
            raise AttributeError(name)

        def method(*args, **kwargs):
            new_tones = []
            for member in self:
                try:
                    member_method = getattr(member, name)
                except AttributeError as e:
                    raise AttributeError(
                        f"ToneCollection member {member} does not have method "
                        f"{name}, and raised an error: {e}"
                    ) from e
                new_tones.append(member_method(*args, **kwargs))

            new_root = None
            if self.root is not None:
                try:
                    root_method = getattr(self.root, name)
                except AttributeError as e:
                    raise AttributeError(
                        f"ToneCollection root {self.root} does not have method "
                        f"{name}, and raised an error: {e}"
                    ) from e
                new_root = root_method(*args, **kwargs)

            return ToneCollection(new_tones, new_root, self._name_template)

        return method


# fix reverse to start with root tone

class ToneSequence(list):
    """An ordered collection of non-repeated tones,
    with an optional name and optional reversed form and name.

    Could be used as is, but more likely
    should be subclassed for structures like scales, modes, tone rows, ragas, etc.
    
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
    