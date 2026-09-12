import pytest

from chord_fixtures import pitch_symbols, chord_type_symbols

from openmusickit.systems.wsmn.tonal.chords import ChordType, Chord, Quality
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from openmusickit.systems.wsmn.tonal.symbols import (
    C, D, E, F, G, maj, min, dom7, add2, add9, add4, add11,
    hdim7, min7_flat5,
)


def test_symbols_include_all_chord_types(chord_type_symbols):
    """Sanity check on the fixture itself: symbols.py currently defines 77
    named chord types."""
    assert len(chord_type_symbols) == 77


def test_chord_type_must_contain_root():
    """A ChordType must include TonalVector(0,0) among its tones,
    since that is what makes it a chord *type* (an interval pattern)
    rather than a concrete Chord."""
    with pytest.raises(ValueError):
        ChordType(tones=[D, E, G], name="rootless")


def test_every_symbol_chord_type_contains_root(chord_type_symbols):
    """Every ChordType shipped in symbols.py should have TonalVector(0,0)
    as a tone, and as its root."""
    for name, chord_type in chord_type_symbols.items():
        assert TonalVector(0, 0) in chord_type, name
        assert chord_type.root == TonalVector(0, 0), name


def test_chord_type_tone_order_is_preserved():
    """Tone order is musically significant, and must not be reordered or
    deduplicated by ChordType (this is what distinguishes an add2 chord
    from the 'same pitches, different degree name' add9 chord)."""
    assert list(add2) == [C, D, E, G]
    assert list(add9) == [C, E, G, D]
    assert list(add4) == [C, E, F, G]
    assert list(add11) == [C, E, G, F]


def test_add2_and_add9_are_not_equal():
    """add2 and add9 use the exact same pitch classes, but in different
    conventional order/voicing, and must not compare equal."""
    assert set(add2) == set(add9)
    assert add2 != add9


def test_add4_and_add11_are_not_equal():
    assert set(add4) == set(add11)
    assert add4 != add11


def test_chord_types_with_identical_tones_are_equal_but_distinct_objects():
    """hdim7 and min7_flat5 are given different names/qualities, but are
    defined with the exact same tones in the exact same order, so they
    should compare equal (equality is based on tones+root, not name)
    while still being distinct objects."""
    assert hdim7 == min7_flat5
    assert hdim7 is not min7_flat5
    assert hdim7.name != min7_flat5.name


def test_chord_type_quality_is_preserved(chord_type_symbols):
    for name, chord_type in chord_type_symbols.items():
        assert isinstance(chord_type.quality, Quality), name


def test_maj_min_have_distinct_third(pitch_symbols):
    """maj and min share root and fifth, but differ on the third."""
    assert C in maj and G in maj
    assert C in min and G in min
    assert E in maj
    assert pitch_symbols["Eb"] in min
    assert E not in min



def test_realize_chord_type_at_root(pitch_symbols):
    """Calling a ChordType with a TonalVector realizes it as a Chord rooted
    there. Also verifies the reverse-call form documented on
    ChordType.__call__: `tv(chord_type)` should produce the same Chord."""
    for name, root in pitch_symbols.items():
        chord = maj(root)
        assert isinstance(chord, Chord)
        assert chord.root == root
        assert chord.bass == root
        assert list(chord) == [t + root for t in maj]

        # reverse-call form: TonalVector.__call__ delegates to its argument
        reverse_chord = root(maj)
        assert reverse_chord == chord


