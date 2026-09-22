"""Groups: lines that are their own things done together (the drums of a
kit, the hands of a pianist), measured from the group's origin, with a Part
per line or one Part for the group. See _plans/percussion.md."""

import warnings

import pytest

from openmusickit.errors import GraphError, OmkWarning
from openmusickit.graph.edge import Contains, EdgeType
from openmusickit.graph.graph import GraphMeta, OmkGraph
from openmusickit.objects.note_event import NoteEvent, Rest
from openmusickit.objects.part import LineGroup, Part, PercussionPart, Stint
from openmusickit.systems.wsmn.percussion.percussion_tone import PercussionTone, Stroke
from openmusickit.systems.wsmn.temporal.symbols import eighth, half, quarter, whole
from openmusickit.systems.wsmn.tonal.symbols import M2, A, B, C, D, E, F, G
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from openmusickit.values.time.duration import ZeroDuration
from openmusickit.values.tone.tone_collection import ToneCollection
from tests.graph.helpers import names, notes, snapshot

HIT = PercussionTone()
CLOSED = PercussionTone(stroke=Stroke.CLOSED)
OPEN = PercussionTone(stroke=Stroke.OPEN)


def hits(*tones, duration=quarter) -> list[NoteEvent]:
    return [Rest(duration) if t is None else NoteEvent(tones={t}, duration=duration) for t in tones]


@pytest.fixture
def kit():
    """One bar of rock: eight closed hi-hats, snare on 2 and 4, kick on 1
    and 3; three lines in a group, a PercussionPart with a stint on each."""
    graph = OmkGraph(GraphMeta())
    hh = hits(*[CLOSED] * 8, duration=eighth)
    sn = hits(None, HIT, None, HIT)
    bd = hits(HIT, None, HIT, None)
    for line in (hh, sn, bd):
        graph.add_line(line)
    group = LineGroup(name="Drum kit")
    graph.add_group(group, [hh[0], sn[0], bd[0]])
    parts = {
        "hi-hat": PercussionPart(name="Hi-hat"),
        "snare": PercussionPart(name="Snare"),
        "kick": PercussionPart(name="Kick"),
    }
    graph.add_stint(parts["hi-hat"], Stint(), hh[0])
    graph.add_stint(parts["snare"], Stint(), sn[0])
    graph.add_stint(parts["kick"], Stint(), bd[0])
    return graph, group, hh, sn, bd, parts


# --- a kit: one line per drum, aligned through the group ------------------------


def test_lines_of_a_group_are_timed_from_its_origin(kit):
    graph, group, hh, sn, bd, parts = kit
    assert graph.relative_onset(hh[0], sn[1]) == quarter
    assert graph.relative_onset(sn[1], bd[2]) == quarter
    assert graph.relative_onset(bd[2], hh[7]) == quarter + eighth
    assert graph.relative_onset(hh[3], sn[0]) == -(quarter + eighth)


def test_group_members_and_groups_of(kit):
    graph, group, hh, sn, bd, parts = kit
    assert {m.id for m in graph.group_members(group)} == {hh[0].id, sn[0].id, bd[0].id}
    assert list(graph.groups_of(sn[0])) == [group]
    assert list(graph.groups_of(sn[1])) == []


def test_walk_group_covers_every_line_and_walk_stint_covers_one(kit):
    graph, group, hh, sn, bd, parts = kit
    walked = list(graph.walk_group(group))
    assert len(walked) == 16
    assert {e.id for e in walked} == {e.id for e in hh + sn + bd}
    (snare_stint,) = graph.stints(parts["snare"])
    assert list(graph.walk_stint(snare_stint)) == sn
    assert list(graph.walk_span(hh[0])) == hh  # a group is not a branch


def test_a_remap_over_the_group_revoices_the_kit(kit):
    graph, group, hh, sn, bd, parts = kit
    for head in graph.group_members(group):
        graph.transform_tones(head, None, lambda t: OPEN if t == CLOSED else t)
    assert all(e.tones == {OPEN} for e in hh)
    assert sn[1].tones == {HIT} and sn[0].is_rest


def test_a_second_voice_on_one_drum_is_a_branch_and_stays_with_its_part(kit):
    graph, group, hh, sn, bd, parts = kit
    fill = hits(HIT, HIT, duration=eighth)
    graph.add_line(fill)
    graph.add_branch(sn[3], fill[0])
    (snare_stint,) = graph.stints(parts["snare"])
    assert list(graph.walk_stint(snare_stint)) == sn + fill
    assert graph.relative_onset(hh[0], fill[1]) == half + quarter + eighth
    with pytest.raises(GraphError):
        graph.add_to_group(group, fill[0])  # in the group already, through the snare line


# --- a piano: one Part for the whole group ------------------------------------------


def test_one_part_may_play_every_line_of_a_group():
    graph = OmkGraph(GraphMeta())
    rh, lh = notes(C, D, E, F), notes(G, A, duration=half)
    graph.add_line(rh)
    graph.add_line(lh)
    hands = LineGroup(name="Piano")
    graph.add_group(hands, [rh[0], lh[0]])
    piano = Part(name="Piano")
    graph.add_performs(piano, hands)
    assert list(graph.groups(piano)) == [hands]
    assert list(graph.stints(piano)) == []
    assert graph.get_edge(piano, hands, EdgeType.PERFORMS).type is EdgeType.PERFORMS


