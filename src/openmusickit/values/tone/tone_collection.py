from __future__ import annotations
from itertools import combinations
from typing import Callable, Iterable, List
from .tone import Tone

class ToneCollection:
    """An ordered collection of tones, with an optional root and optional name.

    Tone order is preserved and is musically significant: for example, it is
    what distinguishes a chord with an added 2nd from one with an added 9th,
    even though both consist of the same pitch classes.

    Note that `name` can be a formattable string including `{root}`,
    which allows chord names to update automatically in the case of transposition.
    `{root}` renders as the root's display form (see `Tone.__format__`),
    so `{root:ascii}` and the like also work.

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
        """The name template formatted with `root`.

        >>> from openmusickit.systems.wsmn.tonal.symbols import Eb, G, Bb
        >>> ToneCollection([Eb, G, Bb], root=Eb, name="{root} major").name
        'E♭ major'
        >>> ToneCollection([Eb, G, Bb], root=Eb, name="{root:ascii} major").name
        'Eb major'
        >>> ToneCollection([Eb, G, Bb], name="a triad").name
        'a triad'
        >>> ToneCollection([Eb, G, Bb]).name is None
        True
        """
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

    def transform(self, operation: Callable[..., Tone], *args,
                  new_name: str | None = None, **kwargs) -> ToneCollection:
        """Returns a new ToneCollection made by applying `operation` to every
        tone of this collection (and to `root`, if set).

        `operation` is called as `operation(tone, *args, **kwargs)` for each
        tone. It is typically a method of the relevant Tone subclass (such as
        `TonalVector.transpose`), but any callable that accepts a Tone as its
        first argument and returns a Tone will do. If the operation returns
        something that is not a Tone, a TypeError is raised.

        The new collection keeps this collection's name template unless
        `new_name` is given. The original ToneCollection is left unmodified.

        Used for tonal transformations such as transposition and inversion.

        Examples
        --------

        >>> from openmusickit.systems.wsmn.tonal.symbols import C, E, G, Gx, B, M3
        >>> from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector, TonalDirection

        Transposition, with the interval passed as the operand. Tone order
        is preserved, and the root is transformed along with the tones:

        >>> triad = ToneCollection([C, E, G], root=C, name="{root} major")
        >>> up = triad.transform(TonalVector.transpose, M3)
        >>> up == ToneCollection([E, Gx, B], root=E)
        True
        >>> up.name
        'E major'
        >>> up.transform(TonalVector.transpose, M3, TonalDirection.DOWN) == triad
        True

        The original is unchanged:

        >>> triad == ToneCollection([C, E, G], root=C)
        True

        A user-defined operation that needs no operand, with a new name:

        >>> def sharpen(tv):
        ...     return tv + TonalVector((0, 1))
        >>> sharp = triad.transform(sharpen, new_name="{root} major (sharpened)")
        >>> list(sharp)
        [TonalVector((0, 1)), TonalVector((2, 5)), TonalVector((4, 8))]
        >>> sharp.name
        'C♯ major (sharpened)'

        A collection with no root works too:

        >>> ToneCollection([C, E]).transform(TonalVector.transpose, M3)
        ToneCollection([TonalVector((2, 4)), TonalVector((4, 8))], root=None)

        An operation that does not produce a Tone is rejected:

        >>> triad.transform(str)
        Traceback (most recent call last):
        ...
        TypeError: ...
        """

        def apply(tone: Tone) -> Tone:
            new_tone = operation(tone, *args, **kwargs)
            if not isinstance(new_tone, Tone):
                raise TypeError(
                    f"`operation` must return a Tone, "
                    f"but returned {new_tone!r} for {tone!r}."
                )
            return new_tone

        new_root = None if self.root is None else apply(self.root)
        new_tones = [apply(t) for t in self._tones]

        if new_name is None:
            new_name = self._name_template

        return ToneCollection(new_tones, new_root, new_name)


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
    