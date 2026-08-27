# Open Music Kit: Goals and Design Values

<!--
The first draft of this document was written by ChatGPT,
after countless hours of discussion about the goals of this project.
While I might have worded or organized things differently if I had hand-written it,
is fully aligned with my thinking on this project.
-->

Open Music Kit exists to provide a general-purpose computational representation of music
capable of describing music faithfully across 
traditions, levels of completeness, theoretical systems, and computational uses.

OMK is not intended to encode a single theory of music, a single notation system, or a single workflow. 
It provides a framework in which many such systems can 
exist, interact, and remain faithful to their own internal logic.

The architecture of OMK follows from these goals. In particular, the decision to represent music as a graph is not itself a foundational goal. It is a design choice made because musical information is fundamentally relational and because more rigid representations impose assumptions that quickly become limiting. That choice, however, makes possible forms of representation, traversal, analysis, and computation that have become important goals in their own right.

## 1. Represent music without privileging one kind of music

OMK should be capable, in principle, of representing any musical system.

The most abstract layers of OMK should therefore make as few culturally specific assumptions as possible. Western pitch, meter, notation, harmony, and formal structure are implementations built on top of more general abstractions, not properties of music itself.

A musical tradition should be able to define the entities and relationships that it considers meaningful rather than translating itself into Western concepts merely because those concepts happen to be built into the software.

Different systems should also be able to coexist. Where two systems share meaningful concepts or relationships, OMK should make it possible to connect them without pretending that they are identical.

The goal is not a universal theory of music. It is a framework capable of hosting many theories of music.

## 2. Represent music at any level of completeness

A complete, publication-ready score is only one possible representation of musical thought.

OMK should also be able to represent:

* a melody with no rhythm;
* a harmonic progression;
* a lead sheet;
* a Nashville-number chart;
* lyrics without music;
* a few disconnected musical ideas;
* an orchestration sketch;
* an incomplete passage;
* alternative possibilities that have not yet been resolved;
* analytical structures layered onto existing music;
* musical relationships that have no conventional notational equivalent.

Incomplete music is not malformed music.

A fragment should not need to pretend to be a score before software can work with it. Components such as notes, chords, lyrics, sections, annotations, and conceptual structures should be able to exist as first-class musical objects and acquire additional relationships as the representation becomes richer.

## 3. Preserve meaningful information

A representation should not discard distinctions merely because a simpler representation is more convenient.

Whenever a musical concept has meaningful internal mathematical structure, OMK should preserve that structure.

In particular, where a musical domain admits a useful vector, coordinate, algebraic, set-theoretic, or other mathematical representation, that representation should be semantically meaningful and as nearly lossless as the domain permits.

Vectorization should not mean flattening musical concepts into arbitrary numeric labels for the convenience of machine learning.

Two objects that are musically distinct should not silently become identical because a chosen encoding cannot express the distinction.

Likewise, mathematical operations should correspond to genuine operations in the musical domain whenever possible.

## 4. Make relationships first-class

Music is not naturally a single sequence.

Musical objects participate simultaneously in many kinds of relationships: temporal, vertical, formal, harmonic, motivic, notational, performative, analytical, textual, and others.

OMK uses a graph representation so that these relationships do not have to be collapsed into a single hierarchy or timeline.

This allows the same musical material to participate in several structures at once, permits disconnected and incomplete material to remain valid, and allows new kinds of relationships to be added without redesigning the entire representation.

The graph began as an architectural solution to the problem of flexible representation. It also creates further possibilities that OMK should actively support: traversal, structural queries, pattern matching, transformation, comparison, corpus analysis, graph algorithms, and graph-native machine learning.

The graph exists for the music, not the other way around.

## 5. Be useful for computation without being designed around one computation

OMK should make musical data useful to many kinds of computational systems.

That includes conventional algorithms, symbolic transformations, search and pattern matching, constraint systems, statistical methods, graph algorithms, neural networks, graph neural networks, generative systems, analytical tools, and approaches that have not yet been invented.

