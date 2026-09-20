"""Compound lines: branches (same performer), pins (independent lines),
parts and stints (who performs what), grace notes (zero width).
See _plans/compound-lines.md."""

import warnings

import pytest

from openmusickit.errors import GraphError, OmkWarning
from openmusickit.graph.edge import EdgeType, Next, TimingAnchor
from openmusickit.graph.graph import GraphMeta, OmkGraph
from openmusickit.objects.chord_event import ChordEvent
from openmusickit.objects.lyrics import LyricSection, LyricSyllable
from openmusickit.objects.marking import Marking, MarkSpanner
from openmusickit.objects.note_event import NoteEvent
from openmusickit.objects.part import Part, Stint
from openmusickit.systems.wsmn.scoring.symbols import crescendo, slur, staccato
from openmusickit.systems.wsmn.temporal.symbols import (
    eighth,
    grace_eighth,
    grace_sixteenth,
    half,
    quarter,
    whole,
)
from openmusickit.systems.wsmn.tonal.symbols import M2, A, B, C, D, E, F, G, maj
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from openmusickit.values.time.duration import GraceDuration, ZeroDuration


def notes(*tones, duration=quarter):
    return [NoteEvent(tones={t}, duration=duration) for t in tones]


def names(events):
    return [format(next(iter(n.tones)), "ascii") for n in events]


# --- NEXT is a chain -----------------------------------------------------------


def test_add_next_refuses_a_second_outgoing_or_incoming_next():
    graph = OmkGraph(GraphMeta())
    c, d, e = notes(C, D, E)
    graph.add_line([c, d])
    with pytest.raises(GraphError):
        graph.add_next(c, e)
    with pytest.raises(GraphError):
        graph.add_next(e, d)
    # the guard is on the edge itself, so the general add_edge cannot get round it
    graph.add_node(e)
    with pytest.raises(GraphError):
        graph.add_edge(c, e, EdgeType.NEXT)
    with pytest.raises(GraphError):
        graph.add_edge(e, d, EdgeType.NEXT)


def test_next_edges_carry_no_timing():
    graph = OmkGraph(GraphMeta())
    c, d = notes(C, D)
    graph.add_line([c, d])
    edge = graph.get_edge(c, d, EdgeType.NEXT)
    assert isinstance(edge, Next)
    assert not hasattr(edge, "displacement")


# --- piano: a second voice mid-line, the left hand as a layer --------------------


@pytest.fixture
def piano():
    """Right hand c-d-e-f (quarters) with a second voice a-b (eighths) under d;
    left hand g-a (halves) branched head from head."""
    graph = OmkGraph(GraphMeta())
    rh = notes(C, D, E, F)
    voice2 = notes(A, B, duration=eighth)
    lh = notes(G, A, duration=half)
    graph.add_line(rh)
    graph.add_line(voice2)
    graph.add_line(lh)
    graph.add_branch(rh[1], voice2[0])
    graph.add_branch(rh[0], lh[0])
    return graph, rh, voice2, lh


def test_span_walk_covers_voices_and_layers_and_line_walk_does_not(piano):
    graph, rh, voice2, lh = piano
    assert names(graph.walk_line(rh[0])) == ["C", "D", "E", "F"]
    assert names(graph.walk_span(rh[0])) == ["C", "G", "A", "D", "A", "B", "E", "F"]
    assert names(graph.walk_span(rh[1], rh[2])) == ["D", "A", "B", "E"]


def test_span_transpose_covers_all_three_lines(piano):
    graph, rh, voice2, lh = piano
    graph.transform_tones(rh[0], None, TonalVector.transpose, M2)
    assert names(rh) == ["D", "E", "F#", "G"]
    assert names(voice2) == ["B", "C#"]
    assert names(lh) == ["A", "B"]


def test_branch_timing(piano):
    graph, rh, voice2, lh = piano
    assert graph.relative_onset(rh[0], voice2[0]) == quarter
    assert graph.relative_onset(rh[0], voice2[1]) == quarter + eighth
    assert graph.relative_onset(rh[0], lh[1]) == half
    assert graph.relative_onset(voice2[1], lh[1]) == eighth
    assert graph.relative_onset(rh[3], lh[0]) == -(quarter + half)


def test_branch_from_offset_and_with_displacement():
    graph = OmkGraph(GraphMeta())
    c, d = notes(C, D, duration=half)
    a, b = notes(A, B)
    graph.add_line([c, d])
    graph.add_line([a, b])
    graph.add_branch(c, a, anchor=TimingAnchor.OFFSET, displacement=-quarter)
    assert graph.relative_onset(c, a) == quarter
    assert graph.relative_onset(c, b) == half


def test_a_head_is_branched_at_most_once_and_must_be_a_head():
    graph = OmkGraph(GraphMeta())
    c, d = notes(C, D)
    a, b = notes(A, B)
    graph.add_line([c, d])
    graph.add_line([a, b])
    with pytest.raises(GraphError):
        graph.add_branch(c, b)  # b has a NEXT in
    graph.add_branch(c, a)
    with pytest.raises(GraphError):
        graph.add_branch(d, a)  # already branched
    with pytest.raises(GraphError):
        graph.add_stint(Part(name="Left hand"), Stint(), a)  # a is owned by whoever does c


