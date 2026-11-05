---
title: Abstract Music Primitives
---

::: {.callout-note}
Because musical ideas are very difficult to discuss in the abstract,
this document will explain both what OMK's base classes represent in the abstract
and also how they are subclasses in the built-in Western Standard Music Notation (WSMN) implementation,
along with what they might represent in other (yet to be implemented) musical systems.

Keep in mind that WSMN particulars are not universal.
:::


## Musical System

There is no unified "Musical System" conception in OMK.
Rather, a Musical System (such as WSMN - Western Standard Music Notation)
is defined in one or more Tonal and Temporal Systems.
For convenience, these can easily be colocated in a single package,
but they are logically distinct.

## Tonal System

A TonalSystem is an interrelated collection of classes 
that implement some real musical Tonal System.
These generally include subclasses of the following:

- Tone (pitches or other defined sounds)
- Interval (relationships or distances between tones)
- ToneCollection (organized and named sets of tones, such as chords and scales)
- ModalContext (organized systems of tones)

Tones within a TonalSystem, and their various relationships and organizing principles,
are defined entirely in reference to each other,
without reference to specific physical or acoustic realizations (such as frequency or MIDI numbers)
or to other TonalSystems (a future Gamelan or Carnatic TonalSystem would not reference WSMN's pitches).

OMK's built-in implementation of Western Standard Music Notation
includes two separate TonalSystems,
WSMN_Tonal (which defines pitch letter names and related phenomena) and
WSMN_Percussion (which defines various types of percussion strokes).
The need for this kind of distinction illustrates what a TonalSystem actually represents.



### Tone

A Tone is a named pitch, or other definable sound-quality primitive.
Musical operations on that pitch (such as transposition),
and the relationships between pitches (such as the interval between two pitches)
are defined in the Tone subclass that implements a particular system's notion of Tone.

In WSMN_Tonal, Tones are implemented by the TonalVector class,
which can represent a pitch class (C natural, F sharp, etc.)
or a specific octave-qualified pitch (Middle C, F sharp two octaves above Middle C, etc.).

#### SilentTone

Every Tonal System automatically has access to, or includes,
the SilentTone, which represents rests.
SilentTone does not need to be re-implemented in TonalSystems,
as no tonal operations (such as transposition) affect it.

#### UnpitchedTone

TonalSystems (such as WSMN_Tonal) in which sounds are not part of a tone-interval relationship network
should typically use the UnpitchedTone base class to implement their notion of Tone,
as it makes fewer demands and assumptions.


### Interval

An Interval is a distance (or other relevant relationship) between two Tones.
A TonalSystem should normally create a set of Tones $T$ and Intervals $I$,
with some defined set of algebraic relationships of the form:

$$
\begin{aligned}
\operatorname{alter\_tone} &: T \times I \to T \\
\operatorname{measure\_relationship} &: T \times T \to I
\end{aligned}
$$

WSMN_Tonal, for example, includes:

$$
\begin{aligned}
\operatorname{transpose} &: T \times I \to T \\
\operatorname{distance} &: T \times T \to I
\end{aligned}
$$

TonalSystems may also include relationships of the form:

$$
\begin{aligned}
\operatorname{some\_operation} &: T \times T \to T \\
\operatorname{some\_operation} &: I \times I \to I
\end{aligned}
$$

For example, in WSMN, you can invert a Tone over another Tone,
or add two intervals together.

$$
\begin{aligned}
\operatorname{invert}\bigl(G, C \bigr) &= F \\
\mathrm{Maj3} + \mathrm{min3} &= \mathrm{Per5}
\end{aligned}
$$

In Western Music Theory, there is a strict mathematical isomorphism between pitches and intervals.
For this reason, Intervals in WSMN_Tonal are also implemented with TonalVector.
The TonalVector class includes methods for reading out its internal vector representation
as musician-readable pitch and interval names.

### ToneCollection

A ToneCollection is an ordered collection of Tones,
along with an implementation of the TonalSystem's rules for manipulating and representing that collection.

For example, in WSMN_Tonal,
Chords and Scales are both types of ToneCollection.
The Chord class includes standard chord operations such as transposition and inversion.

### ModalContext

A ModalContext is a tonal center, a set of tones,
and rules about how tones relate to each other within a ModalContext,
as well as how ModalContexts relate to each other.
It is the abstracted notion of WSMN's Key and similar ideas
such as mode, raga, maqam, and pathet.

As the principles of modal organization of different musical systems vary widely,
the ModalContext abstraction makes very few demands or assumptions of its implementations.

## Temporal System

A TemporalSystem is one or more classes
that implement some real musical Temporal System.

### Duration

The only abstract base class that needs to be implemented
for any TemporalSystem is Duration.
A TemporalSystem's Duration subclass
is instantiated into the various durations that are used within the system,
for example, WSMN's quarter notes, half notes, whole notes, and so forth.
A Duration subclass implements all musically relevant operations,
such as augmentation, diminution, or comparison.

Durations within a TemporalSystem, and their various relationships and organizing principles,
are defined entirely in reference to each other,
without reference to clock time, MIDI ticks, or any other TemporalSystem.
(For example, a future Gregorian TemporalSystem would not
define a punctum in relation to WSMN's quarter note.)

OMK's values.time module includes other classes
used when working with musical time.
(The following is not exhaustive,
but is intended to highlight the more important concepts.)


### TemporalElement

A TemporalElement is any structured period of time.
Duration is a subclass of TemporalUnit.

### Measurable

Measurable is a TemporalUnit that is a measurable period of time.
Measurables from within the same TemporalSystem can be compared to each other.

Implemented Durations in TemporalSystems are usually
(but are not required to be) Measurable.

### TemporalUnit

A TemporalUnit is some number of TemporalElements,
for example, four quarter notes.

WSMN_Temporal subclasses TemporalUnit to create Time Signatures.

### TemporalRatio

A TemporalRatio relates two TemporalUnits,
in other words,
some number of durations to some number of durations.

TemporalRatios are used for tuplets, cross-system translation, and tempo
(tempo being just a cross-system translation between some musical TemporalSystem and ClockTime).

### CLOCK_TIME

CLOCK_TIME is a TemporalSystem that includes ClockDuration,
a duration measured in microseconds.

## Scoring

OMK provides a handful of abstract primitives for scoring.
These are, for the most part, marks on a score
which are used to organize or interpret the Tonal and Temporal material. 

- Clef
- DivisionShape (WSMN subclasses this to BarLines)
- Mark (a wide variety of scoring marks, such as articulations, accents, phrase marks, and other types of annotations)
- StackGroupShape (WSMN subclasses this to Brackets, used to organize groups of staves)
- TempoTerm