def test_a_line_may_enter_after_the_origin():
    graph = OmkGraph(GraphMeta())
    tune, late = notes(C, D, E, F), notes(G, A)
    graph.add_line(tune)
    graph.add_line(late)
    group = LineGroup()
    graph.add_group(group, [tune[0]])
    graph.add_to_group(group, late[0], displacement=whole)
    assert graph.relative_onset(tune[0], late[0]) == whole
    assert graph.relative_onset(late[1], tune[1]) == -whole
    edge = graph.get_edge(group, late[0], EdgeType.CONTAINS)
    assert isinstance(edge, Contains) and edge.displacement == whole


def test_a_pin_that_disagrees_with_the_group_is_reported(kit):
    graph, group, hh, sn, bd, parts = kit
    graph.add_simultaneous(hh[0], bd[0])  # agrees with the group
    with warnings.catch_warnings():
        warnings.simplefilter("error", OmkWarning)
        assert graph.check_alignment() == []
    graph.add_simultaneous(hh[1], sn[0])  # an eighth in, but the group says the origin
    with pytest.warns(OmkWarning, match="pinned .* but lies"):
        (conflict,) = graph.check_alignment()
    assert conflict is graph.get_edge(hh[1], sn[0], EdgeType.SIMULTANEOUS)


# --- what a member must be ---------------------------------------------------------


def test_a_member_is_a_head_that_is_not_branched():
    graph = OmkGraph(GraphMeta())
    c, d = notes(C, D)
    a, b = notes(A, B)
    graph.add_line([c, d])
    graph.add_line([a, b])
    group = LineGroup()
    with pytest.raises(GraphError):
        graph.add_group(group, [d])  # d has a NEXT in
    graph.add_branch(c, a)
    with pytest.raises(GraphError):
        graph.add_to_group(group, a)  # a is a voice of c's line
    graph.add_to_group(group, c)
    with pytest.raises(GraphError):
        graph.add_to_group(group, c)  # once per group
    # the group is a node of the timing graph: its origin is where c starts,
    # a hangs from c's onset, d is a quarter along
    assert graph.relative_onset(group, a) == ZeroDuration()
    assert graph.relative_onset(group, d) == quarter


def test_the_group_is_a_local_origin_not_a_score_root():
    graph = OmkGraph(GraphMeta())
    c, d = notes(C, D)
    e, f = notes(E, F)
    graph.add_line([c, d])
    graph.add_line([e, f])
    graph.add_group(LineGroup(), [c])
    graph.add_group(LineGroup(), [e])
    with pytest.raises(GraphError):
        graph.relative_onset(c, e)  # two groups, no relation between them


def test_removing_the_group_frees_its_lines():
    graph = OmkGraph(GraphMeta())
    c, d = notes(C, D)
    e, f = notes(E, F)
    graph.add_line([c, d])
    graph.add_line([e, f])
    before = snapshot(graph)
    group = LineGroup()
    graph.add_group(group, [c, e])
    assert graph.relative_onset(c, f) == quarter
    graph.remove_node(group)
    assert snapshot(graph) == before
    with pytest.raises(GraphError):
        graph.relative_onset(c, f)
    graph.add_branch(c, e)  # free to be branched again


def test_materialize_does_not_copy_group_membership():
    graph = OmkGraph(GraphMeta())
    flute_line, lh = notes(C, D, E, F), notes(G, A, duration=half)
    graph.add_line(flute_line)
    graph.add_line(lh)
    group = LineGroup()
    graph.add_group(group, [flute_line[0], lh[0]])
    flute, piccolo = Part(name="Flute"), Part(name="Piccolo")
    graph.add_stint(flute, Stint(), flute_line[0])
    piccolo_stint = Stint(transposition=TonalVector((0, 0, 1)))
    graph.add_stint(piccolo, piccolo_stint, flute_line[0], flute_line[1])
    head = graph.materialize(piccolo_stint)
    assert list(graph.groups_of(head)) == []
    assert list(graph.groups_of(flute_line[0])) == [group]
    assert names(graph.walk_stint(piccolo_stint)) == ["C", "D"]
    graph.transform_tones(head, None, TonalVector.transpose, M2)
    assert names(flute_line) == ["C", "D", "E", "F"]


# --- PercussionPart ------------------------------------------------------------------


def test_percussion_part_carries_an_optional_palette():
    snare = PercussionPart(name="Snare")
    assert snare.palette is None
    assert isinstance(snare, Part)
    palette = ToneCollection([HIT, PercussionTone(stroke=Stroke.RIM_SHOT)], name="snare drum")
    snare = PercussionPart(name="Snare", palette=palette)
    assert snare.palette is palette
    assert HIT in snare.palette
    assert snare == PercussionPart(name="Snare", palette=palette)  # by content, not id
    assert snare != PercussionPart(name="Snare")
