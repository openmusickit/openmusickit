from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from itertools import combinations

from openmusickit.values.tone.tone import Tone


def apply_tone_operation(
    operation: Callable[..., Tone], tone: Tone, *args, expected: type = Tone, **kwargs
) -> Tone:
    """Returns `operation(tone, *args, **kwargs)`, checking the result is an `expected` Tone.

    The one validation used by every `transform`/`transform_tones` implementation,
    so they all fail the same way when handed an operation that does not produce a Tone.

    >>> from openmusickit.systems.wsmn.tonal.symbols import C, M3
    >>> from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
    >>> apply_tone_operation(TonalVector.transpose, C, M3)
    TonalVector((2, 4))
    >>> apply_tone_operation(str, C)
    Traceback (most recent call last):
    ...
    TypeError: `operation` must return a Tone, but returned 'TonalVector((0, 0)) # C' for TonalVector((0, 0)).
    """
    result = operation(tone, *args, **kwargs)
    if not isinstance(result, expected):
        raise TypeError(
            f"`operation` must return a {expected.__name__}, but returned {result!r} for {tone!r}."
        )
    return result


@dataclass(frozen=True, slots=True)
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

    tones: tuple[Tone, ...]
    root: Tone | None = None
    name_template: str | None = field(default=None, compare=False)

    def __init__(
        self,
        tones: Iterable[Tone] = (),
        root: Tone | None = None,
        name: str | None = None,
    ):
        object.__setattr__(self, "tones", tuple(tones))
        object.__setattr__(self, "root", root)
        object.__setattr__(self, "name_template", name)

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
        if self.name_template is None:
            return None

        return self.name_template.format(root=self.root)

    def __iter__(self):
        return iter(self.tones)

    def __len__(self):
        return len(self.tones)

    def __getitem__(self, index):
        return self.tones[index]

    def __contains__(self, tone) -> bool:
        return tone in self.tones

    def __repr__(self) -> str:
        return f"{type(self).__name__}({list(self.tones)!r}, root={self.root!r})"

    def combinations(self, k: int) -> list[ToneCollection]:
        """Returns a list of all ToneCollection subsets of k members."""
        return [ToneCollection(c) for c in combinations(self.tones, k)]

    def all_combinations(self) -> list[ToneCollection]:
        """Returns a list of all ToneCollection subsets of length `2` through `len(self)-1`."""
        combos = []
        for k in range(2, len(self)):
            for c in combinations(self.tones, k):
                combos.append(ToneCollection(c))
        return combos

    def transform(
        self, operation: Callable[..., Tone], *args, new_name: str | None = None, **kwargs
    ) -> ToneCollection:
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
            return apply_tone_operation(operation, tone, *args, **kwargs)

        new_root = None if self.root is None else apply(self.root)
        new_tones = [apply(t) for t in self.tones]

        if new_name is None:
            new_name = self.name_template

        return ToneCollection(new_tones, new_root, new_name)
