import pytest

from openmusickit.graph.edge import EdgeType
from openmusickit.graph.graph import GraphMeta, OmkGraph
from openmusickit.objects.marking import Marked, Marking, MarkSpanner
from openmusickit.objects.note_event import NoteEvent
from openmusickit.objects.omk_object import OmkObject, Spanner
from openmusickit.systems.wsmn.scoring import symbols
from openmusickit.systems.wsmn.scoring.symbols import crescendo, fermata, slur, staccato, tie
from openmusickit.systems.wsmn.tonal.symbols import C, D
from openmusickit.values.scoring.mark import AttachmentMode, Mark, MarkType


def test_marking_and_mark_spanner_are_marked_omk_objects():
    marking, spanner = Marking(mark=staccato), MarkSpanner(mark=slur)
    assert isinstance(marking, Marked) and isinstance(marking, OmkObject)
    assert isinstance(spanner, Marked) and isinstance(spanner, Spanner)
    assert not isinstance(marking, Spanner)
    assert marking.mark is staccato and spanner.mark is slur


def test_attachment_mode_is_checked_for_every_mark(mark_symbols):
    """A Marking takes any mark that can sit on a single event (SINGLE or
    EITHER), a MarkSpanner any mark that can span (SPAN or EITHER); the
    wrong placement is a ValueError, for all 238 marks in the table."""
    for name, mark in mark_symbols.items():
        assert mark.attachment_mode in (
            AttachmentMode.SINGLE,
            AttachmentMode.SPAN,
            AttachmentMode.EITHER,
        ), name
        if mark.attachment_mode is AttachmentMode.SPAN:
            with pytest.raises(ValueError):
                Marking(mark=mark)
        else:
            assert Marking(mark=mark).mark is mark, name
        if mark.attachment_mode is AttachmentMode.SINGLE:
            with pytest.raises(ValueError):
                MarkSpanner(mark=mark)
        else:
            assert MarkSpanner(mark=mark).mark is mark, name


def test_a_mark_with_no_attachment_mode_goes_both_ways():
    plain = Mark(name="plain")
    assert plain.attachment_mode is None
    assert Marking(mark=plain).mark is plain
    assert MarkSpanner(mark=plain).mark is plain


def test_mark_table_invariants(mark_symbols):
    """Every mark has a kind and an attachment mode; names are unique;
    aliases are unique across the table and never collide with a name;
    `binds` is only set on marks that can span."""
    names = [mark.name for mark in mark_symbols.values()]
    assert len(set(names)) == len(names) == 238
    aliases = [alias for mark in mark_symbols.values() for alias in mark.aliases]
    assert len(set(aliases)) == len(aliases)
    assert not set(aliases) & set(names)
    for name, mark in mark_symbols.items():
        assert isinstance(mark.kind, MarkType), name
        assert isinstance(mark.attachment_mode, AttachmentMode), name
        assert mark.name.strip() == mark.name and mark.name, name
        if mark.binds:
            assert mark.attachment_mode in (AttachmentMode.SPAN, AttachmentMode.EITHER), name


def test_equality_ignores_id_and_compares_the_mark():
    assert Marking(mark=staccato) == Marking(mark=staccato)
    assert Marking(mark=staccato) != Marking(mark=fermata)
    assert Marking(mark=staccato).id != Marking(mark=staccato).id


def test_repr_round_trips(mark_symbols):
    """Every ready-made mark, and the Marking or MarkSpanner holding it,
    evaluates back to an equal object; a mark made for one score prints
    only what it set."""
    namespace = {
        "Mark": Mark,
        "MarkType": MarkType,
        "AttachmentMode": AttachmentMode,
        "Marking": Marking,
        "MarkSpanner": MarkSpanner,
    }
    for name, mark in mark_symbols.items():
        assert eval(repr(mark), namespace) == mark, name
        if mark.attachment_mode is AttachmentMode.SPAN:
            holder = MarkSpanner(mark=mark)
        else:
            holder = Marking(mark=mark)
        assert eval(repr(holder), namespace) == holder, name
    assert repr(staccato) == (
        "Mark(name='staccato', description='A staccato dot: the note is played detached and shortened.', "
        "kind=MarkType.ARTICULATION, attachment_mode=AttachmentMode.SINGLE)"
    )
    minted = Mark(name="A", kind=MarkType.OTHER, attachment_mode=AttachmentMode.SINGLE)
    assert (
        repr(minted) == "Mark(name='A', kind=MarkType.OTHER, attachment_mode=AttachmentMode.SINGLE)"
    )
    assert eval(repr(minted), namespace) == minted
    assert repr(Marking(mark=Mark(name="dolce"))) == "Marking(mark=Mark(name='dolce'))"


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
