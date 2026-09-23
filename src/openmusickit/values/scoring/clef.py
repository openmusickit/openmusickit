"""What fixes the meaning of the lines of a staff."""


class Clef:
    """What fixes the meaning of a staff's lines:
    which line carries which tone,
    so that a position on the staff is a pitch.

    WSMN's `StaffClef`
    (a G, F or C sign on a numbered line of the five-line staff,
    with an optional octave change;
    or the unpitched percussion and tablature signs)
    is one implementation.
    The C and F clefs of chant notation on a four-line staff would be another.
    A `ClefEvent` places one in a line.
    How pitches map to staff positions under a clef is a renderer's business;
    nothing here draws anything.

    >>> from openmusickit.systems.wsmn.scoring.staff_clef import ClefSign, StaffClef
    >>> isinstance(StaffClef(ClefSign.G, 2), Clef)
    True
    """

    __slots__ = ()
