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
        openmusickit.utils.omk_warning.OmkWarning: nothing happened
    """
