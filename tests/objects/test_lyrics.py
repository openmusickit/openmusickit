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

PRIMARY = LexicalStress.PRIMARY


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


# --- zip: melismas, rests, context events -------------------------------------


def _sung(graph, note):
    return [s.text for s in graph._graph.successors(note, LyricSyllable, EdgeType.LYRIC)]


def test_zip_skips_notes_inside_a_binding_span(graph_with_notes):
    from openmusickit.objects.marking import MarkSpanner
    from openmusickit.systems.wsmn.scoring.symbols import slur

    graph, notes = graph_with_notes
    graph.add_spanner(MarkSpanner(mark=slur), notes[1], notes[2])
    syllables = graph.add_lyrics("Al-le-lu-ia")
    graph.zip_lyrics_to_objects(syllables[0], notes[0])
    assert [_sung(graph, n) for n in notes] == [["Al"], ["le"], [], ["lu"]]
    assert list(graph._graph.predecessors(syllables[3], edge_type=EdgeType.LYRIC)) == []


def test_zip_ties_bind_but_hairpins_and_phrase_marks_do_not(graph_with_notes):
    from openmusickit.objects.marking import MarkSpanner
    from openmusickit.systems.wsmn.scoring.symbols import crescendo, phrase_mark, tie

    graph, notes = graph_with_notes
    graph.add_spanner(MarkSpanner(mark=crescendo), notes[0], notes[3])
    graph.add_spanner(MarkSpanner(mark=phrase_mark), notes[0], notes[3])
    graph.add_spanner(MarkSpanner(mark=tie), notes[2], notes[3])
    syllables = graph.add_lyrics("Al-le-lu-ia")
    graph.zip_lyrics_to_objects(syllables[0], notes[0])
    assert [_sung(graph, n) for n in notes] == [["Al"], ["le"], ["lu"], []]


def test_zip_skips_rests_and_context_events():
    from openmusickit.objects.context_event import ModalContextEvent
    from openmusickit.objects.note_event import Rest

    graph = OmkGraph(GraphMeta())
    key, c, rest, d = ModalContextEvent(), NoteEvent(tones={C}), Rest(None), NoteEvent(tones={D})
    graph.add_line([key, c, rest, d])
    syllables = graph.add_lyrics("Je-sus")
    graph.zip_lyrics_to_objects(syllables[0], key)
    assert _sung(graph, key) == [] and _sung(graph, rest) == []
    assert _sung(graph, c) == ["Je"] and _sung(graph, d) == ["sus"]


def test_zip_a_span_ending_where_another_starts_continues(graph_with_notes):
    from openmusickit.objects.marking import MarkSpanner
    from openmusickit.systems.wsmn.scoring.symbols import slur

    graph, notes = graph_with_notes
    graph.add_spanner(MarkSpanner(mark=slur), notes[0], notes[1])
    graph.add_spanner(MarkSpanner(mark=slur), notes[1], notes[3])
    syllables = graph.add_lyrics("Al-le-lu-ia")
    graph.zip_lyrics_to_objects(syllables[0], notes[0])
    # notes[1] ends the first slur, so it is inside it; the second slur then has no onset of its own
    assert [_sung(graph, n) for n in notes] == [["Al"], [], ["le"], ["lu"]]


def test_zip_stops_when_syllables_run_out(graph_with_notes):
    graph, notes = graph_with_notes
    syllables = graph.add_lyrics("A-men")
    graph.zip_lyrics_to_objects(syllables[0], notes[0])
    assert [_sung(graph, n) for n in notes] == [["A"], ["men"], [], []]
