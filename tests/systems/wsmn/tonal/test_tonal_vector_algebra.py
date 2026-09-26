"""Algebraic laws of `TonalVector`, the class users touch, over every vector
in the test domain (`tests.domains`): 35 abstract pitch classes, which double
as the 35 simple intervals, and 175 octave-qualified pitches.

Each law is stated in musical terms in its docstring, then swept with plain
nested loops; an assertion carries the vectors it failed on.
"""

import pytest

from openmusickit.systems.wsmn.tonal import symbols
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalDirection, TonalVector
from tests.domains import ABSTRACT_VECTORS, ALL_VECTORS, QUALIFIED_VECTORS, in_domain

DOWN = TonalDirection.DOWN
UP = TonalDirection.UP

C4 = TonalVector((0, 0, 0))
P1, M2 = TonalVector((0, 0)), TonalVector((1, 2))


def _pairs(domain):
    return [(a, b) for a in domain for b in domain]


def _difference_in_domain(a, b) -> bool:
    return in_domain(a - b) and in_domain(b - a)


# --- transposition ------------------------------------------------------------


def test_adding_then_subtracting_an_interval_is_identity():
    """Going up an interval and back down it lands on the starting pitch,
    with its octave if it had one."""
    for a in ALL_VECTORS:
        for i in ABSTRACT_VECTORS:
            assert (a + i) - i == a, (a, i)
            assert (a - i) + i == a, (a, i)


def test_transpose_up_then_down_is_identity():
    """Transposing up by an interval and then down by the same interval
    returns the original pitch, with its octave if it had one."""
    for a in ALL_VECTORS:
        for i in ABSTRACT_VECTORS:
            assert a.transpose(i).transpose(i, DOWN) == a, (a, i)
            assert a.transpose(i, DOWN).transpose(i) == a, (a, i)
            assert a.transpose(i) - i == a, (a, i)


def test_an_interval_between_two_pitches_transposes_the_one_to_the_other():
    """The law the tonal contract is stated in: the difference of two pitches
    is the interval that carries the first to the second. The tests above
    sweep a pitch against an *interval*; this sweeps a pitch against another
    *pitch*, which is the form a tonal system has to satisfy to be one."""
    for a in ABSTRACT_VECTORS:
        for b in ABSTRACT_VECTORS:
            if in_domain(b - a):
                assert a + (b - a) == b, (a, b)
                assert a.transpose(b - a) == b, (a, b)
    for a in QUALIFIED_VECTORS:
        for b in QUALIFIED_VECTORS:
            if in_domain(b - a):
                assert a + (b - a) == b, (a, b)


def test_transpose_direction_is_addition_or_subtraction():
    """Transposing up is `+`, transposing down is `-`, and up is the default."""
    for a in ALL_VECTORS:
        for i in ABSTRACT_VECTORS:
            assert a.transpose(i) == a.transpose(i, UP) == a + i, (a, i)
            assert a.transpose(i, DOWN) == a - i, (a, i)


def test_transposition_preserves_octave_kind():
    """An abstract pitch stays abstract and a qualified pitch stays qualified
    under transposition by a simple interval."""
    for a in ALL_VECTORS:
        for i in ABSTRACT_VECTORS:
            assert (a + i).has_octave == a.has_octave, (a, i)
            assert (a - i).has_octave == a.has_octave, (a, i)


def test_an_abstract_pitch_cannot_be_moved_by_a_qualified_interval():
    """A pitch class has no octave for an octave-qualified interval to act on;
    the other way round works and keeps the octave."""
    for a in ABSTRACT_VECTORS:
        for q in QUALIFIED_VECTORS:
            with pytest.raises(TypeError):
                a + q
            with pytest.raises(TypeError):
                a - q
            assert (q + a).has_octave and (q - a).has_octave, (q, a)


# --- inversion ------------------------------------------------------------------


def test_inversion_is_an_involution():
    """Inverting twice, over the origin or over any other pitch, gives back
    the original."""
    for a in ALL_VECTORS:
        assert a.inversion().inversion() == a, a
        for c in ALL_VECTORS:
            if a.has_octave or not c.has_octave:
                assert a.inversion(c).inversion(c) == a, (a, c)
            else:
                # an abstract pitch inverted over a qualified one is qualified
                assert a.inversion(c).inversion(c) == a.qualify_octave(0), (a, c)


