Open Music Kit 
===============

.. toctree::
   :maxdepth: 2
   :caption: Contents:

Open Music Kit (OMK) is a symbolic music representation library
that provides tools for encoding symbolic music information (scores, notation)
and operations on that information (transpositions, metrical elongation)
in mathematically meaningful ways that are 
algebraically isomorphic to the musical concepts they represent.

OMK represents atomic musical entities (pitches, durations) as vectors,
and musical structures (chords, melodies, scores) as graphs.

Universal Music Encoding
------------------------

One of the goals of OMK is to support 
any type of music from any musical culture.
While true universality is probably impossible in an absolute sense,
the data model is designed to be as abstract and foundational as possible,
to support as many specific tonal and rhythmic systems as possible.

- Atomic musical units (for example, tonal and temporal elements)
  are first defined in abstract terms and then implemented into specific
  Tonal and Temporal Systems.
- Harmonic elements along with their functions and operations
  are defined as graphs built out of atomic Tonal elements within a specific system
  - This allows each Tonal System to have its own Harmonic System.
  - A single Tonal System (such Western Standard 12-tone music)
    can also have multiple independent Harmonic Systems
    (for example, Common Practice and NeoRiemannian)
- Temporal Systems are fully independent of Tonal Systems,
  and multiple Temporal and Tonal systems can be used together,
  allowing the encoding of mixed-system or cross-cultural/fusion scores.
- The Graph structure provides a number of cross-cultural capabilities:
  - Linear and cyclic structuring that can model conventional WSMN scores
    as well as cycle-based music such as Gamelan and African Drumming
    (as well as more complex bespoke structures
    for contemporary experimental music).
  - Arbitrary levels of "completeness".
    Fully realized orchestral scores, lead sheets, chord charts, slash charts,
    short scores, conceptual diagrams, time-based scores, circular beat charts,
    unrealized figured bass, and nearly any other manner of music representation
    is equally valid, equally analyzable, and equally amenable to vectorization.

The core OMK library (this repo/package) provides the foundational abstract layer,
and a few built-in implementations of specific musical systems.

Foundational Abstract Layer 
~~~~~~~~~~~~~~~~~~~~~~~~~

The foundational data model includes:

- `Tone`, a musical sound
- `Interval`, the distance between two tones
- `TemporalElement`, a measurable period of musical time 
- `TemporalRatio`, a relationship between two equal but differently-subdivided `TemporalElement`s
- `PercussionTone`, a general-purpose percussion vectorization that encodes
   objective (measurable) and subjective (judgement-based) sound qualities.
- `Note`, a `Tone` with a `Duration`
- `Score`, the graph-based datamodel for musical structure


Western Standard Music Notation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Western Standard Music Notation (WSMN) implementation includes:

- 12 note (really 35+ note) Tonal System and intervallic relationships
- standard Metrical Durations (whole, half, quarter, etc; dots, tuples)
  and TimeSignature
- chords, chords symbols, and an implementation of Common Practice harmonic theory
- contextual Tuning calculation for just intonation and other non-tempered tunings.
- linear scores with standard roadmap and expression nodes
- just about anything else you would need to represent and vectorize
  nearly any piece "Western" music from any style (classical, jazz, folk, pop, sacred)
  in any standard (and many non-standard) score/notation format.
- Output to MusicXML and Lilypond for rendering and printing scores, charts, and leadsheets.
- Output to MIDI for use in a DAW.

MIDI
~~~~

While MIDI is based around WSMN,
it includes information not normally found in a conventional score
(for example, ticks, channels, mod wheels, tuning offsets)
and does not fully model the conceptual underpinning of the Western Tonal system.
Additionally, in keeping with the goal of universalization,
this project needs system-agnostic abstractions for translating
from any specific Musical System into sound synthesis and playback.

Therefore, MIDI is implemented as its own musical system.

Clock Time
~~~~~~~~~~

OMK implements Clock Time as an independent Temporal System.
This is useful for time-based scores as well as
metronome markings and MIDI tempo/timing data.

OMK Ecosystem
-------------

The goal of this project is to create a complete ecosystem for
music composition, analysis, generation, and research.
The present package forms the core data model for an OMK score.

Other planned packages will handle:

- MIDI (in more depth and detail than the core MIDI representation)
- Chant
- Time, Space, and Event-driven scoring
- Harmonic analysis, function harmony, and harmonic systems
- Counterpoint rules
- Orchestration, instrumentation, and arranging
- Generative music and agentic composition
- Audio processing
- Structural analysis
- Tuning, intonation, and non-12TET tonal systems
- Visual and non-standard scores
- Music visualization

We are also eager to work with musician/programmers
who can implement non-Western musical systems
in OMK's graph model.