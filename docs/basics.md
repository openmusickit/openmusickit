---
title: Basics
---

Open Music Kit is a symbolic music representation system,
using a graph-based data structure and abstract music primitives,
designed to support scores at any level of completeness
in any musical system.

What does that mean, exactly?

## Symbolic Music Representation System

There are, essentially, two ways to think about storing music data:

- audio
- symbols

Symbolic music representation means
storing the kind of data used to create a score.
MusicXML, Lilypond, ABC, Music21, and the file formats of various notation software systems
are all examples of *symbolic* music representation formats.

## Graph Based

Music is inherently relational:
this note follows that note,
these notes sound together,
this chorus comes between these two verses,
this section is a variation of that section.

Music is also multi-hierarchical:
notes sit inside bars, which sit inside sections, which sit inside movements;
notes also sit inside parts, which sit inside groups, which sit inside ensembles. 

There are many possible ways to represent these relationships and hierarchies.
Conventional visual notation uses the vertical axis
to represent simultaneity (as well as relative pitch),
and the horizontal dimension to represent relative time.
It uses barlines and staff groupings to represent different types of hierarchies.

OMK uses a graph,
which is a data structure made up of nodes (things) and edges (relationships).
So notes, chords, lyric syllables, and other things you typically think of as "marks on a score"
are each nodes in a graph,
and the edges (connections) show how they related to each other.
This allows for many divergent relational and hierarchical structures to be represented at once.

## Abstract Music Primitives

There are many musical system in the world,
and only a few related ones use the things many of us most associate with "music theory" or notated scores:
letter names for pitches, durations like "quarter note", chords like "C maj" or "D min", key signatures, time signatures.
But (nearly) all music systems have some notion of different types of sounds happening at some time in relationship to other sounds.

OMK seeks to support as many musical systems as possible,
and so has abstracted as many of these ideas as possible 
into their underlying conceptual essence.

A Tone doesn't have to be a pitch with a letter name (or a specific frequency or a MIDI number),
a Duration doesn't have to be a fractional note name, a length in milliseconds, or even measurable at all.
Each musical system can have its own implementation of these ideas,
and the graph can hold objects from any system together in a single score.

OMK also separates tonal and temporal systems from each other,
so a single score could (for example) mix Western-style note names with Gamelan-style temporal structure.
There are also mechanism for defining conversions between various systems.

### Western Standard Music Notation

Western Standard Music Notation (WSMN, throughout the OMK system and documentation)
is one possible implementation of the underlying Abstract Data Types.
OMK ships with a complete implementation of WSMN's Tonal, Temporal, Percussion, and Scoring systems.

This serves the immediate needs of most musicians working in any WSMN-based genre
(including classical, pop, folk, rock, jazz and any other music that has A-G pitch names and concepts like "quarter notes".)
It also serves as an exemplar implementation for anyone wishing to create an OMK extension package for other musical systems.

## Any Level of Completeness

Many symbolic music representations,
especially those targeting printed score preparation or playback,
do not support musical work in progress,
the partial specifications used by many musicians
(comping charts, lead sheets, sketches, lyrics+chords),
or the incomplete information provided by some manuscript sources.

For example --- 
often, a note has to have both a pitch and a duration,
and sit inside a measure with some defined key signature and time signature,
with a definite horizontal and vertical relationship to all other notes already included in the piece.

OMK's graph structure lets you specify only the information and only the relationships
that you actually want to specify,
and makes no assumptions about what you have not included.

All of the following are valid graphs:

- notes without defined rhythm
- rhythms without defined pitches
- chord progressions without melody, anchor notes, or durations
- lyrics alone
- chords attached directly to lyrics with no other details
- sections without content
- independent snippets not connected to each other
- descriptions of music you plan to write ("big horn blast here")

## Any Musical System

OMK is deliberately extensible.
The graph structure makes no assumptions or demands regarding Tonal or Temporal systems,
and can hold heterogenous material in a single graph.
The musical primitives are designed as a collection of (mostly Abstract) Base Classes,
which can be subclassed to implement a wide variety of Tonal and Temporal systems.

While OMK ships with a complete (we hope) implementation of Western Standard Music Notation,
WSMN is not privileged in any way, and is treated as merely one possible implementation of the musical primitives.
(Downstream users are even free to provide their own implementation of WSMN,
if the built-in one does not suit their purposes.)

