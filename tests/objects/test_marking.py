import pytest

from openmusickit.graph.edge import EdgeType
from openmusickit.graph.graph import GraphMeta, OmkGraph
from openmusickit.objects.marking import Marked, Marking, MarkSpanner
from openmusickit.objects.note_event import NoteEvent
from openmusickit.objects.omk_object import OmkObject, Spanner
from openmusickit.systems.wsmn.scoring import symbols
from openmusickit.systems.wsmn.scoring.symbols import crescendo, fermata, slur, staccato, tie
from openmusickit.systems.wsmn.tonal.symbols import C, D
from openmusickit.values.scoring.mark import AttachmentMode, Mark


def test_marking_and_mark_spanner_are_marked_omk_objects():
    marking, spanner = Marking(mark=staccato), MarkSpanner(mark=slur)
    assert isinstance(marking, Marked) and isinstance(marking, OmkObject)
    assert isinstance(spanner, Marked) and isinstance(spanner, Spanner)
    assert not isinstance(marking, Spanner)
    assert marking.mark is staccato and spanner.mark is slur


def test_attachment_mode_is_checked():
    with pytest.raises(ValueError):
        Marking(mark=slur)
    with pytest.raises(ValueError):
        MarkSpanner(mark=staccato)
    # EITHER and unspecified go both ways
    assert crescendo.attachment_mode is AttachmentMode.EITHER
    Marking(mark=crescendo)
    MarkSpanner(mark=crescendo)
    plain = Mark(name="plain")
    Marking(mark=plain)
    MarkSpanner(mark=plain)


def test_equality_ignores_id_and_compares_the_mark():
    assert Marking(mark=staccato) == Marking(mark=staccato)
    assert Marking(mark=staccato) != Marking(mark=fermata)
    assert Marking(mark=staccato).id != Marking(mark=staccato).id


def test_repr_is_compact():
    assert repr(Marking(mark=staccato)) == "Marking(mark=Mark(name='staccato', ...))"
    assert repr(MarkSpanner(mark=slur)) == "MarkSpanner(mark=Mark(name='slur', ...))"


def test_only_slur_and_tie_bind():
    marks = {name: m for name, m in vars(symbols).items() if isinstance(m, Mark)}
    assert {name for name, m in marks.items() if m.binds} == {"slur", "tie"}
    assert slur.binds and tie.binds and not crescendo.binds
    assert Mark(name="x").binds is False


def test_marks_attach_through_the_graph():
    graph = OmkGraph(GraphMeta())
    c, d = NoteEvent(tones={C}), NoteEvent(tones={D})
    graph.add_line([c, d])
    dot, arc = Marking(mark=staccato), MarkSpanner(mark=slur)
    graph.add_articulation(dot, c)
    graph.add_spanner(arc, c, d)
    assert graph.get_edge(dot, c, EdgeType.MARKS).type is EdgeType.MARKS
    assert graph.get_edge(arc, c, EdgeType.STARTS_AT).type is EdgeType.STARTS_AT
    assert graph.get_edge(arc, d, EdgeType.ENDS_AT).type is EdgeType.ENDS_AT