def test_inversion_undoes_transposition_only_on_abstract_vectors():
    """Pitch-class inversion of M2 is m7; going up M2 then up m7 lands an
    octave higher, not back home. The octave is the point of a qualified
    vector, so `transpose(i, DOWN)` (or `- i`) is the inverse there, never
    `transpose(i.inversion())`. Unison-class intervals are the exception:
    an augmented unison and a diminished unison add to a plain unison."""
    assert C4.transpose(M2).transpose(M2.inversion()) == TonalVector((0, 0, 1))
    assert C4.transpose(M2).transpose(M2, DOWN) == C4

    for a in ABSTRACT_VECTORS:
        for i in ABSTRACT_VECTORS:
            assert a.transpose(i).transpose(i.inversion()) == a, (a, i)

    for a in QUALIFIED_VECTORS:
        for i in ABSTRACT_VECTORS:
            up_and_round = a.transpose(i).transpose(i.inversion())
            if i.d == 0:
                assert up_and_round == a, (a, i)
            else:
                assert up_and_round == a.qualify_octave(a.o + 1), (a, i)


# --- size and order ---------------------------------------------------------------


def test_size_of_a_qualified_difference():
    """Between two octave-qualified pitches the distance is the same either
    way round, and the signed size of the difference is the difference of
    the signed sizes; asserted where the difference is a spellable interval."""
    for a, b in _pairs(QUALIFIED_VECTORS):
        if _difference_in_domain(a, b):
            assert abs(a - b) == abs(b - a), (a, b)
            assert int(a - b) == int(a) - int(b), (a, b)


def test_size_of_an_abstract_difference():
    """Between two pitch classes the two differences are the ascending
    intervals each way round the octave, so they cancel modulo 12; `abs`
    of an abstract vector is the size of that ascending interval, not a
    symmetric distance (use `distance` for that)."""
    for a, b in _pairs(ABSTRACT_VECTORS):
        if _difference_in_domain(a, b):
            assert (int(a - b) + int(b - a)) % 12 == 0, (a, b)
            assert (int(a - b) - (int(a) - int(b))) % 12 == 0, (a, b)
    assert abs(symbols.C - symbols.D) == 10  # up a minor seventh
    assert abs(symbols.D - symbols.C) == 2  # up a major second


def test_distance_is_symmetric_and_within_a_tritone():
    """The distance between two pitch classes is the same in either order and
    never more than a tritone; between two qualified pitches it is the
    same in either order."""
    for a, b in _pairs(ABSTRACT_VECTORS):
        assert a.distance(b) == b.distance(a), (a, b)
        assert abs(a.distance(b)) <= 6, (a, b)
    for a, b in _pairs(QUALIFIED_VECTORS):
        assert a.distance(b) == b.distance(a), (a, b)


def test_distance_is_a_magnitude_and_does_not_carry_a_direction():
    """`distance` answers "how far apart", not "what gets me there": it is
    unsigned, so transposing by it lands on the second pitch only when that
    pitch is the higher of the two and nothing is spelled enharmonically.
    C to G is a fourth away -- C up a fourth is F, not G. Use `b - a` to
    move from one to the other (see the law in the transposition section).

    This pins a deliberate asymmetry that reads like a bug: making
    `distance` directed would satisfy every other test in this file."""
    recovered = [
        (a, b)
        for a in ABSTRACT_VECTORS
        for b in ABSTRACT_VECTORS
        if a.transpose(a.distance(b)) == b
    ]
    assert len(recovered) < len(ABSTRACT_VECTORS) ** 2  # it is not a recovery operation
    assert symbols.C.distance(symbols.G) == symbols.P4
    assert symbols.C.transpose(symbols.C.distance(symbols.G)) == symbols.F
    assert symbols.C + (symbols.G - symbols.C) == symbols.G

    for a in ABSTRACT_VECTORS:
        for b in ABSTRACT_VECTORS:
            assert a.distance(b) == a.distance(b).inversion().inversion(), (a, b)
            if a.transpose(a.distance(b)) != b:
                assert a + (b - a) == b, (a, b)  # the directed difference always works


def test_nearest_instance_has_the_pitch_class_asked_for():
    """The nearest instance of b to a is b's pitch class, placed within a
    tritone of a when a has an octave."""
    for a in ALL_VECTORS:
        for b in ALL_VECTORS:
            n = a.nearest_instance(b)
            assert (n.d, n.c) == (b.d, b.c), (a, b, n)
            assert n.has_octave == a.has_octave, (a, b, n)
            if a.has_octave:
                assert abs(int(a) - int(n)) <= 6, (a, b, n)


