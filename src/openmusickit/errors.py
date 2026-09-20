"""Exceptions and warnings raised by OpenMusicKit.

Every OMK-specific exception derives from `OmkError`, so a caller can catch
the whole family at once; the domain subclasses exist for callers that need
to tell the failures apart (for example, to fall back to another strategy).
"""


class OmkError(Exception):
    """Base class for exceptions raised by OpenMusicKit."""


class OmkWarning(UserWarning):
    """Base class for warnings issued by OpenMusicKit.

    Issued (via `warnings.warn`) when an operation is a no-op or otherwise
    does less than the caller might expect, but is not an error. Callers can
    catch, filter, or escalate these with the standard `warnings` machinery:

        >>> import warnings
        >>> with warnings.catch_warnings():
        ...     warnings.simplefilter("error", OmkWarning)
        ...     warnings.warn("nothing happened", OmkWarning)
        Traceback (most recent call last):
            ...
        openmusickit.errors.OmkWarning: nothing happened
    """


class TemporalError(OmkError):
    """Base class for temporal system errors."""


class ScalingError(TemporalError):
    """Raised when a Measurable cannot perform the requested scaling operation.

    This covers scalars that are invalid in any system (zero, negative,
    non-rational), and scaled values that a particular TemporalSystem
    has no way to represent.

    Systems whose elements can always be re-spelled should do so rather than
    raise (WSMN's MetricalDuration, for example, resolves non-power-of-two
    scalars into dotted values, tuplets, or tied notes). Systems that cannot
    should raise this so callers can fall back to an alternate strategy,
    such as a composite element or a clock-time calculation.
    """


class TemporalCompatibilityError(TemporalError):
    """Raised when temporal elements from incompatible systems are combined.

    Callers may catch this error and implement an alternate compatibility strategy,
    such as clock-time calculations.
    """


class LyricConsistencyError(OmkError, ValueError):
    """Raised when lyric data is not self consistent."""


class GraphError(OmkError):
    """Raised by the graph layer for a missing node or edge, or a relationship the
    graph cannot hold (for example a second NEXT edge out of one node). Backend
    exceptions never pass through the adapter boundary."""
