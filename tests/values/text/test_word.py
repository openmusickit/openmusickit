"""`Word`: the syllables of one word as sung, with its accent pattern."""

import pytest

from openmusickit.errors import LyricConsistencyError
from openmusickit.values.text.word import LexicalStress, Word

PRIMARY, SECONDARY = LexicalStress.PRIMARY, LexicalStress.SECONDARY


def test_word_basics():
    word = Word(["al", "le", "lu", "ia"])
    assert len(word) == 4
    assert word[2] == "lu"
    assert list(word) == ["al", "le", "lu", "ia"]
    assert str(word) == "alleluia"
    assert word.stress == (None, None, None, None)
    assert word.primary is None
    assert [word.stress_at(i) for i in range(4)] == [None] * 4


def test_word_from_string_without_marks():
    assert Word.from_string("Je-sus") == Word(["Je", "sus"])
    assert Word.from_string("sing") == Word(["sing"])


def test_word_from_string_with_marks():
    word = Word.from_string(",un-der-'stand")
    assert word.syllables == ("un", "der", "stand")
    assert word.stress == (SECONDARY, None, PRIMARY)
    assert word.primary == 2
    assert word.stress_at(0) is SECONDARY
    assert word.stress_at(1) is None
    assert word.stress_at(2) is PRIMARY


def test_word_from_string_marks_can_be_turned_off():
    assert Word.from_string("'tis", primary=None).syllables == ("'tis",)
    assert Word.from_string(",un-'der", primary=None, secondary=None).syllables == (",un", "'der")


def test_word_from_string_custom_hyphen_and_marks():
    word = Word.from_string("al_le_*lu_ia", hyphen="_", primary="*")
    assert word.syllables == ("al", "le", "lu", "ia")
    assert word.primary == 2
    assert Word.from_string("al--le-").syllables == ("al", "le")


def test_word_trailing_comma_is_text_and_leading_comma_is_stress():
    word = Word.from_string(",ia,")
    assert word.syllables == ("ia,",)
    assert word.stress == (SECONDARY,)


def test_word_stress_from_mapping_and_sequence_agree():
    by_index = Word(["al", "le", "lu", "ia"], stress={2: PRIMARY})
    parallel = Word(["al", "le", "lu", "ia"], stress=[None, None, PRIMARY, None])
    assert by_index == parallel
    assert hash(by_index) == hash(parallel)


def test_word_equality_counts_stress():
    assert Word(["al", "le"], stress={0: PRIMARY}) != Word(["al", "le"])
    assert Word(["al", "le"], stress={0: PRIMARY}) != Word(["al", "le"], stress={0: SECONDARY})


@pytest.mark.parametrize(
    "syllables, stress",
    [
        ([], None),
        (["al", ""], None),
        (["al", "  "], None),
        (["al", "le"], [PRIMARY]),
        (["al", "le"], {0: PRIMARY, 1: PRIMARY}),
        (["al", "le"], {2: PRIMARY}),
        (["al", "le"], {-1: PRIMARY}),
    ],
)
def test_word_rejects_inconsistent_input(syllables, stress):
    with pytest.raises(LyricConsistencyError):
        Word(syllables, stress)


def test_word_is_immutable():
    with pytest.raises(AttributeError):
        Word(["al"]).syllables = ("le",)


def test_str_then_from_string_is_lossy_by_design():
    """`str` joins the syllables, so parsing it back gives one syllable and
    no stress: the hyphenated spelling, not `str`, is the round-trip form."""
    word = Word.from_string("al-le-'lu-ia")
    assert str(word) == "alleluia"
    assert Word.from_string(str(word)) == Word(["alleluia"])
    assert Word.from_string(str(word)) != word


def test_hyphenated_spelling_round_trips_through_from_string():
    """Joining the syllables with hyphens and putting the marks back in
    front of the stressed ones reproduces the Word exactly."""
    marks = {PRIMARY: "'", SECONDARY: ",", None: ""}
    for spelling in ["Je-sus", "'Je-sus,", ",un-der-'stand", "al-le-'lu-ia", "sing", "'tis"]:
        word = Word.from_string(spelling)
        respelled = "-".join(marks[word.stress_at(i)] + syllable for i, syllable in enumerate(word))
        assert Word.from_string(respelled) == word, spelling
        assert Word.from_string("-".join(word), primary=None, secondary=None) == Word(list(word))


def test_repr_shows_syllables_and_marked_stress_only():
    assert repr(Word.from_string("Je-sus")) == "Word('Je', 'sus')"
    assert (
        repr(Word.from_string("al-le-'lu-ia"))
        == "Word('al', 'le', 'lu', 'ia', stress={2: 'primary'})"
    )
    assert repr(Word.from_string(",un-der-'stand")) == (
        "Word('un', 'der', 'stand', stress={0: 'secondary', 2: 'primary'})"
    )
