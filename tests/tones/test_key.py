import pytest


from openmusickit.systems.wsmn.tonal.key import KeySignature, ModePattern, Key
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from openmusickit.systems.wsmn.tonal.chords import Quality
from openmusickit.values.tone.tone_collection import ToneCollection
from openmusickit.systems.wsmn.tonal.symbols import (
    C, D, E, F, G, A, B,
    Cb, Db, Eb, Gb, Ab, Bb, Cx, Fx,
    P1, a1, M2, M3, P5, M6,
    Major, Minor,
    Ionian, Dorian, Phrygian, Lydian, Mixolydian, Aeolian, Locrian,
    NoKey,
)


# Order in which sharps (and, reversed, flats) accumulate, as C..B indices.
SHARP_ORDER = [3, 0, 4, 1, 5, 2, 6]  # F C G D A E B

# Position of each natural letter (indexed by d) on the circle of fifths,
# expressed as the `fifths` of its major key: F=-1, C=0, G=1, D=2, A=3, E=4, B=5.
LETTER_FIFTHS = {0: 0, 1: 2, 2: 4, 3: -1, 4: 1, 5: 3, 6: 5}

# Each diatonic mode's key signature, relative to the major key on the same tonic.
MODE_FIFTHS_OFFSET = {
    "Lydian": 1,
    "Major": 0, "Ionian": 0,
    "Mixolydian": -1,
    "Dorian": -2,
    "Minor": -3, "Aeolian": -3,
    "Phrygian": -4,
    "Locrian": -5,
}

DIATONIC_MODES = [Major, Minor, Ionian, Dorian, Phrygian, Lydian, Mixolydian, Aeolian, Locrian]

# The 15 conventional key signatures, by number of sharps (+) or flats (-).
STANDARD_SIGNATURES = {
    -7: KeySignature(c=-1, d=-1, e=-1, f=-1, g=-1, a=-1, b=-1),
    -6: KeySignature(c=-1, d=-1, e=-1, g=-1, a=-1, b=-1),
    -5: KeySignature(d=-1, e=-1, g=-1, a=-1, b=-1),
    -4: KeySignature(d=-1, e=-1, a=-1, b=-1),
    -3: KeySignature(e=-1, a=-1, b=-1),
    -2: KeySignature(e=-1, b=-1),
    -1: KeySignature(b=-1),
    0: KeySignature(),
    1: KeySignature(f=1),
    2: KeySignature(c=1, f=1),
    3: KeySignature(c=1, f=1, g=1),
    4: KeySignature(c=1, d=1, f=1, g=1),
    5: KeySignature(a=1, c=1, d=1, f=1, g=1),
    6: KeySignature(a=1, c=1, d=1, e=1, f=1, g=1),
    7: KeySignature(a=1, b=1, c=1, d=1, e=1, f=1, g=1),
}


@pytest.fixture
def chromatic_tonics(tonal_tuples):
    """All 35 WSMN pitch classes: naturals, sharps, flats, double sharps, double flats."""
    return [TonalVector(t) for t in tonal_tuples]


# --------------------------------------------------------------------------
# KeySignature construction and letter properties
# --------------------------------------------------------------------------

def test_key_signature_is_a_seven_tuple_in_c_to_b_order():
    ks = KeySignature(c=1, d=2, e=3, f=-1, g=-2, a=-3, b=0)
    assert tuple(ks) == (1, 2, 3, -1, -2, -3, 0)
    assert (ks.c, ks.d, ks.e, ks.f, ks.g, ks.a, ks.b) == (1, 2, 3, -1, -2, -3, 0)


def test_key_signature_defaults_to_all_natural():
    assert tuple(KeySignature()) == (0,) * 7


@pytest.mark.parametrize("letter", "cdefgab")
@pytest.mark.parametrize("value", [4, -4, 3.5, -3.5])
def test_key_signature_rejects_alterations_beyond_triple(letter, value):
    with pytest.raises(ValueError):
        KeySignature(**{letter: value})


@pytest.mark.parametrize("value", [3, -3, 0.5, -0.5])
def test_key_signature_accepts_triples_and_microtones(value):
    assert KeySignature(f=value).f == value


def test_key_signature_equality_is_tuple_equality():
    assert KeySignature(c=1, f=1) == KeySignature(f=1, c=1)
    assert KeySignature(c=1, f=1) == (1, 0, 0, 1, 0, 0, 0)
    assert KeySignature(c=1, f=1) != KeySignature(f=1)
    assert hash(KeySignature(f=1)) == hash((0, 0, 0, 1, 0, 0, 0))


# --------------------------------------------------------------------------
# KeySignature.__repr__
# --------------------------------------------------------------------------

def test_repr_shows_only_nonzero_alterations_as_kwargs():
    assert repr(KeySignature()) == "KeySignature()"
    assert repr(KeySignature(f=1)) == "KeySignature(f=1)"
    assert repr(KeySignature(e=-1, a=-1, b=-1)) == "KeySignature(e=-1, a=-1, b=-1)"
    assert repr(KeySignature(f=0.5)) == "KeySignature(f=0.5)"


