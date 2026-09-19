"""Objects are the basic building blocks of the music graph, serving as nodes in the graph.

Objects are (usually) mutable, and represent items found in a score, sketch, or other piece of music,
such as notes, chords, sections, lyrics, articulations, markings, analysis figures, etc.
Each instantiated object represents a single things: this note, that syllable, this staccato mark.
They are generally composed of immutable values.

So a C-sharp in the tenor line of a chorale is represented by a single OmkObject instance
(in this case, a Note, which is a SequentialObject),
and has a tone attribute (the value of C# -- TonalVector(0, 1, 0)),
and a duration (for example, the value of a quarter note -- TemporalDuration(1,4)).

To transpose the note, a new Note object is not needed --
the tone attribute can simply be assigned a new value.

OmkObjects are connected to each other in the graph by edges (see the edges module).
In the case of our C-sharp above, the lyric syllable sung on that C-sharp
is a LyricSyllable object (which is also a SequentialObject, and contains the syllable text),
and is connected to the Note object by an edge of type LYRIC.
"""

from openmusickit.objects import lyrics, note, omk_object

__all__ = [
    "lyrics",
    "note",
    "omk_object",
]