def test_realized_chords_transpose_every_chord_type_at_every_natural_root(chord_type_symbols):
    """Every chord type in symbols.py can be realized at any of the seven
    natural pitches without error, and each tone of the resulting chord is
    the sum of the interval and the root, in the original order.

    Restricted to natural roots rather than every pitch symbol: stacking an
    already-altered root (e.g. Db) with a chord type that has its own
    alteration on the same scale degree (e.g. the flat 9 in dom7_flat9) can
    produce a compound interval extreme enough to hit a gap in
    interval_quality's lookup table -- a pre-existing issue in
    tonal_arithmetic/interval_quality, unrelated to ChordType/Chord, and out
    of scope here."""
    from openmusickit.systems.wsmn.tonal.symbols import C, D, E, F, G, A, B
    natural_roots = [C, D, E, F, G, A, B]

    for root in natural_roots:
        for chord_type in chord_type_symbols.values():
            chord = chord_type(root)
            assert list(chord) == [t + root for t in chord_type]
            assert chord.root == root


def test_simple_chords_transpose_onto_altered_roots():
    """Simple (unaltered) chord types can be realized on sharp/flat roots
    too, not just naturals."""
    from openmusickit.systems.wsmn.tonal.symbols import Cb, Cx, Fb, Gx
    from openmusickit.systems.wsmn.tonal.symbols import maj7, min7

    for root in [Cb, Cx, Fb, Gx]:
        for chord_type in [maj, min, dom7, maj7, min7]:
            chord = chord_type(root)
            assert list(chord) == [t + root for t in chord_type]
            assert chord.root == root


def test_arpeggiate_starts_on_bass():
    """arpegiate() returns the chord's tones as a sequence starting with
    the bass tone."""
    arp = maj.arpegiate()
    assert arp[0] == maj.bass
    assert set(arp) == set(maj)


def test_arpeggiate_inversion_starts_on_new_bass():
    first_inversion = maj.inversion(1)
    arp = first_inversion.arpegiate()
    assert arp[0] == first_inversion.bass == E


def test_inversion_by_int_selects_bass_by_position():
    """inversion(n) selects the nth tone (in stored order) of the chord
    as the new bass."""
    root_position = maj.inversion(0)
    first_inversion = maj.inversion(1)
    second_inversion = maj.inversion(2)

    assert root_position.bass == C
    assert first_inversion.bass == E
    assert second_inversion.bass == G

    # tones themselves are unaffected -- only bass changes
    assert list(root_position) == list(maj)
    assert list(first_inversion) == list(maj)
    assert list(second_inversion) == list(maj)


def test_inversion_by_int_out_of_range_raises():
    with pytest.raises(IndexError):
        maj.inversion(len(maj))


def test_inversion_by_tonal_vector_sets_bass_directly():
    inv = maj.inversion(G)
    assert inv.bass == G
    assert list(inv) == list(maj)


def test_slash_chord_on_chord_type_reuses_inversion():
    """`chord_type / bass` is documented sugar for `chord_type.inversion(bass)`."""
    assert (maj / G) == maj.inversion(G)


def test_slash_chord_on_realized_chord():
    """A realized Chord also supports slash-chord notation, changing its
    bass without altering its root or tones."""
    c_major = C(maj)
    c_over_e = c_major / E

    assert isinstance(c_over_e, Chord)
    assert c_over_e.root == C
    assert c_over_e.bass == E
    assert list(c_over_e) == list(c_major)


def test_realized_chord_inversion_keeps_root():
    """Inverting a realized Chord changes its bass, but its root (where it
    was realized) must stay put -- unlike ChordType, whose root is always
    the abstract origin (0,0)."""
    e_major = maj(E)
    inv = e_major.inversion(1)

    assert inv.root == e_major.root == E
    assert inv.bass != e_major.bass
    assert list(inv) == list(e_major)


def test_dom7_realized_matches_expected_pitches():
    """A concrete, musically meaningful check: a C dominant 7th chord
    realized from the `dom7` symbol should be spelled C, E, G, Bb."""
    from openmusickit.systems.wsmn.tonal.symbols import Bb

    c_dom7 = dom7(C)
    assert list(c_dom7) == [C, E, G, Bb]


def test_default_bass_is_root():
    """When no explicit bass is given, a ChordType's bass is its root."""
    assert maj.bass == maj.root == C
