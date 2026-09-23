import pytest

from openmusickit.systems.wsmn.scoring.staff_clef import ClefSign, StaffClef
from openmusickit.systems.wsmn.scoring.symbols import (
    alto_clef,
    baritone_clef,
    baritone_f_clef,
    bass_clef,
    bass_clef_8va,
    bass_clef_8vb,
    bass_clef_15mb,
    french_clef,
    mezzo_soprano_clef,
    no_clef,
    percussion_clef,
    soprano_clef,
    subbass_clef,
    tab_clef,
    tenor_clef,
    treble_clef,
    treble_clef_8va,
    treble_clef_8vb,
    treble_clef_15ma,
)
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from openmusickit.values.scoring.clef import Clef

G4, F3, C4 = (4, 7, 0), (3, 5, -1), (0, 0, 0)


def test_construction_stores_sign_line_and_octave_change():
    assert (treble_clef.sign, treble_clef.line, treble_clef.octave_change) == (ClefSign.G, 2, 0)
    assert (percussion_clef.sign, percussion_clef.line) == (ClefSign.PERCUSSION, None)
    assert treble_clef_8vb.octave_change == -1
    assert StaffClef(ClefSign.C, 3) == alto_clef


def test_pitched_signs_need_a_staff_line_1_to_5():
    for sign in (ClefSign.G, ClefSign.F, ClefSign.C):
        for line in (None, 0, 6, "2"):
            with pytest.raises(ValueError, match="staff line 1 to 5"):
                StaffClef(sign, line)
        assert all(StaffClef(sign, line).line == line for line in range(1, 6))


def test_unpitched_signs_take_no_line():
    for sign in (ClefSign.PERCUSSION, ClefSign.TAB, ClefSign.NONE):
        with pytest.raises(ValueError, match="no particular line"):
            StaffClef(sign, 1)
        assert StaffClef(sign).line is None


def test_reference_tone_for_every_symbol():
    expected = {
        treble_clef: G4,
        french_clef: G4,
        soprano_clef: C4,
        mezzo_soprano_clef: C4,
        alto_clef: C4,
        tenor_clef: C4,
        baritone_clef: C4,
        baritone_f_clef: F3,
        bass_clef: F3,
        subbass_clef: F3,
        treble_clef_8vb: (4, 7, -1),
        treble_clef_8va: (4, 7, 1),
        bass_clef_8vb: (3, 5, -2),
        bass_clef_8va: (3, 5, 0),
        treble_clef_15ma: (4, 7, 2),
        bass_clef_15mb: (3, 5, -3),
        percussion_clef: None,
        tab_clef: None,
        no_clef: None,
    }
    assert len(expected) == 19
    for clef, tone in expected.items():
        if tone is None:
            assert clef.reference_tone is None, clef
        else:
            assert clef.reference_tone == TonalVector(tone), clef
    assert treble_clef.reference_tone.pitch.unicode == "G4"
    assert bass_clef.reference_tone.pitch.unicode == "F3"
    assert alto_clef.reference_tone.pitch.unicode == "C4"
    assert treble_clef_8vb.reference_tone.pitch.unicode == "G3"


def test_repr_round_trips(clef_symbols):
    for name, clef in clef_symbols.items():
        assert eval(repr(clef)) == clef, name
    assert repr(treble_clef) == "StaffClef(ClefSign.G, 2)"
    assert repr(treble_clef_8vb) == "StaffClef(ClefSign.G, 2, octave_change=-1)"
    assert repr(percussion_clef) == "StaffClef(ClefSign.PERCUSSION)"


def test_a_staff_clef_is_a_clef_and_is_frozen():
    assert isinstance(treble_clef, Clef)
    with pytest.raises(AttributeError):
        treble_clef.line = 1


def test_every_symbol_is_a_distinct_hashable_staff_clef(clef_symbols):
    clefs = list(clef_symbols.values())
    assert all(type(clef) is StaffClef for clef in clefs)
    assert len(set(clefs)) == len(clefs) == 19
    for clef in clefs:
        if clef.sign in (ClefSign.G, ClefSign.F, ClefSign.C):
            assert clef.line in range(1, 6) and isinstance(clef.reference_tone, TonalVector)
        else:
            assert clef.line is None and clef.reference_tone is None
