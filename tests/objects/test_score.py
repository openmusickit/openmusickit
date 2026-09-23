import copy

from openmusickit.objects.omk_object import OmkObject, SequentialEvent
from openmusickit.objects.score import Score

FIELDS = (
    "title",
    "subtitle",
    "composer",
    "lyricist",
    "arranger",
    "copyright",
    "opus",
    "dedication",
)


def test_fields_default_to_none():
    score = Score()
    assert all(getattr(score, name) is None for name in FIELDS)
    assert isinstance(score, OmkObject) and not isinstance(score, SequentialEvent)


def test_equality_ignores_id_and_compares_the_content():
    assert Score(title="A") == Score(title="A")
    assert Score(title="A") != Score(title="B")
    assert Score() == Score() and Score() != Score(composer="Anon.")
    assert Score(title="A").id != Score(title="A").id


def test_repr_round_trips():
    full = Score(**{name: name.upper() for name in FIELDS})
    for score in (Score(), Score(title="A"), full):
        assert eval(repr(score), {"Score": Score}) == score


def test_survives_deepcopy():
    score = Score(title="A", lyricist="B")
    twin = copy.deepcopy(score)
    assert twin == score and twin is not score
