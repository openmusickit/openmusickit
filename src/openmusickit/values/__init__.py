"""Values are immutable datatypes representing musical primitives.

Most Values are abstract base classes representing fundamental musical concepts,
and need to be subclassed within a specific tonal or temporal musical system."""

from . import scoring, time, tone

__all__ = [
    "scoring",
    "time",
    "tone",
]
