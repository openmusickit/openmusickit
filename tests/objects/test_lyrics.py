import pytest

from openmusickit.errors import LyricConsistencyError
from openmusickit.graph.edge import EdgeType
from openmusickit.graph.graph import GraphMeta, OmkGraph
from openmusickit.objects.lyrics import LyricSection, LyricSyllable, SyllablePlacement, parse_lyrics
from openmusickit.objects.note_event import NoteEvent
from openmusickit.objects.omk_object import Spanner
from openmusickit.systems.wsmn.temporal.symbols import quarter
from openmusickit.systems.wsmn.tonal.symbols import C, D, E, F
from openmusickit.values.text.word import LexicalStress, Word

PRIMARY, SECONDARY = LexicalStress.PRIMARY, LexicalStress.SECONDARY


# --- Word --------------------------------------------------------------------


def test_word_basics():
    word = Word(["al", "le", "lu", "ia"])
    assert len(word) == 4
    assert word[2] == "lu"
    assert list(word) == ["al", "le", "lu", "ia"]
    assert str(word) == "alleluia"
    assert word.stress == (None, None, None, None)
    assert word.primary is None


def test_word_from_string_without_marks():
    assert Word.from_string("Je-sus") == Word(["Je", "sus"])
    assert Word.from_string("sing") == Word(["sing"])


def test_word_from_string_with_marks():
    word = Word.from_string(",un-der-'stand")
    assert word.syllables == ("un", "der", "stand")
    assert word.stress == (SECONDARY, None, PRIMARY)
    assert word.primary == 2
    assert word.stress_at(0) is SECONDARY


def test_word_from_string_marks_can_be_turned_off():
    assert Word.from_string("'tis", primary=None).syllables == ("'tis",)


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


@pytest.mark.parametrize(
    "syllables, stress",
    [
        ([], None),
        (["al", ""], None),
        (["al", "  "], None),
        (["al", "le"], [PRIMARY]),
        (["al", "le"], {0: PRIMARY, 1: PRIMARY}),
        (["al", "le"], {2: PRIMARY}),
    ],
)
def test_word_rejects_inconsistent_input(syllables, stress):
    with pytest.raises(LyricConsistencyError):
        Word(syllables, stress)


def test_word_is_immutable():
    with pytest.raises(AttributeError):
        Word(["al"]).syllables = ("le",)


# --- parse_lyrics ------------------------------------------------------------


def test_parse_lyrics_words_and_syllables():
    syllables = parse_lyrics("Al-le-lu-ia, sing to Je-sus")
    assert [s.text for s in syllables] == ["Al", "le", "lu", "ia,", "sing", "to", "Je", "sus"]
    assert [str(s) for s in syllables] == [
        "Al -", "- le -", "- lu -", "- ia,", "sing", "to", "Je -", "- sus",
    ]  # fmt: skip


def test_parse_lyrics_shares_one_word_object_per_word():
    syllables = parse_lyrics("Al-le-lu-ia sing")
    assert all(s.word is syllables[0].word for s in syllables[:4])
    assert syllables[4].word is not syllables[0].word
    assert [s.index for s in syllables] == [0, 1, 2, 3, 0]


@pytest.mark.parametrize(
    "text", ["Al-le-lu-ia", "Al- le- lu- ia", "Al-\nle-lu-\n  ia", "Al--le-lu-ia-"]
)
def test_parse_lyrics_hyphen_continuation_and_doubled_hyphens(text):
    syllables = parse_lyrics(text)
    assert [s.text for s in syllables] == ["Al", "le", "lu", "ia"]
    assert len({id(s.word) for s in syllables}) == 1


def test_parse_lyrics_stress_marks():
    syllables = parse_lyrics("Al-le-'lu-ia, sing to 'Je-sus")
    assert [s.text for s in syllables if s.lexical_stress is PRIMARY] == ["lu", "Je"]
    assert all(s.lexical_stress is None for s in parse_lyrics("'lu", primary=None))


def test_parse_lyrics_empty():
    assert parse_lyrics("") == []
    assert parse_lyrics("   \n ") == []


# --- LyricSyllable -----------------------------------------------------------


def test_syllable_placement_by_word_length():
    assert LyricSyllable(word=Word(["sing"])).placement is SyllablePlacement.WHOLE
    two = Word(["Je", "sus"])
    assert LyricSyllable(word=two, index=0).placement is SyllablePlacement.BEGINNING
    assert LyricSyllable(word=two, index=1).placement is SyllablePlacement.END
    four = Word(["Al", "le", "lu", "ia"])
    assert [LyricSyllable(word=four, index=i).placement for i in range(4)] == [
        SyllablePlacement.BEGINNING,
        SyllablePlacement.MIDDLE,
        SyllablePlacement.MIDDLE,
        SyllablePlacement.END,
    ]


def test_syllable_strings_with_custom_hyphen():
    four = Word(["Al", "le", "lu", "ia"])
    assert [LyricSyllable(word=four, index=i).syl_str("_") for i in range(4)] == [
        "Al _", "_ le _", "_ lu _", "_ ia",
    ]  # fmt: skip
    assert LyricSyllable(word=Word(["sing"])).syl_str("_") == "sing"


