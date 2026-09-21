import pytest

from openmusickit.systems.wsmn.tonal.chords import Chord, ChordQuality, ChordType
from openmusickit.systems.wsmn.tonal.symbols import (
    C,
    D,
    E,
    F,
    G,
    add2,
    add4,
    add9,
    add11,
    dom7,
    hdim7,
    maj,
    min7_flat5,
    min_,
)
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalDirection, TonalVector
from tests.domains import distinct


def test_symbols_include_all_chord_types(chord_type_symbols):
    """Sanity check on the fixture itself: symbols.py currently defines 77
    named chord types."""
    assert len(chord_type_symbols) == 78  # 77 distinct types plus the `m` alias of `min_`


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
        assert isinstance(chord_type.quality, ChordQuality), name


def test_maj_min_have_distinct_third(pitch_symbols):
    """maj and min_ share root and fifth, but differ on the third."""
    assert C in maj and G in maj
    assert C in min_ and G in min_
    assert E in maj
    assert pitch_symbols["Eb"] in min_
    assert E not in min_


def test_realize_chord_type_at_root(pitch_symbols):
    """Calling a ChordType with a TonalVector realizes it as a Chord rooted
    there. Also verifies the reverse-call form documented on
    ChordType.__call__: `tv(chord_type)` should produce the same Chord."""
    for _name, root in pitch_symbols.items():
        chord = maj(root)
        assert isinstance(chord, Chord)
        assert chord.root == root
        assert chord.bass == root
        assert list(chord) == [t + root for t in maj]

        # reverse-call form: TonalVector.__call__ delegates to its argument
        reverse_chord = root(maj)
        assert reverse_chord == chord


def test_every_chord_type_realizes_and_renders_at_every_root(chord_type_symbols, pitch_symbols):
    """Every chord type in symbols.py can be realized at every one of the 35
    pitch classes; each tone is the interval above the root (delegation), and
    independently, the half-step content of the chord is the type's half-step
    content shifted by the root. Every tone then renders in every string form."""
    for root_name, root in distinct(pitch_symbols).items():
        for type_name, chord_type in distinct(chord_type_symbols).items():
            chord = chord_type(root)
            assert chord.root == root, (root_name, type_name)
            assert list(chord) == [t + root for t in chord_type], (root_name, type_name)
            assert [int(t) % 12 for t in chord] == [
                (int(t) + int(root)) % 12 for t in chord_type
            ], (root_name, type_name)
            for tone in chord:
                for form in (
                    tone.pitch.unicode,
                    tone.pitch.ascii,
                    tone.pitch.verbose,
                    tone.pitch.ly,
                    tone.interval.unicode,
                ):
                    assert isinstance(form, str) and form, (root_name, type_name, tone)
            assert str(chord).startswith(root.pitch.unicode), (root_name, type_name)


def test_simple_chords_transpose_onto_altered_roots():
    """Simple (unaltered) chord types can be realized on sharp/flat roots
    too, not just naturals."""
    from openmusickit.systems.wsmn.tonal.symbols import Cb, Cx, Fb, Gx, maj7, min7

    for root in [Cb, Cx, Fb, Gx]:
        for chord_type in [maj, min_, dom7, maj7, min7]:
            chord = chord_type(root)
            assert list(chord) == [t + root for t in chord_type]
            assert chord.root == root


def test_arpeggiate_starts_on_bass():
    """arpeggiate() returns the chord's tones as a sequence starting with
    the bass tone."""
    arp = maj.arpeggiate()
    assert arp[0] == maj.bass
    assert set(arp) == set(maj)


def test_arpeggiate_inversion_starts_on_new_bass():
    first_inversion = maj.inversion(1)
    arp = first_inversion.arpeggiate()
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


# --- literal spellings, one root per chord family -------------------------------------


def _names(tones) -> list[str]:
    return [t.pitch.unicode for t in tones]


@pytest.mark.parametrize(
    "chord_type_name, root_name, expected",
    [
        ("maj", "D", ["D", "F♯", "A"]),
        ("min_", "F", ["F", "A♭", "C"]),
        ("dim", "B", ["B", "D", "F"]),
        ("aug", "Eb", ["E♭", "G", "B"]),
        ("sus2", "A", ["A", "B", "E"]),
        ("sus4", "G", ["G", "C", "D"]),
        ("pow5", "Bb", ["B♭", "F"]),
        ("maj6", "E", ["E", "G♯", "B", "C♯"]),
        ("min6", "D", ["D", "F", "A", "B"]),
        ("maj7", "Ab", ["A♭", "C", "E♭", "G"]),
        ("min7", "Fx", ["F♯", "A", "C♯", "E"]),
        ("dom7", "G", ["G", "B", "D", "F"]),
        ("hdim7", "E", ["E", "G", "B♭", "D"]),
        ("dim7", "Cx", ["C♯", "E", "G", "B♭"]),
        ("min_maj7", "C", ["C", "E♭", "G", "B"]),
        ("add2", "F", ["F", "G", "A", "C"]),
        ("add9", "F", ["F", "A", "C", "G"]),
        ("maj9", "D", ["D", "F♯", "A", "C♯", "E"]),
        ("dom9", "C", ["C", "E", "G", "B♭", "D"]),
        ("dom11", "G", ["G", "B", "D", "F", "A", "C"]),
        ("maj13", "C", ["C", "E", "G", "B", "D", "F", "A"]),
        ("dom7_sus4", "D", ["D", "G", "A", "C"]),
        ("dom7_flat9", "E", ["E", "G♯", "B", "D", "F"]),
        ("dom7_sharp9", "C", ["C", "E", "G", "B♭", "D♯"]),
        ("dom7_sharp11", "Bb", ["B♭", "D", "F", "A♭", "E"]),
        ("dom7_flat13", "A", ["A", "C♯", "E", "G", "F"]),
        ("dom7_alt", "C", ["C", "E", "B♭", "D♭", "D♯", "G♭", "A♭"]),
        ("dim9", "D", ["D", "F", "A♭", "C♭", "E"]),
    ],
)
def test_chord_spellings(chord_type_symbols, pitch_symbols, chord_type_name, root_name, expected):
    """Hand-written spellings, independent of the arithmetic: one root per
    chord family (triads, sixths, sevenths, added-tone, ninths, elevenths,
    thirteenths, sus, altered dominants, diminished)."""
    chord = chord_type_symbols[chord_type_name](pitch_symbols[root_name])
    assert _names(chord) == expected


