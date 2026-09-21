"""Properties of typed lyrics: `parse_lyrics` reads back exactly the
syllables typed, with their stress and placement, for any valid text; any
text at all either parses or raises `LyricConsistencyError`; and a lyric
line zips onto a plain line of notes one syllable per note and unzips
back to where it was.
"""

from hypothesis import assume, given
from hypothesis import strategies as st

from openmusickit.errors import LyricConsistencyError
from openmusickit.graph.edge import EdgeType
from openmusickit.graph.graph import GraphMeta, OmkGraph
from openmusickit.objects.lyrics import LyricSyllable, SyllablePlacement, parse_lyrics
from openmusickit.values.text.word import LexicalStress, Word
from tests.graph.helpers import snapshot
from tests.strategies import lines, lyric_texts


def _typed_words(text: str) -> list[list[str]]:
    """The syllables as typed, word by word, marks and all: the strategy
    never ends a token in a hyphen, so whitespace separates words."""
    return [token.split("-") for token in text.split()]


def _unmarked(piece: str) -> str:
    return piece[1:] if piece[:1] in ("'", ",") else piece


@given(lyric_texts())
def test_parse_lyrics_reads_back_the_typed_syllables(text):
    syllables = parse_lyrics(text)
    typed = _typed_words(text)
    assert [s.text for s in syllables] == [_unmarked(p) for word in typed for p in word]
    assert sum(len(word) for word in typed) == len(syllables)

    at = 0
    for word in typed:
        these = syllables[at : at + len(word)]
        at += len(word)
        assert all(s.word is these[0].word for s in these)
        assert [s.index for s in these] == list(range(len(word)))
        assert str(these[0].word) == "".join(_unmarked(p) for p in word)
        for piece, syllable in zip(word, these, strict=True):
            if piece.startswith("'"):
                assert syllable.lexical_stress is LexicalStress.PRIMARY
            elif piece.startswith(","):
                assert syllable.lexical_stress is LexicalStress.SECONDARY
            else:
                assert syllable.lexical_stress is None
        if len(word) == 1:
            assert these[0].placement is SyllablePlacement.WHOLE
        else:
            assert these[0].placement is SyllablePlacement.BEGINNING
            assert these[-1].placement is SyllablePlacement.END
            assert all(s.placement is SyllablePlacement.MIDDLE for s in these[1:-1])


@given(st.text(max_size=24))
def test_parse_lyrics_only_ever_raises_lyric_consistency_error(text):
    try:
        syllables = parse_lyrics(text)
    except LyricConsistencyError as error:
        assert isinstance(error, ValueError)
        return
    assert all(isinstance(s, LyricSyllable) for s in syllables)


@given(st.text(max_size=16))
def test_word_from_string_only_ever_raises_lyric_consistency_error(text):
    try:
        word = Word.from_string(text)
    except LyricConsistencyError:
        return
    assert isinstance(word, Word) and len(word) >= 1
    assert Word.from_string("-".join(word), primary=None, secondary=None) == Word(list(word))


@given(lyric_texts(), lines(min_size=1, max_size=8))
def test_lyrics_zip_onto_a_plain_line_and_unzip(text, line):
    """On a line with no rests, graces or slurs, every note begins the next
    syllable until one line runs out; unlinking restores the graph."""
    syllables = parse_lyrics(text)
    assume(syllables)
    graph = OmkGraph(GraphMeta())
    graph.add_line(line)
    added = graph.add_lyrics(syllables)
    assert added == syllables
    assert [graph.get_next(s) for s in syllables] == syllables[1:] + [None]
    before = snapshot(graph)

    graph.zip_lyrics_to_objects(syllables[0], line[0])
    sung = min(len(line), len(syllables))
    for note, syllable in zip(line[:sung], syllables[:sung], strict=True):
        assert graph.get_edge(note, syllable, EdgeType.LYRIC).type is EdgeType.LYRIC
    assert len(list(graph.edges(EdgeType.LYRIC))) == sung

    graph.unlink_lyric_sequence(syllables[0])
    assert snapshot(graph) == before