@pytest.mark.parametrize("n", range(-21, 22))
def test_repr_round_trips_through_eval(n):
    ks = KeySignature.from_alts(n)
    assert eval(repr(ks)) == ks


# --------------------------------------------------------------------------
# KeySignature.from_alts and .fifths
# --------------------------------------------------------------------------

@pytest.mark.parametrize("n, expected", STANDARD_SIGNATURES.items())
def test_from_alts_produces_the_standard_signatures(n, expected):
    assert KeySignature.from_alts(n) == expected


@pytest.mark.parametrize("n, expected", STANDARD_SIGNATURES.items())
def test_fifths_of_the_standard_signatures(n, expected):
    assert expected.fifths == n


@pytest.mark.parametrize("n", range(-21, 22))
def test_from_alts_and_fifths_are_inverses(n):
    assert KeySignature.from_alts(n).fifths == n


@pytest.mark.parametrize("n", range(-21, 22))
def test_from_alts_accumulates_in_sharp_or_flat_order(n):
    """Beyond 7, alterations wrap around and become doubles, then triples,
    always in the same F C G D A E B (or reversed) order."""
    ks = KeySignature.from_alts(n)
    order = SHARP_ORDER if n >= 0 else SHARP_ORDER[::-1]
    sign = 1 if n >= 0 else -1
    q, r = divmod(abs(n), 7)
    for position, index in enumerate(order):
        expected = sign * (q + 1 if position < r else q)
        assert ks[index] == expected, (n, "cdefgab"[index])
    assert sum(ks) == n


@pytest.mark.parametrize("n", [22, -22, 100, -100])
def test_from_alts_rejects_more_than_triple_alterations(n):
    with pytest.raises(ValueError):
        KeySignature.from_alts(n)


@pytest.mark.parametrize("ks", [
    KeySignature(f=1, b=-1),                 # mixed sharps and flats
    KeySignature(c=1),                       # C# without F#
    KeySignature(b=1),                       # B# alone
    KeySignature(e=-1),                      # Eb without Bb
    KeySignature(f=-1),                      # Fb alone
    KeySignature(f=2),                       # Fx without the other six sharps
    KeySignature(f=1, c=1, g=1, d=1, a=1, e=1, b=2),  # B## before F##
    KeySignature(f=0.5),                     # microtonal
    KeySignature(f=1, c=1, g=2),             # gap: G## but C# single
])
def test_fifths_raises_for_nonstandard_signatures(ks):
    with pytest.raises(AttributeError):
        ks.fifths


# --------------------------------------------------------------------------
# ModePattern
# --------------------------------------------------------------------------

def test_mode_pattern_must_begin_at_the_root():
    with pytest.raises(ValueError):
        ModePattern(name="bad", tones=ToneCollection([M2, M3]))


def test_mode_pattern_is_frozen():
    with pytest.raises(AttributeError):
        Major.name = "Other"


def test_every_symbol_mode_is_a_seven_note_pattern_from_the_root():
    for mode in DIATONIC_MODES:
        assert mode.tones[0] is TonalVector((0, 0)), mode.name
        assert len(mode.tones) == 7, mode.name
        assert [t.d for t in mode.tones] == list(range(7)), mode.name


def test_major_and_minor_alias_ionian_and_aeolian():
    assert Major.tones == Ionian.tones
    assert Minor.tones == Aeolian.tones
    assert Major.name != Ionian.name
    assert Minor.name != Aeolian.name


def test_diatonic_modes_are_rotations_of_the_major_scale():
    """Each mode on its white-key tonic uses only naturals."""
    for tonic, mode in zip([C, D, E, F, G, A, B],
                           [Ionian, Dorian, Phrygian, Lydian, Mixolydian, Aeolian, Locrian]):
        key = Key.of(tonic, mode)
        assert key.signature == KeySignature(), mode.name
        assert [t.d for t in key.tones] == [(tonic.d + i) % 7 for i in range(7)], mode.name


# --------------------------------------------------------------------------
# Key.of across the full chromatic set of tonics
# --------------------------------------------------------------------------

def test_chromatic_tonics_fixture_covers_all_35_pitch_classes(chromatic_tonics):
    assert len(chromatic_tonics) == 35
    assert len(set(chromatic_tonics)) == 35


def test_key_of_transposes_the_mode_to_the_tonic(chromatic_tonics):
    for tonic in chromatic_tonics:
        for mode in DIATONIC_MODES:
            key = Key.of(tonic, mode)
            assert key.tonic is tonic
            assert key.tones[0] is tonic
            assert key.tones.root is tonic
            assert len(key.tones) == 7
            # letters ascend from the tonic, each used exactly once
            assert [t.d for t in key.tones] == [(tonic.d + i) % 7 for i in range(7)], key.name
            # chromatic values are the mode's intervals above the tonic
            assert [t.c for t in key.tones] == [(tonic.c + i.c) % 12 for i in mode.tones], key.name