# --- incomplete music: pins ------------------------------------------------------


@pytest.fixture
def sketch():
    """A four-bar melody in whole notes, a two-bar chord line pinned at bar 1,
    and a countermelody pinned a quarter into bar 3."""
    graph = OmkGraph(GraphMeta())
    melody = notes(C, D, E, F, duration=whole)
    chords = [ChordEvent(chord=C(maj), duration=whole), ChordEvent(chord=F(maj), duration=whole)]
    counter = notes(G, A, B, duration=half)
    graph.add_line(melody)
    graph.add_line(chords)
    graph.add_line(counter)
    graph.add_simultaneous(melody[0], chords[0])
    graph.add_simultaneous(melody[2], counter[0], displacement=quarter)
    return graph, melody, chords, counter


def test_pins_relate_lines_without_an_origin(sketch):
    graph, melody, chords, counter = sketch
    assert graph.relative_onset(melody[0], chords[1]) == whole
    assert graph.relative_onset(melody[0], counter[0]) == whole + whole + quarter
    assert graph.relative_onset(chords[1], counter[2]) == whole + quarter + half + half
    assert graph.relative_onset(counter[0], melody[0]) == -(whole + whole + quarter)


def test_pins_are_not_entered_by_span_walks(sketch):
    graph, melody, chords, counter = sketch
    assert list(graph.walk_span(melody[0])) == melody
    graph.transform_tones(melody[0], None, TonalVector.transpose, M2)
    assert str(chords[0].chord) == "C"
    assert names(counter) == ["G", "A", "B"]


def test_a_consistent_second_pin_is_silent(sketch):
    graph, melody, chords, counter = sketch
    graph.add_simultaneous(melody[1], chords[1])
    with warnings.catch_warnings():
        warnings.simplefilter("error", OmkWarning)
        assert graph.check_alignment() == []


def test_an_inconsistent_second_pin_is_reported(sketch):
    graph, melody, chords, counter = sketch
    graph.add_simultaneous(melody[2], chords[1])  # but chords[1] is only a whole after melody[0]
    with pytest.warns(OmkWarning, match="pinned .* but lies"):
        conflicts = graph.check_alignment()
    assert len(conflicts) == 2  # each of the two chord pins contradicts the other
    assert all(edge.type is EdgeType.SIMULTANEOUS for edge in conflicts)


def test_unknown_durations_are_opaque():
    graph = OmkGraph(GraphMeta())
    c, d, e = notes(C, D, E)
    d.duration = None
    graph.add_line([c, d, e])
    assert graph.relative_onset(c, d) == quarter  # c's own width is known
    with pytest.raises(GraphError):
        graph.relative_onset(c, e)
    with pytest.raises(GraphError):
        graph.relative_onset(e, c)
    a = NoteEvent(tones={A}, duration=quarter)
    graph.add_branch(d, a, anchor=TimingAnchor.OFFSET)
    with pytest.raises(GraphError):
        graph.relative_onset(d, a)
    graph.add_node(b := NoteEvent(tones={B}))
    with pytest.raises(GraphError):
        graph.relative_onset(c, b)  # not connected at all


# --- doubling: parts, stints, materialize ------------------------------------------


def test_piccolo_doubles_the_flute_then_stops():
    graph = OmkGraph(GraphMeta())
    flute_line = notes(C, D, E, F)
    graph.add_line(flute_line)
    flute, piccolo = Part(name="Flute"), Part(name="Piccolo")
    octave = TonalVector((0, 0, 1))
    graph.add_stint(flute, Stint(), flute_line[0])
    graph.add_stint(piccolo, Stint(transposition=octave), flute_line[0], flute_line[1])
    (flute_stint,) = graph.stints(flute)
    (piccolo_stint,) = graph.stints(piccolo)
    assert list(graph.walk_stint(flute_stint)) == flute_line
    assert list(graph.walk_stint(piccolo_stint)) == flute_line[:2]
    assert piccolo_stint.transposition == octave
    # the events themselves are untouched: the view is the consumer's to apply
    assert names(flute_line) == ["C", "D", "E", "F"]


def test_materialize_forks_the_covered_span_only():
    graph = OmkGraph(GraphMeta())
    flute_line = notes(C, D, E, F)
    voice2 = notes(A, B, duration=eighth)
    graph.add_line(flute_line)
    graph.add_line(voice2)
    graph.add_branch(flute_line[1], voice2[0])
    flute, piccolo = Part(name="Flute"), Part(name="Piccolo")
    graph.add_stint(flute, Stint(), flute_line[0])
    piccolo_stint = Stint()
    graph.add_stint(piccolo, piccolo_stint, flute_line[0], flute_line[1])

    head = graph.materialize(piccolo_stint)

    forked = list(graph.walk_stint(piccolo_stint))
    assert forked[0] is head
    assert forked == flute_line[:2] + voice2  # same content ...
    assert not any(f is o for f in forked for o in flute_line + voice2)  # ... new objects
    assert {f.id for f in forked}.isdisjoint({o.id for o in flute_line + voice2})
    assert graph.get_previous(head) is None and graph.get_next(forked[-1]) is None
    assert graph.relative_onset(head, forked[2]) == quarter  # the branch came along, timed the same
    # the original line, and the flute's stint over it, are untouched
    (flute_stint,) = graph.stints(flute)
    assert list(graph.walk_stint(flute_stint)) == [
        flute_line[0],
        flute_line[1],
        *voice2,
        *flute_line[2:],
    ]
    graph.transform_tones(head, None, TonalVector.transpose, M2)
    assert names(forked) == ["D", "E", "B", "C#"]
    assert names(flute_line) == ["C", "D", "E", "F"]


