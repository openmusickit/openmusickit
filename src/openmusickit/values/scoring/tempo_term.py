"""A verbal tempo indication as it appears in a notation system's vocabulary."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TempoTerm:
    """A tempo word as it appears in a notation system's vocabulary
    (Allegro, Andante, a tempo).
    The thing placed in a score is a `TempoEvent` holding one of these,
    beside the `TemporalRatio` the word stands for, or alone.

    A term is descriptive.
    The conventional beats-per-minute range of a word, where it has one,
    is stated in its `description` and is not data.
    `aliases` are other printed forms of the same word
    ("Tempo I" for tempo primo).

    >>> TempoTerm(name="allegro")
    TempoTerm(name='allegro', description=None, aliases=())
    >>> TempoTerm(name="tempo primo", aliases=("Tempo I",)).aliases
    ('Tempo I',)
    """

    name: str
    description: str | None = None
    aliases: tuple[str, ...] = ()