def test_key_of_does_not_modify_the_mode_pattern(chromatic_tonics):
    before = {mode.name: (list(mode.tones), mode.tones.root) for mode in DIATONIC_MODES}
    for tonic in chromatic_tonics:
        for mode in DIATONIC_MODES:
            Key.of(tonic, mode)
    for mode in DIATONIC_MODES:
        assert (list(mode.tones), mode.tones.root) == before[mode.name]


def test_key_of_derives_signature_matching_every_tone(chromatic_tonics):
    """Each letter's alteration in the signature equals the alteration of
    that letter's tone in the key, so the key can be written with no accidentals."""
    for tonic in chromatic_tonics:
        for mode in DIATONIC_MODES:
            key = Key.of(tonic, mode)
            for tone in key.tones:
                assert key.signature[tone.d] == tone.pitch._modifier_value, (key.name, tone)


def test_key_of_derived_signature_is_standard_with_the_expected_fifths(chromatic_tonics):
    """Every diatonic mode on every chromatic tonic (up to double sharps/flats)
    yields a standard, circle-of-fifths signature, and that signature's `fifths`
    is the tonic letter's position + 7 per accidental + the mode's offset."""
    for tonic in chromatic_tonics:
        for mode in DIATONIC_MODES:
            key = Key.of(tonic, mode)
            expected = (
                LETTER_FIFTHS[tonic.d]
                + 7 * tonic.pitch._modifier_value
                + MODE_FIFTHS_OFFSET[mode.name]
            )
            assert key.signature.fifths == expected, key.name
            assert key.signature == KeySignature.from_alts(expected), key.name


def test_key_of_names(chromatic_tonics):
    for tonic in chromatic_tonics:
        for mode in DIATONIC_MODES:
            key = Key.of(tonic, mode)
            assert key.name == f"{tonic.pitch.unicode} {mode.name}"
            assert key.mode == mode.name


def test_relative_major_and_minor_share_a_signature(chromatic_tonics):
    for tonic in chromatic_tonics:
        relative_minor = tonic.transpose(M6)
        assert Key.of(tonic, Major).signature == Key.of(relative_minor, Minor).signature, tonic


@pytest.mark.parametrize("tonic, expected", [
    (Cb, -7), (Gb, -6), (Db, -5), (Ab, -4), (Eb, -3), (Bb, -2), (F, -1),
    (C, 0), (G, 1), (D, 2), (A, 3), (E, 4), (B, 5), (Fx, 6), (Cx, 7),
])
def test_major_circle_of_fifths(tonic, expected):
    assert Key.of(tonic, Major).signature == STANDARD_SIGNATURES[expected]


# --------------------------------------------------------------------------
# Key.of edge cases
# --------------------------------------------------------------------------

def test_key_of_uses_an_explicit_signature_without_inspection():
    odd = KeySignature(f=1, b=-1)
    key = Key.of(C, Major, odd)
    assert key.signature is odd


def test_key_of_raises_when_a_letter_has_conflicting_alterations():
    chromatic_ish = ModePattern(name="conflict", tones=ToneCollection([P1, a1, M2]))
    with pytest.raises(ValueError):
        Key.of(C, chromatic_ish)


def test_key_of_conflict_is_avoided_by_an_explicit_signature():
    chromatic_ish = ModePattern(name="conflict", tones=ToneCollection([P1, a1, M2]))
    key = Key.of(C, chromatic_ish, KeySignature())
    assert key.signature == KeySignature()


def test_key_of_leaves_absent_letters_natural():
    """A gapped (pentatonic) mode still gets a signature; unused letters are natural."""
    pentatonic = ModePattern(name="Major Pentatonic",
                             tones=ToneCollection([P1, M2, M3, P5, M6]))
    assert Key.of(Fx, pentatonic).signature == KeySignature(f=1, g=1, a=1, c=1, d=1)
    assert Key.of(Eb, pentatonic).signature == KeySignature(e=-1, b=-1)


def test_key_of_keeps_mode_quality():
    assert Key.of(C, Major)._mode.quality is Quality.MAJ
    assert Key.of(C, Locrian)._mode.quality is Quality.HDM


# --------------------------------------------------------------------------
# Key naming fallbacks and NoKey
# --------------------------------------------------------------------------

def test_key_name_falls_back_to_tonic_and_mode():
    key = Key(tonic=D, tones=ToneCollection([D]), signature=KeySignature(), _mode=Dorian)
    assert key.name == "D Dorian"


def test_key_name_falls_back_when_no_mode():
    key = Key(tonic=Eb, tones=ToneCollection([Eb]), signature=KeySignature())
    assert key.name == "E♭ (unspecified mode)"
    assert key.mode is None


def test_explicit_name_wins():
    key = Key(tonic=C, tones=ToneCollection([C]), signature=KeySignature(), _mode=Major,
              _name="Do major")
    assert key.name == "Do major"


def test_no_key():
    assert NoKey.tonic is None
    assert NoKey.mode is None
    assert NoKey.name == "No Key"
    assert NoKey.signature == KeySignature()
    assert NoKey.signature.fifths == 0
    assert len(NoKey.tones) == 0


def test_key_is_frozen():
    key = Key.of(C, Major)
    with pytest.raises(AttributeError):
        key.tonic = D
