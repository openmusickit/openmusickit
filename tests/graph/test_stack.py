"""Stacks: the order in which things are drawn one above another (STACKS_ABOVE),
and the StackGroups that span runs of it. See _plans/stack-order.md.

Run with `uv run pytest --hypothesis-profile=thorough` for 2,000 examples per
property.
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from openmusickit.errors import GraphError
from openmusickit.graph.edge import EdgeType
from openmusickit.graph.graph import GraphMeta, OmkGraph
from openmusickit.objects.part import LineGroup, Part, PercussionPart, StackGroup, Stint
from openmusickit.objects.score import Score
from openmusickit.objects.sync_line import SyncLine
from openmusickit.systems.wsmn.scoring.symbols import brace, bracket
from openmusickit.systems.wsmn.temporal.wsmn import WSMN_TEMPORAL
from openmusickit.systems.wsmn.tonal.symbols import C, D, E, F, G
from tests.graph.helpers import notes


def parts(*names: str) -> list[Part]:
    return [Part(name=name) for name in names]


def stacked_names(graph: OmkGraph, top) -> list[str]:
    return [member.name for member in graph.walk_stack(top)]


def stacked_names_of_group(graph: OmkGraph, group: StackGroup) -> list[str]:
    return [member.name for member in graph.stack_group_members(group)]


def group_ids(graph: OmkGraph, node) -> set:
    return {group.id for group in graph.stack_groups_of(node)}


@pytest.fixture
def quartet():
    graph = OmkGraph(GraphMeta())
    members = parts("Violin 1", "Violin 2", "Viola", "Cello")
    graph.add_stack(members)
    return graph, members


# The shape of a stack


def test_a_stack_reads_top_to_bottom_in_both_directions(quartet):
    graph, (v1, v2, va, vc) = quartet
    assert stacked_names(graph, v1) == ["Violin 1", "Violin 2", "Viola", "Cello"]
    assert stacked_names(graph, va) == ["Viola", "Cello"]
    assert graph.stacked_above(v1) is None and graph.stacked_below(vc) is None
    assert graph.stacked_above(va) is v2 and graph.stacked_below(va) is vc


def test_every_kind_of_stackable_thing_stacks_with_every_other():
    graph = OmkGraph(GraphMeta())
    chords, melody = notes(C, D), notes(E, F)
    graph.add_line(chords)
    graph.add_line(melody)
    bars = SyncLine(temporal_system=WSMN_TEMPORAL, name="bars")
    piano_lines = LineGroup(name="Piano")
    snare = PercussionPart(name="Snare")
    members = [chords[0], melody[0], Part(name="Flute"), piano_lines, snare, bars]
    graph.add_stack(members)
    assert list(graph.walk_stack(chords[0])) == members


def test_one_member_stack_adds_the_node_and_no_edge():
    graph = OmkGraph(GraphMeta())
    (flute,) = parts("Flute")
    graph.add_stack([flute])
    assert graph.get_node(flute.id) is flute
    assert list(graph.walk_stack(flute)) == [flute]


def test_an_order_partly_known_is_several_stacks():
    graph = OmkGraph(GraphMeta())
    flute, oboe, violin, viola, harp = parts("Flute", "Oboe", "Violin", "Viola", "Harp")
    graph.add_stack([flute, oboe])
    graph.add_stack([violin, viola])
    graph.add_node(harp)
    assert stacked_names(graph, flute) == ["Flute", "Oboe"]
    assert stacked_names(graph, violin) == ["Violin", "Viola"]
    assert graph.stacked_above(harp) is None and graph.stacked_below(harp) is None


def test_a_stack_says_nothing_about_time():
    graph = OmkGraph(GraphMeta())
    upper, lower = notes(C, D), notes(E, F)
    graph.add_line(upper)
    graph.add_line(lower)
    graph.add_stack([upper[0], lower[0]])
    with pytest.raises(GraphError, match="No timing path"):
        graph.relative_onset(upper[0], lower[0])


# What a stack refuses


def test_a_node_has_one_thing_directly_below_and_one_directly_above(quartet):
    graph, (v1, v2, va, vc) = quartet
    (harp,) = parts("Harp")
    with pytest.raises(GraphError, match="already has something stacked below"):
        graph.add_stacked(v1, harp)
    with pytest.raises(GraphError, match="already has something stacked above"):
        graph.add_stacked(harp, v2)


def test_a_stack_has_no_cycles(quartet):
    graph, (v1, _, _, vc) = quartet
    with pytest.raises(GraphError, match="would close a cycle"):
        graph.add_stacked(vc, v1)
    (harp,) = parts("Harp")
    with pytest.raises(GraphError, match="would close a cycle"):
        graph.add_stacked(harp, harp)


def test_a_line_stacks_by_its_head_and_a_branch_through_its_parent():
    graph = OmkGraph(GraphMeta())
    line, second_voice = notes(C, D, E), notes(G)
    graph.add_line(line)
    graph.add_line(second_voice)
    graph.add_branch(line[1], second_voice[0])
    (flute,) = parts("Flute")
    with pytest.raises(GraphError, match="not the head of a line"):
        graph.add_stacked(flute, line[1])
    with pytest.raises(GraphError, match="stacked through its parent"):
        graph.add_stacked(flute, second_voice[0])


@pytest.mark.parametrize(
    "thing", [Score(title="Not stacked"), Stint(), StackGroup(name="Not stacked")]
)
def test_only_parts_groups_line_heads_and_sync_lines_stack(thing):
    graph = OmkGraph(GraphMeta())
    (flute,) = parts("Flute")
    with pytest.raises(GraphError, match="does not stack"):
        graph.add_stacked(flute, thing)
    with pytest.raises(GraphError, match="does not stack"):
        graph.add_stacked(thing, flute)


# Inserting and removing


def test_insert_puts_a_node_between_two_neighbours(quartet):
    graph, (v1, v2, va, vc) = quartet
    (harp,) = parts("Harp")
    graph.insert_stacked(harp, v2, va)
    assert stacked_names(graph, v1) == ["Violin 1", "Violin 2", "Harp", "Viola", "Cello"]


def test_insert_needs_direct_neighbours_and_an_unstacked_node(quartet):
    graph, (v1, v2, va, vc) = quartet
    (harp,) = parts("Harp")
    with pytest.raises(GraphError):
        graph.insert_stacked(harp, v1, va)
    with pytest.raises(GraphError, match="already in a stack"):
        graph.insert_stacked(vc, v1, v2)
    assert stacked_names(graph, v1) == ["Violin 1", "Violin 2", "Viola", "Cello"]


@pytest.mark.parametrize(
    ("removed", "left"),
    [
        (0, ["Violin 2", "Viola", "Cello"]),
        (1, ["Violin 1", "Viola", "Cello"]),
        (3, ["Violin 1", "Violin 2", "Viola"]),
    ],
)
def test_removing_splices_the_neighbours_together(quartet, removed, left):
    graph, members = quartet
    gone = members[removed]
    graph.remove_from_stack(gone)
    top = members[1] if removed == 0 else members[0]
    assert stacked_names(graph, top) == left
    assert graph.get_node(gone.id) is gone
    assert graph.stacked_above(gone) is None and graph.stacked_below(gone) is None


def test_removing_an_unstacked_node_changes_nothing():
    graph = OmkGraph(GraphMeta())
    (harp,) = parts("Harp")
    graph.add_node(harp)
    graph.remove_from_stack(harp)
    assert graph.get_node(harp.id) is harp


def test_removing_an_end_member_moves_the_group_inward(quartet):
    graph, (v1, v2, va, vc) = quartet
    strings = StackGroup(name="Strings", shape=bracket)
    graph.add_stack_group(strings, v1, vc)
    graph.remove_from_stack(v1)
    assert stacked_names_of_group(graph, strings) == ["Violin 2", "Viola", "Cello"]
    graph.remove_from_stack(vc)
    assert stacked_names_of_group(graph, strings) == ["Violin 2", "Viola"]


def test_removing_an_inner_member_leaves_the_group_ends(quartet):
    graph, (v1, v2, va, vc) = quartet
    strings = StackGroup(name="Strings")
    graph.add_stack_group(strings, v1, vc)
    graph.remove_from_stack(va)
    assert stacked_names_of_group(graph, strings) == ["Violin 1", "Violin 2", "Cello"]


def test_removing_a_group_s_only_member_removes_the_group(quartet):
    graph, (_, v2, _, _) = quartet
    solo = StackGroup(name="Solo")
    graph.add_stack_group(solo, v2, v2)
    graph.remove_from_stack(v2)
    assert graph.get_node(solo.id) is None


# Stack groups


def test_groups_nest_and_overlap(quartet):
    graph, (v1, v2, va, vc) = quartet
    strings, violins = StackGroup(name="Strings", shape=bracket), StackGroup(shape=brace)
    middle = StackGroup(name="Middle")
    graph.add_stack_group(strings, v1, vc)
    graph.add_stack_group(violins, v1, v2)
    graph.add_stack_group(middle, v2, va)  # overlaps `violins` without nesting
    assert stacked_names_of_group(graph, violins) == ["Violin 1", "Violin 2"]
    assert stacked_names_of_group(graph, middle) == ["Violin 2", "Viola"]
    assert group_ids(graph, v1) == {strings.id, violins.id}
    assert group_ids(graph, v2) == {strings.id, violins.id, middle.id}
    assert group_ids(graph, vc) == {strings.id}


def test_a_group_may_be_one_member(quartet):
    graph, (_, _, va, _) = quartet
    solo = StackGroup()
    graph.add_stack_group(solo, va, va)
    assert list(graph.stack_group_members(solo)) == [va]


def test_a_group_runs_downward_within_one_stack(quartet):
    graph, (v1, _, _, vc) = quartet
    with pytest.raises(GraphError, match="not at or below"):
        graph.add_stack_group(StackGroup(), vc, v1)
    flute, oboe = parts("Flute", "Oboe")
    graph.add_stack([flute, oboe])
    with pytest.raises(GraphError, match="not at or below"):
        graph.add_stack_group(StackGroup(), flute, vc)


def test_a_group_starts_at_something_that_stacks():
    graph = OmkGraph(GraphMeta())
    line = notes(C, D)
    graph.add_line(line)
    with pytest.raises(GraphError, match="not the head of a line"):
        graph.add_stack_group(StackGroup(), line[1], line[1])


def test_a_group_over_a_line_head_is_not_copied_when_the_line_is_forked():
    graph = OmkGraph(GraphMeta())
    line = notes(C, D)
    graph.add_line(line)
    flute, oboe = parts("Flute", "Oboe")
    graph.add_stint(flute, Stint(), line[0])
    oboe_stint = Stint()
    graph.add_stint(oboe, oboe_stint, line[0])
    group = StackGroup(name="Over the line")
    graph.add_stack_group(group, line[0], line[0])
    copy = graph.materialize(oboe_stint)
    assert list(graph._graph.predecessors(copy, StackGroup, EdgeType.STARTS_AT)) == []
    assert list(graph.stack_group_members(group)) == [line[0]]


# Against a model: random edits keep the stack a set of chains


POOL = 6

operations = st.lists(
    st.tuples(
        st.sampled_from(["stack", "insert", "remove", "group"]),
        st.integers(0, POOL - 1),
        st.integers(0, POOL - 1),
        st.integers(0, POOL - 1),
    ),
    max_size=30,
)


class Model:
    """Stacks as two neighbour maps, and groups as [first, last] by index."""

    def __init__(self):
        self.below: dict[int, int] = {}
        self.above: dict[int, int] = {}
        self.groups: dict[int, list[int]] = {}  # group number -> [first, last]

    def walk(self, i: int) -> list[int]:
        run = [i]
        while run[-1] in self.below:
            run.append(self.below[run[-1]])
        return run

    def stack(self, i: int, j: int) -> bool:
        if i in self.below or j in self.above or i in self.walk(j):
            return False
        self.below[i], self.above[j] = j, i
        return True

    def remove(self, k: int) -> None:
        upper, lower = self.above.pop(k, None), self.below.pop(k, None)
        for number, (first, last) in list(self.groups.items()):
            if first == k and last == k:
                del self.groups[number]
                continue
            if first == k:
                self.groups[number][0] = lower
            if last == k:
                self.groups[number][1] = upper
        if upper is not None:
            del self.below[upper]
        if lower is not None:
            del self.above[lower]
        if upper is not None and lower is not None:
            self.below[upper], self.above[lower] = lower, upper

    def members(self, number: int) -> list[int]:
        first, last = self.groups[number]
        run = self.walk(first)
        return run[: run.index(last) + 1]


@given(operations)
def test_random_edits_agree_with_a_model_of_chains(steps):
    graph = OmkGraph(GraphMeta())
    pool = parts(*(f"P{i}" for i in range(POOL)))
    for part in pool:
        graph.add_node(part)
    model = Model()
    groups: dict[int, StackGroup] = {}

    for op, i, j, k in steps:
        if op == "stack":
            expected = model.stack(i, j)
            if expected:
                graph.add_stacked(pool[i], pool[j])
            else:
                with pytest.raises(GraphError):
                    graph.add_stacked(pool[i], pool[j])
        elif op == "insert":
            if i in model.below and k not in model.below and k not in model.above:
                j = model.below[i]
                graph.insert_stacked(pool[k], pool[i], pool[j])
                del model.below[i], model.above[j]
                model.below[i], model.above[k] = k, i
                model.below[k], model.above[j] = j, k
        elif op == "remove":
            graph.remove_from_stack(pool[k])
            model.remove(k)
        elif op == "group":
            if j in model.walk(i):
                number = len(groups)
                groups[number] = StackGroup(name=f"G{number}")
                graph.add_stack_group(groups[number], pool[i], pool[j])
                model.groups[number] = [i, j]
            else:
                with pytest.raises(GraphError):
                    graph.add_stack_group(StackGroup(), pool[i], pool[j])

        for index, part in enumerate(pool):
            below = model.below.get(index)
            above = model.above.get(index)
            assert graph.stacked_below(part) is (None if below is None else pool[below])
            assert graph.stacked_above(part) is (None if above is None else pool[above])
        for number, group in groups.items():
            if number in model.groups:
                assert list(graph.stack_group_members(group)) == [
                    pool[m] for m in model.members(number)
                ]
            else:
                assert graph.get_node(group.id) is None
        for index, part in enumerate(pool):
            expected_groups = {
                groups[number].id for number in model.groups if index in model.members(number)
            }
            assert group_ids(graph, part) == expected_groups