def test_materialize_copies_the_music_on_the_span_exactly():
    graph = OmkGraph(GraphMeta())
    line = notes(C, D, E, F)
    graph.add_line(line)
    graph.add_articulation(Marking(mark=staccato), line[0])
    graph.add_spanner(MarkSpanner(mark=crescendo), line[0], line[1])  # inside the span
    graph.add_spanner(MarkSpanner(mark=slur), line[1], line[3])  # crosses its end
    verse = LyricSection(section_type="verse", section_number=1)
    syllables = graph.add_lyrics("Al-le-lu-ia", section=verse)  # section reaches past the span
    graph.zip_lyrics_to_objects(syllables[0], line[0])
    flute, oboe = Part(name="Flute"), Part(name="Oboe")
    graph.add_stint(flute, Stint(), line[0])
    oboe_stint = Stint()
    graph.add_stint(oboe, oboe_stint, line[0], line[1])

    with pytest.warns(OmkWarning) as caught:
        head = graph.materialize(oboe_stint)
    assert sorted(str(w.message).split(" was not copied")[0] for w in caught) == sorted(
        [repr(verse), "MarkSpanner(mark=Mark(name='slur', ...))"]
    )

    forked = list(graph.walk_stint(oboe_stint))
    attached = {
        type(n).__name__: n
        for e in forked
        for n in graph._graph.predecessors(e)
        if not isinstance(n, Stint | NoteEvent)
    }
    assert set(attached) == {"Marking", "MarkSpanner"}
    assert attached["Marking"].mark == staccato and attached["MarkSpanner"].mark == crescendo
    assert list(graph._graph.successors(attached["MarkSpanner"], edge_type=EdgeType.STARTS_AT)) == [
        head
    ]
    assert list(graph._graph.successors(attached["MarkSpanner"], edge_type=EdgeType.ENDS_AT)) == [
        forked[1]
    ]
    sung = [next(graph._graph.successors(e, LyricSyllable, EdgeType.LYRIC)) for e in forked]
    assert [str(s) for s in sung] == ["Al -", "- le -"]
    assert sung[0] is not syllables[0] and sung[0].word is sung[1].word  # a copy, sharing one Word
    assert sung[0].word is not syllables[0].word
    assert graph.get_next(sung[0]) is sung[1] and graph.get_next(sung[1]) is None
    # the originals keep everything: staccato, hairpin, flute stint (the oboe's moved)
    assert len(list(graph._graph.predecessors(line[0]))) == 3
    assert graph.get_next(syllables[1]) is syllables[2]


# --- grace notes ----------------------------------------------------------------------


def test_grace_notes_have_zero_width():
    assert grace_eighth == ZeroDuration()
    assert grace_eighth == grace_sixteenth
    assert grace_eighth.nominal == eighth
    assert quarter + grace_eighth + grace_sixteenth == quarter
    assert sum([grace_eighth, quarter, grace_sixteenth, quarter]) == half
    assert isinstance(grace_eighth, GraceDuration) and isinstance(grace_eighth, ZeroDuration)


def test_a_run_of_grace_notes_adds_nothing_to_the_line():
    graph = OmkGraph(GraphMeta())
    c, d = notes(C, D)
    graces = notes(A, B, duration=grace_sixteenth)
    graph.add_line([c, *graces, d])
    assert graph.relative_onset(c, d) == quarter
    assert graph.relative_onset(c, graces[1]) == quarter
    graph.transform_tones(c, d, TonalVector.transpose, M2)
    assert names(graces) == ["B", "C#"]


def test_lyrics_zip_past_grace_notes_unless_attached_by_hand():
    graph = OmkGraph(GraphMeta())
    c, d, e = notes(C, D, E)
    grace = NoteEvent(tones={B}, duration=grace_eighth)
    graph.add_line([c, grace, d, e])
    syllables = graph.add_lyrics("Al-le-lu")
    graph.zip_lyrics_to_objects(syllables[0], c)

    def sung(event):
        return [str(s) for s in graph._graph.successors(event, LyricSyllable, EdgeType.LYRIC)]

    assert (sung(c), sung(d)) == (["Al -"], ["- le -"])
    assert sung(grace) == []
    assert sung(e) == ["- lu"]
    graph.connect_lyric_to_object(syllables[1], grace)
    assert sung(grace) == ["- le -"]
