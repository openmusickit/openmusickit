from __future__ import annotations
from itertools import combinations
from typing import Iterable, List
from .tone import Tone

class ToneCollection:
    """An ordered collection of tones, with an optional root and optional name.

    Tone order is preserved and is musically significant: for example, it is
    what distinguishes a chord with an added 2nd from one with an added 9th,
    even though both consist of the same pitch classes.

    Note that `name` can be a formattable string including `{root}`,
    which allows chord names to update automatically in the case of transposition.

    Equality and hashing are based on tones and root only (not `name`),
    so two ToneCollections built from the same tones and root compare equal
    even if they were given different names -- but they remain distinct
    objects (`is` is unaffected).
    """

    def __init__(
        self,
        tones: Iterable[Tone] = (),
        root: Tone | None = None,
        name: str | None = None,
    ):
        self._tones = tuple(tones)
        self.root = root
        self._name_template = name

    @property
    def name(self) -> str | None:
        if self._name_template is None:
            return None

        return self._name_template.format(root=self.root)

    def __iter__(self):
        return iter(self._tones)

    def __len__(self):
        return len(self._tones)

    def __getitem__(self, index):
        return self._tones[index]

    def __contains__(self, tone) -> bool:
        return tone in self._tones

    def __eq__(self, other) -> bool:
        if not isinstance(other, ToneCollection):
            return NotImplemented
        return self._tones == other._tones and self.root == other.root

    def __hash__(self) -> int:
        return hash((self._tones, self.root))

    def __repr__(self) -> str:
        return f"{type(self).__name__}({list(self._tones)!r}, root={self.root!r})"

    def combinations(self, k) -> list[ToneCollection]:
        """Returns a list of all ToneCollection subsets of k members."""
        return [ToneCollection(c) for c in combinations(self._tones, k)]
    
    def all_combinations(self) -> list[ToneCollection]:
        """Returns a list of all ToneCollection subsets of length `2` through `len(self)-1`."""
        combos = []
        for k in range(2, len(self)):
            for c in combinations(self._tones, k):
                combos.append(ToneCollection(c))
        return combos

    def map_tones(self, method_name: str, *args, **kwargs) -> ToneCollection:
        """Calls `method_name` on every tone in the collection (and on `root`,
        if set), returning a new ToneCollection built from the results.

        Used for tonal transformations such as transposition and inversion.

        The original ToneCollection is left unmodified.

        Raises:
            AttributeError: if a tone (or the root) does not implement
                `method_name`.
        """

        new_tones = []
        for member in self._tones:
            try:
                member_method = getattr(member, method_name)
            except AttributeError as e:
                raise AttributeError(
                    f"ToneCollection member {member} does not have method "
                    f"{method_name}, and raised an error: {e}"
                ) from e
            new_tones.append(member_method(*args, **kwargs))

        new_root = None
        if self.root is not None:
            try:
                root_method = getattr(self.root, method_name)
            except AttributeError as e:
                raise AttributeError(
                    f"ToneCollection root {self.root} does not have method "
                    f"{method_name}, and raised an error: {e}"
                ) from e
            new_root = root_method(*args, **kwargs)

        return ToneCollection(new_tones, new_root, self._name_template)


# fix reverse to start with root tone

class ToneSequence(list):
    """An ordered collection of non-repeated tones,
    with an optional name and optional reversed form and name.

    Could be used as is, but more likely
    should be subclassed for structures like scales, modes, tone rows, ragas, etc.
    
    DO NOT include the octave tone. This will break things.
    If you need a ToneSequence that specifies an octave tone,
    subclass this and re-implement `__getitem__` and probably `chords`."""

    def __init__(self, tones: List[Tone], rev: List[Tone]=None, name: str=None,
                 rev_name=None, _reverse_of: "ToneSequence"=None):
        super().__init__(tones)
        self.name = name

        if rev_name is None:
            if name:
                rev_name = name + "-reversed"
            else:
                rev_name = None

        if _reverse_of is not None:
            # We are being constructed as the `reversed` counterpart of
            # `_reverse_of`. Point back at it rather than building another
            # reversed sequence, which would recurse forever.
            self.reversed = _reverse_of
            return

        reversed_tones = rev if rev is not None else list(reversed(tones))
        self.reversed = ToneSequence(reversed_tones, name=rev_name, _reverse_of=self)
    
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
    