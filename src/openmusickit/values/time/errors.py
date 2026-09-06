class TemporalError(Exception):
    """Base class for temporal system errors."""

class ScalingError(TemporalError):
    """Raised when a TemporalElement cannot represent the requested scaling operation.
    
    Callers may catch this error and implement an alternate scaling strategy,
    such as tuplets or tied notes.
    """

class TemporalCompatibilityError(TemporalError):
    """Raised when temporal elements from incompatible systems are combined.
    
    Callers may catch this error and implement an alternate compatibility strategy,
    such as clock-time calculations.
    """