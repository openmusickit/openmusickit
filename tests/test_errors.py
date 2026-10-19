"""The exception hierarchy in `openmusickit.errors`: every OMK error is an
`OmkError`, each domain error also subclasses the closest built-in, and the
warning base is a `UserWarning`, not an error.
"""

import inspect
import warnings

import pytest

from openmusickit import errors
from openmusickit.errors import (
    GraphError,
    GraphvizNotFoundError,
    LyricConsistencyError,
    MusicXmlError,
    OmkError,
    OmkWarning,
    RenderingError,
    ScalingError,
    TemporalCompatibilityError,
    TemporalError,
    UnexportableError,
)

OMK_ERRORS = {
    name: cls
    for name, cls in vars(errors).items()
    if inspect.isclass(cls) and issubclass(cls, OmkError)
}


def test_the_error_classes_in_the_module():
    assert set(OMK_ERRORS) == {
        "OmkError",
        "TemporalError",
        "ScalingError",
        "TemporalCompatibilityError",
        "LyricConsistencyError",
        "GraphError",
        "RenderingError",
        "GraphvizNotFoundError",
        "MusicXmlError",
        "UnexportableError",
    }


def test_every_omk_error_is_catchable_as_omk_error():
    for name, cls in OMK_ERRORS.items():
        with pytest.raises(OmkError):
            raise cls(f"raised {name}")
        assert issubclass(cls, Exception), name
        assert not issubclass(cls, Warning), name


def test_domain_errors_subclass_the_closest_builtin():
    assert issubclass(LyricConsistencyError, ValueError)
    assert issubclass(LyricConsistencyError, OmkError)
    with pytest.raises(ValueError):
        raise LyricConsistencyError("inconsistent")
    assert issubclass(ScalingError, TemporalError)
    assert issubclass(TemporalCompatibilityError, TemporalError)
    assert issubclass(RenderingError, RuntimeError)
    assert issubclass(GraphvizNotFoundError, RenderingError)
    assert issubclass(MusicXmlError, ValueError)
    assert issubclass(UnexportableError, ValueError)
    assert not issubclass(ScalingError, TemporalCompatibilityError)
    assert not issubclass(GraphError, TemporalError)


def test_omk_warning_is_a_user_warning_not_an_error():
    assert issubclass(OmkWarning, UserWarning)
    assert not issubclass(OmkWarning, OmkError)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        warnings.warn("nothing happened", OmkWarning, stacklevel=1)
    assert [w.category for w in caught] == [OmkWarning]
    with warnings.catch_warnings():
        warnings.simplefilter("error", OmkWarning)
        with pytest.raises(OmkWarning):
            warnings.warn("escalated", OmkWarning, stacklevel=1)