def test_comparison_is_a_total_order_up_to_half_step_size():
    """`<` and `>` order pitches (and intervals) by size in half-steps: one
    of `a < b`, `a > b`, or `int(a) == int(b)` holds, never both of the
    first two, and each is the mirror of the other."""
    for domain in (ABSTRACT_VECTORS, QUALIFIED_VECTORS):
        for a, b in _pairs(domain):
            assert (a < b) == (b > a), (a, b)
            assert (a > b) == (b < a), (a, b)
            assert not (a < b and a > b), (a, b)
            assert (a < b) or (a > b) or int(a) == int(b), (a, b)
            assert (a < b) == (int(a) < int(b)), (a, b)


# --- the line of fifths -------------------------------------------------------------


def test_fifths_position_is_a_group_homomorphism():
    """Transposition acts on the line of fifths by translation: the position
    of a sum is the sum of the positions, for every pair whose sum is still
    a domain spelling. Read as a pitch, the position is the signed number of
    sharps in the major key on that tonic; read as an interval, it is how
    far a signature travels when its tonic moves by that interval."""
    for a in ABSTRACT_VECTORS:
        for b in ABSTRACT_VECTORS:
            if in_domain(a + b):
                assert (a + b).fifths_position == a.fifths_position + b.fifths_position, (a, b)


def test_fifths_position_ignores_the_octave():
    """A pitch class and every octave of it sit at the same place on the line."""
    for v in ABSTRACT_VECTORS:
        for o in (-2, -1, 0, 1, 2):
            assert v.qualify_octave(o).fifths_position == v.fifths_position, (v, o)


def test_the_line_of_fifths_does_not_wrap():
    """Spelling is what is being counted, so the line is not a circle:
    B-sharp is twelve fifths up from C, not back at it."""
    assert symbols.C.fifths_position == 0
    assert symbols.Bx.fifths_position == 12
    assert symbols.Cb.fifths_position == -7
    assert len({v.fifths_position for v in ABSTRACT_VECTORS}) == len(ABSTRACT_VECTORS)


# --- value semantics ----------------------------------------------------------------


def test_repr_round_trips():
    for v in ALL_VECTORS:
        assert eval(repr(v)) == v, v


def test_equality_and_hash_agree_with_the_tuple():
    """A TonalVector is its tuple: equal to it, hashed like it, and equal to
    another vector exactly when the tuples are equal."""
    for v in ALL_VECTORS:
        assert v == tuple(v), v
        assert hash(v) == hash(tuple(v)), v
    for a, b in _pairs(ALL_VECTORS):
        assert (a == b) == (tuple(a) == tuple(b)), (a, b)
        if a == b:
            assert hash(a) == hash(b), (a, b)


def test_enharmonic_equivalents_are_not_equal():
    """C-sharp and D-flat have the same size but are different vectors."""
    for a, b in _pairs(ALL_VECTORS):
        if a != b and a.has_octave == b.has_octave and int(a) == int(b):
            assert hash(a) != hash(b) or a != b, (a, b)
            assert not (a == b), (a, b)


PITCH_INTERVAL_ALIASES = [
    ("Cbb", "dd1"), ("Cb", "d1"), ("C", "P1"), ("Cx", "a1"), ("Cxx", "aa1"),
    ("Dbb", "d2"), ("Db", "m2"), ("D", "M2"), ("Dx", "a2"), ("Dxx", "aa2"),
    ("Ebb", "d3"), ("Eb", "m3"), ("E", "M3"), ("Ex", "a3"), ("Exx", "aa3"),
    ("Fbb", "dd4"), ("Fb", "d4"), ("F", "P4"), ("Fx", "a4"), ("Fxx", "aa4"),
    ("Gbb", "dd5"), ("Gb", "d5"), ("G", "P5"), ("Gx", "a5"), ("Gxx", "aa5"),
    ("Abb", "d6"), ("Ab", "m6"), ("A", "M6"), ("Ax", "a6"), ("Axx", "aa6"),
    ("Bbb", "d7"), ("Bb", "m7"), ("B", "M7"), ("Bx", "a7"), ("Bxx", "aa7"),
]  # fmt: skip


def test_pitch_and_interval_symbols_are_the_same_objects(pitch_symbols):
    """A pitch class above C and the interval from C to it are one value:
    `C is P1`, `Bb is m7`. The 35 pairs cover every abstract vector."""
    assert len(PITCH_INTERVAL_ALIASES) == 35
    for pitch_name, interval_name in PITCH_INTERVAL_ALIASES:
        assert pitch_symbols[pitch_name] is pitch_symbols[interval_name], (
            pitch_name,
            interval_name,
        )
    assert {pitch_symbols[p] for p, _ in PITCH_INTERVAL_ALIASES} == set(ABSTRACT_VECTORS)
    assert symbols.C is symbols.P1
    assert symbols.Bb is symbols.m7