def test_lead_sheet_symbols():
    from openmusickit.systems.wsmn.tonal.symbols import Bb, Eb, Fx, dom7_flat9, maj7, min7, sus4

    assert str(Fx(min7)) == "F♯min7"
    assert str(Bb(maj7) / D) == "B♭maj7/D"
    assert str(Eb(dom7_flat9)) == "E♭7♭9"
    assert str(G(sus4).inversion(1)) == "Gsus4/C"
    assert str(C(maj)) == "C" and str(C(min_)) == "Cmin"


# --- inversion laws over every chord type and every realized chord -------------------


def test_inversion_laws_over_every_chord_type(chord_type_symbols):
    """The k-th inversion has the k-th tone as its bass and the same tones;
    inversion 0 is the type itself; the slash form is the same inversion;
    arpeggiation starts at the bass and is a rotation of the tones; the
    label names the inversion; one past the last tone is an IndexError."""
    for name, chord_type in distinct(chord_type_symbols).items():
        assert chord_type.inversion(0) == chord_type, name
        assert chord_type.bass == chord_type.root == TonalVector((0, 0)), name
        for k in range(len(chord_type)):
            inverted = chord_type.inversion(k)
            assert inverted.bass == chord_type[k], (name, k)
            assert list(inverted) == list(chord_type), (name, k)
            assert chord_type / chord_type[k] == inverted, (name, k)
            assert inverted.quality is chord_type.quality, (name, k)
            arpeggio = inverted.arpeggiate()
            assert arpeggio[0] == inverted.bass, (name, k)
            assert list(arpeggio) == list(chord_type)[k:] + list(chord_type)[:k], (name, k)
            assert (" inv." in str(inverted)) == (k > 0), (name, k, str(inverted))
        with pytest.raises(IndexError):
            chord_type.inversion(len(chord_type))


def test_inversion_laws_over_every_realized_chord(chord_type_symbols, pitch_symbols):
    """Inverting a realized chord moves the bass and nothing else: the root
    stays where the type was realized, the tones keep their order, and the
    slash form and arpeggiation agree with the type's."""
    for root_name, root in distinct(pitch_symbols).items():
        for type_name, chord_type in distinct(chord_type_symbols).items():
            chord = chord_type(root)
            for k in range(len(chord)):
                inverted = chord.inversion(k)
                assert inverted.root == root, (root_name, type_name, k)
                assert inverted.bass == chord[k], (root_name, type_name, k)
                assert list(inverted) == list(chord), (root_name, type_name, k)
                assert chord / chord[k] == inverted, (root_name, type_name, k)
                assert list(inverted.arpeggiate()) == list(chord)[k:] + list(chord)[:k], (
                    root_name,
                    type_name,
                    k,
                )
                assert ("/" in str(inverted)) == (k > 0), (root_name, type_name, k)


def test_transposing_a_realized_chord_up_then_down_restores_it(chord_type_symbols):
    """Transposition moves root, tones and bass together, and is undone by
    transposing back, for every chord type at C in every inversion."""
    from openmusickit.systems.wsmn.tonal.symbols import M3, m6

    for name, chord_type in distinct(chord_type_symbols).items():
        for k in range(len(chord_type)):
            chord = chord_type(C).inversion(k)
            for i in (M3, m6):
                moved = chord.transform(TonalVector.transpose, i)
                assert moved.root == C + i, (name, k, i)
                assert moved.bass == chord.bass + i, (name, k, i)
                assert list(moved) == [t + i for t in chord], (name, k, i)
                assert moved.suffix == chord.suffix and moved.name == chord.name, (name, k, i)
                assert moved.transform(TonalVector.transpose, i, TonalDirection.DOWN) == chord, (
                    name,
                    k,
                    i,
                )


@pytest.mark.xfail(
    strict=True,
    reason="revisit: inversion onto a tone the chord does not contain is accepted, "
    "and the bad bass only surfaces later as a ValueError from list.index in arpeggiate",
)
def test_inversion_onto_a_tone_not_in_the_chord_is_rejected():
    from openmusickit.systems.wsmn.tonal.symbols import Db

    with pytest.raises(ValueError):
        maj.inversion(Db)
    with pytest.raises(ValueError):
        C(maj) / Db
