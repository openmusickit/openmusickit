"""`ToneCollection`: an ordered, optionally rooted, optionally named set of
tones. Laws are checked over every mode pattern and every chord type in the
WSMN symbol tables, taken as plain collections, and over all 35 intervals.
"""

import itertools
import math

import pytest

from openmusickit.systems.wsmn.tonal.symbols import M3, C, E, Eb, G
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalDirection, TonalVector
from openmusickit.values.tone.tone_collection import ToneCollection, apply_tone_operation
from tests.domains import ABSTRACT_VECTORS, distinct

DOWN = TonalDirection.DOWN


def _collections(mode_pattern_symbols, chord_type_symbols) -> dict[str, ToneCollection]:
    """Every mode and chord type as a plain ToneCollection, rooted at C."""
    found = {name: mode.tones for name, mode in mode_pattern_symbols.items()}
    for name, chord_type in distinct(chord_type_symbols).items():
        found[name] = ToneCollection(chord_type, root=chord_type.root, name=name)
    return found


# --- sequence protocol ------------------------------------------------------------


def test_order_length_indexing_and_containment():
    triad = ToneCollection([C, E, G], root=C, name="{root} major")
    assert list(triad) == [C, E, G]
    assert len(triad) == 3
    assert triad[1] is E and triad[-1] is G
    assert E in triad and Eb not in triad
    assert triad.tones == (C, E, G)
    assert repr(triad) == (
        "ToneCollection([TonalVector((0, 0)), TonalVector((2, 4)), TonalVector((4, 7))], "
        "root=TonalVector((0, 0)))"
    )


def test_the_empty_collection():
    empty = ToneCollection()
    assert len(empty) == 0 and list(empty) == [] and empty.root is None
    assert empty.name is None
    assert empty.transform(TonalVector.transpose, M3) == empty
    assert empty.all_combinations() == []


# --- equality, hashing, naming ------------------------------------------------------


def test_equality_ignores_the_name_but_not_the_root_or_the_order():
    assert ToneCollection([C, E, G], root=C, name="major") == ToneCollection([C, E, G], root=C)
    assert hash(ToneCollection([C, E, G], root=C, name="major")) == hash(
        ToneCollection([C, E, G], root=C)
    )
    assert ToneCollection([C, E, G], root=C) != ToneCollection([C, E, G], root=E)
    assert ToneCollection([C, E, G], root=C) != ToneCollection([C, E, G])
    assert ToneCollection([C, E, G]) != ToneCollection([E, C, G])
    assert ToneCollection([C, E, G], root=C).name is None


def test_name_is_the_template_formatted_with_the_root():
    assert ToneCollection([Eb, G], root=Eb, name="{root} major").name == "E♭ major"
    assert ToneCollection([Eb, G], root=Eb, name="{root:ascii} major").name == "Eb major"
    assert ToneCollection([Eb, G], name="a dyad").name == "a dyad"
    assert ToneCollection([Eb, G], root=Eb, name="{root} major").name_template == "{root} major"


def test_it_is_frozen():
    with pytest.raises(AttributeError):
        ToneCollection([C]).tones = ()


# --- combinations -------------------------------------------------------------------


def test_combinations_are_ordered_subsets_of_the_expected_count(
    mode_pattern_symbols, chord_type_symbols
):
    """`combinations(k)` has n-choose-k members, each a k-subset in the
    collection's own order; `all_combinations` is every k from 2 to n-1."""
    for name, collection in _collections(mode_pattern_symbols, chord_type_symbols).items():
        n = len(collection)
        tones = list(collection)
        expected_all = []
        for k in range(0, n + 1):
            combos = collection.combinations(k)
            assert len(combos) == math.comb(n, k), (name, k)
            for combo in combos:
                assert isinstance(combo, ToneCollection), (name, k)
                assert len(combo) == k, (name, k)
                assert combo.root is None, (name, k)
                assert all(t in collection for t in combo), (name, k, combo)
                positions = [tones.index(t) for t in combo]
                assert positions == sorted(positions), (name, k, combo)
            if 2 <= k <= n - 1:
                expected_all.extend(combos)
        assert collection.all_combinations() == expected_all, name


# --- transform -------------------------------------------------------------------------


def test_transposing_up_then_down_restores_every_collection(
    mode_pattern_symbols, chord_type_symbols
):
    """Transposition by any interval and back is the identity on the tones,
    the root, and the name template, and never reorders the tones."""
    for name, collection in _collections(mode_pattern_symbols, chord_type_symbols).items():
        for i in ABSTRACT_VECTORS:
            up = collection.transform(TonalVector.transpose, i)
            assert list(up) == [t + i for t in collection], (name, i)
            assert up.root == (None if collection.root is None else collection.root + i), (name, i)
            assert up.name_template == collection.name_template, (name, i)
            back = up.transform(TonalVector.transpose, i, DOWN)
            assert back == collection, (name, i)
            assert back.name_template == collection.name_template, (name, i)
            assert list(back) == list(collection), (name, i)


def test_transform_leaves_the_original_alone_and_can_rename():
    triad = ToneCollection([C, E, G], root=C, name="{root} major")
    moved = triad.transform(TonalVector.transpose, M3, new_name="{root} triad")
    assert moved.name == "E triad"
    assert triad == ToneCollection([C, E, G], root=C)
    assert triad.name == "C major"


def test_transform_rejects_an_operation_that_does_not_return_a_tone():
    triad = ToneCollection([C, E, G], root=C)
    with pytest.raises(TypeError):
        triad.transform(str)
    with pytest.raises(TypeError):
        apply_tone_operation(str, C)
    assert apply_tone_operation(TonalVector.transpose, C, M3) == E


def test_transform_passes_keyword_arguments_through():
    triad = ToneCollection([C, E, G], root=C)
    assert triad.transform(TonalVector.transpose, M3, direction=DOWN) == ToneCollection(
        [C - M3, E - M3, G - M3], root=C - M3
    )


def test_every_pair_of_collections_is_equal_exactly_when_tones_and_root_agree(
    mode_pattern_symbols, chord_type_symbols
):
    collections = _collections(mode_pattern_symbols, chord_type_symbols)
    for (na, a), (nb, b) in itertools.product(collections.items(), repeat=2):
        same = tuple(a) == tuple(b) and a.root == b.root
        assert (a == b) == same, (na, nb)
        if same:
            assert hash(a) == hash(b), (na, nb)