def test_syllable_lexical_stress_is_read_from_the_word():
    word = Word.from_string("al-le-'lu-ia")
    assert LyricSyllable(word=word, index=2).lexical_stress is PRIMARY
    assert LyricSyllable(word=word, index=0).lexical_stress is None


@pytest.mark.parametrize("index", [-1, 2, 10])
def test_syllable_index_must_be_in_range(index):
    with pytest.raises(LyricConsistencyError):
        LyricSyllable(word=Word(["Je", "sus"]), index=index)


def test_syllable_duration_defaults_to_none_and_accepts_a_duration():
    syllable = LyricSyllable(word=Word(["sing"]))
    assert syllable.duration is None
    syllable.duration = quarter
    assert syllable.duration == quarter
    assert repr(syllable) == "LyricSyllable('sing', duration=MetricalDuration(1, 4))"


def test_syllables_with_the_same_content_compare_equal_but_are_distinct():
    a, b = LyricSyllable(word=Word(["sing"])), LyricSyllable(word=Word(["sing"]))
    assert a == b
    assert a is not b
    assert a.id != b.id


# --- LyricSection ------------------------------------------------------------


def test_section_is_a_spanner_with_a_derived_name():
    section = LyricSection(section_type="verse", section_number=2, language="en")
    assert isinstance(section, Spanner)
    assert section.section_name == "verse 2"
    assert LyricSection(section_type="refrain").section_name == "refrain"
    assert LyricSection(section_number=2).section_name is None
    assert LyricSection(section_type="verse", section_name="Doxology").section_name == "Doxology"


# --- graph -------------------------------------------------------------------


@pytest.fixture
def graph_with_notes():
    graph = OmkGraph(GraphMeta())
    notes = [NoteEvent(tones={tone}) for tone in (C, D, E, F)]
    graph.add_line(notes)
    return graph, notes


def test_add_lyrics_from_string_builds_a_next_line(graph_with_notes):
    graph, _ = graph_with_notes
    syllables = graph.add_lyrics("Al-le-lu-ia")
    assert [graph.get_next(s) for s in syllables] == syllables[1:] + [None]
    assert graph.get_node(syllables[0].id) is syllables[0]


def test_add_lyrics_from_prebuilt_syllables(graph_with_notes):
    graph, _ = graph_with_notes
    syllables = parse_lyrics("A-men")
    assert graph.add_lyrics(syllables) == syllables
    assert graph.get_next(syllables[0]) is syllables[1]


def test_add_lyrics_after_appends_to_an_existing_line(graph_with_notes):
    graph, _ = graph_with_notes
    first = graph.add_lyrics("Al-le-lu-ia")
    second = graph.add_lyrics("A-men", after=first[-1])
    assert graph.get_next(first[-1]) is second[0]
    assert graph.get_previous(second[0]) is first[-1]


def test_add_lyrics_with_section_adds_spanner_edges(graph_with_notes):
    graph, _ = graph_with_notes
    verse = LyricSection(section_type="verse", section_number=1)
    syllables = graph.add_lyrics("Al-le-lu-ia", section=verse)
    assert graph.get_edge(verse, syllables[0], EdgeType.STARTS_AT).type is EdgeType.STARTS_AT
    assert graph.get_edge(verse, syllables[-1], EdgeType.ENDS_AT).type is EdgeType.ENDS_AT


def test_add_lyrics_empty(graph_with_notes):
    graph, _ = graph_with_notes
    assert graph.add_lyrics("") == []
    with pytest.raises(ValueError):
        graph.add_lyrics("", section=LyricSection(section_type="verse"))


def test_zip_and_unlink(graph_with_notes):
    graph, notes = graph_with_notes
    syllables = graph.add_lyrics("Al-le-lu-ia")
    graph.zip_lyrics_to_objects(syllables[0], notes[0])
    for note, syllable in zip(notes, syllables, strict=True):
        assert graph.get_edge(note, syllable, EdgeType.LYRIC).type is EdgeType.LYRIC

    graph.unlink_lyric_sequence(syllables[0], stop_syllable=syllables[2])
    assert list(graph.edges_between(notes[0], syllables[0], EdgeType.LYRIC)) == []
    assert list(graph.edges_between(notes[1], syllables[1], EdgeType.LYRIC)) == []
    assert len(list(graph.edges_between(notes[2], syllables[2], EdgeType.LYRIC))) == 1
    assert len(list(graph.edges_between(notes[3], syllables[3], EdgeType.LYRIC))) == 1


def test_unlink_stops_at_the_given_object_not_an_equal_one(graph_with_notes):
    graph, notes = graph_with_notes
    # "la la la la": every syllable has equal content, so `==` could not tell them apart.
    syllables = graph.add_lyrics("la la la la")
    assert syllables[0] == syllables[3]
    graph.zip_lyrics_to_objects(syllables[0], notes[0])

    graph.unlink_lyric_sequence(syllables[0], stop_syllable=syllables[3])
    assert all(
        list(graph.edges_between(n, s, EdgeType.LYRIC)) == []
        for n, s in zip(notes[:3], syllables[:3], strict=True)
    )
    assert len(list(graph.edges_between(notes[3], syllables[3], EdgeType.LYRIC))) == 1