OMK should not distort its representation of music merely to suit the input format of a particular model architecture.

The core representation should describe the musical object as faithfully as possible. Adapters, encoders, samplers, feature extractors, and model-specific transformations can then produce the representations required by particular computational methods.

The data model should outlive today's preferred AI architecture.

## 6. Be genuinely extensible

OMK cannot and should not contain authoritative implementations of every musical tradition, theoretical system, analytical method, or compositional practice.

Instead, it should provide enough stable infrastructure that domain experts can extend it.

A sufficiently motivated expert in gamelan music should be able to implement the concepts and relationships required by that tradition without modifying the foundations of OMK or disguising those concepts as approximations of Western ones.

The same should be true for new tuning systems, rhythmic systems, notation systems, analytical theories, compositional techniques, performance practices, and experimental forms.

Extensions should be able to participate in the larger OMK ecosystem wherever their capabilities overlap with other systems.

Extensibility is therefore not an escape hatch for concepts the core library forgot to implement. It is part of the fundamental design.

## 7. Prefer faithful abstractions to convenient special cases

OMK should strive for conceptual correctness.

Software inevitably contains pragmatic compromises, but the underlying musical abstractions should not be based on shortcuts that merely happen to cover common repertoire.

If an operation has a general mathematical definition, the implementation should normally reflect that definition rather than a table of familiar cases.

A dotted duration is a simple example. Most musicians will never encounter a note with five augmentation dots. That is not a reason to implement only one, two, or three dots. The underlying operation is well defined for an arbitrary number of dots, and the representation should express that fact directly.

This principle applies throughout OMK:

**Represent the thing itself, not merely the cases we currently expect to encounter.**

Edge cases are especially valuable because they reveal whether an abstraction actually describes its domain or merely imitates it.

## 8. Keep simple things simple without making complex things impossible

Generality should not require every user to manipulate the most general representation all the time.

OMK can provide convenient sequences, collections, constructors, importers, and other simpler interfaces for ordinary cases while retaining a richer underlying model.

A four-part chorale should not require dozens of lines of graph construction code simply because OMK can also represent an indeterminate electroacoustic performance.

Convenience abstractions may deliberately express a subset of OMK's capabilities. They should, however, have clear semantics and well-defined relationships to the richer representation.

Simple interfaces should be simplifications of the model, not competing models that quietly disagree with it.

## 9. Separate musical meaning from incidental presentation

OMK's core objects should describe musical meaning rather than the incidental requirements of a particular application or notation renderer.

Visual layout, editor state, application-specific presentation information, provenance, annotations, and similar concerns may all be important and should have places in the ecosystem. They should not be confused with the musical concepts themselves.

This separation makes the same musical structure usable by notation software, analytical tools, databases, educational applications, generative systems, research code, and software that has no visual representation at all.

## 10. Remain inspectable and understandable

OMK should make its representations explicit.

Musical data structures should be understandable by programmers and domain experts rather than functioning as opaque implementation machinery.

Relationships should have names. Transformations should have defined semantics. Units and coordinate systems should be identifiable. Conversions should make their assumptions visible. Lossy operations should be recognizable as lossy operations.

The library should favor designs whose correctness can be reasoned about.

This is especially important for software intended to become infrastructure. A representation that is clever but impossible to explain is difficult to trust, extend, or preserve.

# In short

OMK should be:

**Universal without claiming universality of musical theory.**

**Flexible enough for finished works, fragments, sketches, and structures that do not resemble conventional scores.**

**Mathematically meaningful wherever the music itself permits mathematical structure.**

**Faithful before convenient.**

**Useful for algorithms and AI without being shaped around one particular algorithm or AI architecture.**

**Extensible by people who know musical systems that OMK's original developers do not.**

**Simple to use in ordinary cases without placing artificial limits on extraordinary ones.**

And above all:

**The representation should follow the music. The music should never have to deform itself to fit the representation.**
