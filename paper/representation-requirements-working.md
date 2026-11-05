---
title: "What anyone has ever wanted from a music representation system: a master list"
date: 2026-10-12
---

A synthesis of the 42 requirement lists collected in `representation-requirements.md` (with
verified quotations there), plus the borderline and "no list, but says something" sources from the
same note. Requirements that different authors state in different words are merged; each item cites
every source that asks for it, with the page where it does. Where authors want opposite things, the
conflict is recorded in the last section rather than smoothed over.

Page numbers follow the excerpt note, including its caveats (preprint pagination for Dannenberg
1993, Harris et al. 1991, Roland 2002 and Wiggins 2009; approximate journal pages for Marsden 2005).
Byrd & Isaacson 2003 and Huron 2002 were added on 2026-10-12; Wolff 1977, Brinkman 1986, Honing 1993 and 2001,
Pachet 1993, Balaban 1996, Hirata & Aoyagi 2003 and Wiering et al. 2009 (plus short statements from Allen 1983 and
others) on 2026-10-13; Huron 1992 (scanned) on 2026-10-14.

# 1. Scope and coverage

## Comprehensive and Complete

A representation of a score or piece of music should be capable of carrying all the musical information intended by the composer, arranger, or transcriber of the piece, along with any information a consumer of the representation (such as a musicologist or AI model) needs to accomplish their tasks.

As straightforward as this requirement may sound, it immediately exposes many of the problems with music data representation - what exactly is included in the set of "everything"? The particulars of a specific performance, including exact frequencies, timing, and timbre? The circumstances surrounding that performance? Analysis and commentary? The phase of the moon during which it is customary to sing the piece?

As intractable as "represent everything" is, the requirement should be taken seriously as it immediately implies a number of design principles. Two in particular should be highlighted here.

First, a music representation system should be extensible. Not just in theory, but rather built with a robust extensibility system in place.

Second, details of musical information the system is capable of capturing should not be thrown away. In other words, while the "phases of moon" extension may await an interested developer, an initial release of a system that captures note names, but does not distinguish between enharmonic spellings, is inadequate. Within the musical domains supported, complete information should be captured.

## Generality Across Musical Systems, Styles, Repertoires

An ideal system would be capable of representing music from any system or tradition, and any genre or level of complexity within those systems and traditions.

At least two design requirements are implied by this requirement. The first is the need for abstract data types for musical components (pitches, rhythms, etc), realized into concrete types for each musical system. That is, the vocabulary of Western Standard Music Notation ("C-sharp", "quarter note") are a special case, not the foundation. The second is a highly flexible structure at the score level, capable of representing any arbitrary relationship between musical components.

## The Piece and the Performance; Notation and Sound

Symbolic representation (score-oriented), MIDI, audio, and other data representing either the piece in the abstract or a specific performance of it should be representable, and should be capable of coexisting in a single representation.

## The Work and the Arrangement

A piece of music can exist at multiple levels of realization. "Happy Birthday" has an existence apart from any particular arrangement of it, any particular arrangement may have many performances, and a single performance may even have multiple recordings (famously, a single Grateful Dead concert might have any number of "bootleg" fan-made recordings).

An ideal music representation would not just be capable of representing a piece of music at any of these levels of realization, but also capable of colocating them in a single, deeply connected representation.

## Analysis and Meta-musical information

Various types of theoretical analysis (from simple harmonic analysis to more complex apparatuses such as Schenkerian or Neo-Riemannian) belong most naturally on the score, and therefore as a supported part of any symbolic representation.







6. **Timbre and the other parameters.** Pitch needs a rich representation; timbre is still being
   worked out; an event needs at least pitch class, register, duration, dynamic, timbre and metrical
   placement. [@dannenberg1993music, pp. 4–5; @babbitt2003use, p. 207]

# 2. Domains, levels and the musical surface

7. **Multiple domains of representation, explicitly labelled.** Each entity is tagged with its domain
   (graphemic / acoustic / auditory; logical / visual / gestural / analytical), with a coreference
   relation between domains; output is interpreted only in the domain of the input; Huron maps seven classes (sound,
   synthesis, performance, notation, rendered notation, analyses, meta-scores) linked by translation
   processes, a network a user traverses; type tags inside
   the data let several forms of information coexist in one document and be processed together.
   [@harley2018abstract, p. 67; @wiggins2009computer, p. 7; @babbitt2003use, p. 204; @fields2011segment,
   p. 1; @byrd2003music, pp. 45, 49–57; @huron2002music, p. 24; @huron1992design, pp. 12–15]
8. **Layered organisation.** Music information structured in layers (MX/IEEE 1599: general, logic,
   structural, notational, performance, audio), each layer usable alone. [@haus2005music, p. 331;
   @barate2009ieee, pp. 273–274; @grande1997notation, p. 493]
9. **Logical content as the core.** Encode the logical content of the score rather than the page; in
   an interchange format, logical data is the only required kind. [@hewlett1997musedata, p. 403;
   @grande1997notation, p. 493; @selfridgefield1997describing, p. 8; @byrd2003music, p. 45] (Compare item 90.)
10. **Graphical detail where it matters.** Positions of symbols (relative to their context), sizes and
    shapes, so hand-tuned layout survives; for marks whose meaning is unclear, store only the graphics and
    let the encoder choose. [@byrd2003music, p. 45]
11. **Controllable mapping between domains.** The performance meaning of each notational symbol
    (fermata length, articulation playback) can be specified, and arbitrary performance data attached to
    any symbol. [@byrd2003music, pp. 52, 57]
12. **Multiple levels of abstraction.** Zoom in and out of detail; abstract categories (pitch names)
    coexist with the continuous space beneath them; the degree of abstraction can be a parameter; the grain of reasoning can vary; a more refined
    representation can be worth its redundancy.
    [@harley2018abstract, p. 67; @wiggins2021structure, pp. 415–416; @cella2009symbolic, pp. 58–59;
    @dannenberg1993music, p. 2; @marsden2005generative, p. 411; @allen1983maintaining, p. 833; @cambouropoulos1996general, p. 232]
13. **An explicit, user-definable musical surface.** The system has a notion of the surface, and users
    can define new surfaces for an application. [@wiggins2009computer, p. 5; @harley2018abstract, p. 67;
    @pearce2005construction, p. 50]
14. **Continuous and discrete data together.** Integrate continuous controls and discrete events, with
    context-dependent equality theories for each. [@dannenberg1993music, p. 8; @wiggins2009computer, p. 8;
    @wiggins2021structure, p. 415; @cella2009symbolic, p. 58; @honing1993issues, p. 229 (continuous time for accelerando and rubato)]

# 3. Structure

15. **Hierarchy.** Higher-level structures can be introduced hierarchically; levels of detail
    correspond to levels of musical significance. [@loy1985programming, p. 256; @dannenberg1986structure,
    p. 155; @harris1991representing, p. 7; @dannenberg1993music, p. 2; @roland2002music, p. 2;
    @marsden2005generative, p. 411; @haus2005music, p. 331; @humphrey2014jams, p. 592;
    @wiggins2021structure, p. 414; @balaban1996music, p. 101]
16. **Multiple simultaneous hierarchies.** Many hierarchies over the same events at once, to represent
    ambiguous interpretations and keep kinds of information (harmony, orchestration) logically separate;
    a single hierarchy is inadequate. [@dannenberg1986structure, p. 155; @dannenberg1989music, p. 74;
    @harris1991representing, p. 7; @dannenberg1993music, p. 2; @wiggins2009computer, p. 6;
    @milmeister2009rubato, p. 18; @harley2018abstract, p. 68; @wiggins2021structure, p. 414; @byrd2003music, p. 55 (notes in several beam groups at once)]
17. **Hierarchy not imposed.** The structures and kinds of grouping must not be imposed on the user;
    structures are flexible in hierarchy and type and user-configurable. [@harris1991representing, p. 7;
    @zahorka1995predibase, p. 203]
18. **Hierarchies carry descriptions.** Each constituent hierarchy states, formally and in text, the
    relationship it denotes. [@wiggins2009computer, p. 6]
19. **Non-hierarchical relations: reference, a directed graph, cycles.** One component can refer to or
    be related to another; these relations form a directed graph over the constituents; circular
    structures are allowed. [@wiggins2009computer, p. 6; @milmeister2009rubato, p. 18;
    @wiggins2021structure, p. 416; @tanguiane1997score, p. 460; @fields2011segment, p. 1; @wiering2016digital, p. 12]
20. **Logical lines independent of layout.** Every note knows its voice, part and staff, but a voice
    can wander among the staves of its part, parts can share a staff, chords can span staves.
    [@byrd2003music, pp. 49–50, 52]
21. **Parallelism and composable part/time structure.** Simultaneity and parallel strands, built with
    composable types and operators. [@loy1985programming, p. 256; @hoglund2014music, p. 33; @honing2001time, p. 50]
22. **Segmentation: decomposable and combinable.** Divide a representation into segments matching
    significant musical segments, and combine representations when the music combines; work in segments
    rather than single notes or slices. [@marsden2005generative, p. 411; @tanguiane1997score, p. 460]
23. **Generative: context-sensitive interrelation.** Relations inside a segment follow from the segment;
    relations outside it use its context, so transposing a whole segment changes nothing inside it.
    [@marsden2005generative, p. 411]
24. **Data reduction by reference.** A recurring pattern is coded once and recalled by reference;
    rhythm and pitch patterns each get their own reference scheme. [@tanguiane1997score, pp. 460, 466]
25. **Components and construction methods.** Concepts are built from named components by a small set
    of constructions (selection, conjunction, disjunction), and have named instances with values.
    [@milmeister2009rubato, pp. 19–20]

# 4. Time

26. **Convenient handling of time.** [@loy1985programming, p. 256]
27. **Beat time and real time; performance timing.** Derive real time from the event representation;
    deal with beat time and absolute time, multiple tempi, and the timing of performances.
    [@dannenberg1989music, p. 74; @dannenberg1993music, pp. 4–5; @honing1993issues, p. 229]
28. **Exact durations, temporal constraints, transformations.** Rounding errors must not accumulate;
    timing relations should be expressible as constraints; time representations should support musical
    transformations and stay consistent under them. [@dannenberg1993music, pp. 4–5; @honing2001time, p. 50]
29. **An explicit timeline at the right level of abstraction.** Whether a special temporal logic is
    needed is an open question. [@wiggins2009computer, p. 9]
30. **Relative and partial timing.** Much temporal knowledge is relative ("A is before B") and imprecise;
    onsets can be given relative to a governing note, and abstracting the differences leaves order, not
    absolute times; onsets and temporal relations may be unknown or only partly known.
    [@allen1983maintaining, p. 833; @hirata2003computational, p. 78; @balaban1996music, pp. 101–102]
31. **Structure on time intervals, constraints in the syntax.** Musical structures are associated with time
    intervals, and the constraints between them belong to the representation's syntax so that operations
    respect them "for free"; timing transformations are likewise part of the representation, not only
    something done to it. [@honing1993issues, p. 235; @honing2001time, p. 50]
32. **Synchronisation of components, views and media.** Separately encoded parts, notation, audio and
    metadata must synchronise; MX's space-time construct. [@halperin1997afterword, p. 577;
    @barate2009ieee, p. 273; @haus2005music, p. 331; @stewart2011interactive, p. 22; @byrd2003music, p. 45 (score and audio, by measure or better by note)]
33. **Explicit timing in the encoding.** Starting times and durations are given for every note;
    MIDI's implicit timing is the counter-example. [@dannenberg1993music, p. 10; @byrd2003music, p. 50]

34. **Structure behind the visible sign.** Metric structure described independently of the written time
    signature; invisible tuplets represented anyway, since otherwise "the rhythm is not represented
    correctly"; repeat structure (where, when, how often) stored. [@byrd2003music, pp. 53–54]

# 5. Musical values and their mathematics

35. **Accurate pitch and rhythm, with rich pitch.** Absolute accuracy as to pitch and rhythm; pitch
    representation rich enough for everything a general pitch representation must handle, including
    microtones and explicitly encoded transposition and scordatura. [@howard1997plaine, p. 363;
    @dannenberg1993music, p. 4; @byrd2003music, pp. 49, 51; @brinkman1986binomial, p. 44; @pachet1993object, pp. 2–3]
36. **Parametric treatment of pitch, dynamics and articulation.** [@hoglund2014music, p. 33]
37. **Algebraic data types: explicit equality and operations.** Each musical type comes with its notion
    of equality and the operations that capture its behaviour under transformation; many concrete
    representations share software through abstract data types; spelled notes, alterations and
    intervals each have an algebra that keeps enharmonic distinctions while staying arithmetic. [@harley2018abstract, pp. 68–69;
    @wiggins2009computer, p. 8; @harris1991representing, p. 2; @brinkman1986binomial, p. 44; @pachet1993object, pp. 2, 8]
38. **Structure-preserving transformations (transposition, intervals).** Interval relations preserved
    (translational invariance), relative embeddings that transpose, transposition of a segment without
    changing it. [@guo2023domain, p. 5072; @marsden2005generative, p. 411; @dannenberg1993music, p. 5; @howard1997plaine, p. 363]
39. **Separation of dimensions.** Rhythm and pitch represented separately; different kinds of tokens
    (pitch, duration, interval) kept apart; different sign subsets for different parameters.
    [@tanguiane1997score, p. 466; @guo2023domain, p. 5072; @halperin1997afterword, p. 578]
40. **Heterogeneous, variable and missing parameters.** Objects on the same level live in different
    parameter spaces; the number and type of parameters vary per instance; some values are unknown and
    the system stays operable; every field of every symbol has an "unknown" value; data may be implicit, partially specified
    (non-ground) or incomplete, or give only the type of a value. [@zahorka1995predibase, p. 203; @anders2007composing, p. 4; @byrd2003music, p. 50; @huron2002music, p. 11; @balaban1996music, pp. 101–102; @hirata2003computational, p. 75]
41. **Not only numeric points.** Not restricted to point sets in parameter spaces; objects distinct
    from the spaces they live in; a functorial (variable) point of view. [@mazzola2002topos, pp. 47–48]

# 6. Meaning, interpretation and formality

42. **Declarative rather than procedural.** State what is, not how to compute it; procedural
    descriptions are hard to manipulate. [@dannenberg1989music, p. 73; @roland2002music, p. 2; @byrd2003music, p. 43; @honing1993issues, pp. 221, 235]
    (Compare item 93.)
43. **Explicit.** All relations and knowledge stated in the representation, not left implicit; commentary about what an
    encoding contains (e.g. transposed parts) belongs inside the representation; to support
    a feature is to represent its relationships (these parentheses enclose that note), not graphics a
    program must interpret.
    [@roland2002music, p. 2; @pazel2022music, p. vii; @byrd2003music, p. 46; @honing1993issues, p. 235; @huron1992design, p. 34]
44. **Interpretations explicit and separable.** Make interpretations explicit ("to represent is to interpret; and to represent well is to lay
    plain the interpretation"); keep editorial matter
    distinguished from authorial and marked as not in the source; treat suggestions as a separate data
    type that software can ignore or strip; any symbol can be marked as from an alternate (editorial)
    source; editorial decisions form a layer of inferences on top of the source representation. [@roland2002music, p. 2; @halperin1997afterword, pp. 576, 578;
    @hewlett1997musedata, p. 403; @byrd2003music, p. 50; @wiering2016digital, p. 12; @huron1992design, pp. 31–33]
45. **Sources, variants and editions.** Represent all the information in the sources needed to derive
    meaningful views of a work (not just its surface or its logic); keep variants, multiple sources and the
    loss-free original notation; an edition is one view on the sources.
    [@wiering2016digital, pp. 9–11, 18; @byrd2003music, p. 50]
46. **Formal, with provable correctness and well-defined semantics.** As formal as possible; correctness
    provable from the formal definition alone (Roland's wording follows Honing); no ambiguities left by a
    missing formal specification; a defined language of symbols and configurations; every
    concept defined from predefined ones. [@roland2002music, p. 2; @marsden2005generative, p. 410;
    @hirata2022music, p. 162; @pazel2022music, p. 10; @honing1993issues, p. 235; @thomae2024preliminary, p. 45]
47. **Formal description language(s).** A language with primitives and combination operators for
    specifying musical entities and relations within and between surfaces, itself extensible
    (conservatively, preserving soundness), with projection operators. [@wiggins2009computer, pp. 6–7;
    @harley2018abstract, p. 69]
48. **Correspondence and grounding.** Configurations of symbols correspond to things in the world;
    symbols are grounded in real-world counterparts; the model maps clearly to the domain.
    [@marsden2005generative, p. 410; @hirata2022music, p. 162; @pazel2022music, p. vii]
49. **Meaningful differences.** Differences between representations correspond to significant
    differences between the music represented. [@marsden2005generative, p. 411]
50. **Round trip: constructive and derivable.** Music can be created from the representation and the
    representation derived from the music; retranslatable without loss into notation; at least
    "weakly invertible" (the relevant parts reconstructable). [@marsden2005generative, pp. 410–411;
    @howard1997plaine, p. 363; @cella2009symbolic, p. 59]; and able to generate music other than the original
    from it [@cella2009symbolic, p. 59]
51. **Uncertainty and ambiguity.** Represent uncertainty explicitly: disjunction, probabilities on
    disjuncts, in principle continuous distributions; respect the inherent ambiguity of music and of its notation (e.g. a pivot chord functioning in two keys at once).
    [@wiggins2009computer, pp. 8–9; @harris1991representing, p. 7; @milmeister2009rubato, p. 18; @byrd2003music, p. 57; @wolff1977problems, pp. 3, 11; @allen1983maintaining, p. 833; @huron1992design, p. 33 (signifiers marking an insecure interpretation)]
52. **Identity and naming.** Every entity has a unique identifier; names are distinct from objects;
    concepts and instances are named; references are encoded. [@wiggins2009computer, p. 7;
    @mazzola2002topos, p. 48; @milmeister2009rubato, pp. 19–20; @dannenberg1993music, p. 10]
53. **Unique mapping.** No two signifieds may share a signifier; each signified maps to a unique
    signifier. For Huron "the only necessary and sufficient criterion"; every other design principle
    answers human frailty and finite computers. [@huron1992design, p. 16; @roland2002music, p. 3]
54. **Natural, concise expression with efficient reasoning.** [@wiggins1993framework, p. 33]
55. **Inference over the representation.** Operations and inference are defined on what is
    represented. [@wiggins1993framework, p. 33; @wiggins2009computer, p. 7]
56. **Cognitive validity.** Constrained by, and able to incorporate, what music psychology knows about
    how people represent music; afford hierarchy, abstraction and reference as perception does.
    [@pearce2005construction, p. 49; @dannenberg1993music, p. 10; @wiggins2021structure, p. 413]
57. **Similarity.** A theory of similarity, needed for reference between components.
    [@wiggins2021structure, p. 416]
58. **Semantics inferred from the data.** The concepts of the representation learned from the signal
    rather than fixed in advance. [@cella2009symbolic, p. 58]

59. **Analysis stored with the music.** An analytic domain alongside the logical one: analytic parts,
    Roman numerals, figured bass, Schenkerian notation; multiple annotations of one work.
    [@byrd2003music, pp. 49–50, 56–57; @humphrey2014jams, p. 592; @fields2011segment, p. 1;
    @huron2002music, p. 24]

# 7. Views and viewpoints

60. **Multiple viewpoints of the same object.** The same musical object represented in many ways for
    different purposes, explicitly supported; many features of the surface manipulated in tandem.
    [@wiggins1993framework, pp. 33–34; @pearce2005construction, p. 50; @honing1993issues, p. 235; @smaill1993hierarchical, p. 10]
61. **Multiple views; parts as views on the score.** Views fully supported (an edition, too, is a view on its sources), with attributes attachable
    to particular views. [@dannenberg1989music, p. 75; @dannenberg1993music, p. 6; @wiering2016digital, p. 18]

# 8. Extensibility and flexibility

62. **Extensible.** New concepts, structures, types, layers and data can be added (at run time, by the
    user), with extensions that are modular (no change to the original) and concise (no duplication);
    "a primary concern for any representation that hopes to have a shelf life"; extensions backward
    compatible; users can define their own representations and attributes.
    [@dannenberg1993music, p. 3; @zahorka1995predibase, p. 203; @grande1997notation, p. 493;
    @roland2002music, pp. 3–4; @mazzola2002topos, p. 47; @haus2005music, p. 331;
    @anders2007composing, pp. 23, 77; @wiggins2009computer, p. 6; @barate2009ieee, p. 273;
    @selfridgefield2009abstracts, p. 37; @harley2018abstract, p. 69; @byrd2003music, pp. 50, 52; @huron2002music, pp. 11–12; @balaban1996music, p. 108 (modularity); @assayag1999computer, p. 66 (extensible type conversion); @huron1992design, pp. 35–36]
63. **Flexible.** "Tuned" to the information available; accommodate variation between sources, programs, users and uses; most encoding optional, and
    nobody is forced to encode what does not interest them ("represent only what is needed");
    flexible and simple; general where needed, within bounds. [@roland2002music, p. 3;
    @grande1997notation, p. 493; @zahorka1995predibase, p. 203; @alvaro2005ev, PDF p. 12;
    @pazel2022music, p. vii; @byrd2003music, p. 44; @huron2002music, pp. 11, 22; @balaban1996music, p. 101; @huron1992design, p. 34] (Compare item 94.)
64. **Tolerate the "illegal".** No notation element is illegal; minor variants in sources are
    accommodated; measures that disagree with the time signature, and deliberately wrong notation for
    teaching, can be encoded. [@grande1997notation, p. 493; @roland2002music, p. 3; @byrd2003music, p. 44]
65. **Deferred meaning.** Structures can exist before values are assigned, and stay operable.
    [@zahorka1995predibase, p. 203; @anders2007composing, p. 4; @huron2002music, p. 11; @hirata2003computational, p. 75]

# 9. Use: access, manipulation, computation

66. **Purpose-neutral, multipurpose, open to unanticipated uses.** Printing, analysis and sound from one
    encoding; recording, analysis and composition all served; software-neutral; the goals representations serve
    are "legion and unpredictable" and research tasks are open-ended, so favour composable tools over one closed application.
    [@hewlett1997musedata, pp. 402–403; @wiggins1993framework, p. 31; @milmeister2009rubato, p. 7; @huron2002music, p. 22; @wolff1977problems, p. 4; @pachet1996representing, p. 252; @assayag1999computer, p. 59; @huron1992design, pp. 11–12]
67. **Accuracy for recording and archiving.** [@wiggins1993framework, p. 31; @howard1997plaine, p. 363]
68. **Access to structure and to all information.** Structure findable and exploitable; every piece of
    information accessible (e.g. for search strategies); constituent properties efficiently testable;
    standard access functions defined. [@wiggins1993framework, p. 31; @anders2007composing, pp. 5, 78;
    @harris1991representing, pp. 6, 9]
69. **Manipulability for composition and transformation.** [@wiggins1993framework, p. 31;
    @milmeister2009rubato, p. 7; @dannenberg1989music, p. 73; @dannenberg1993music, p. 5]
70. **Rules and constraints in any context.** A user can apply a rule to every conceivable score
    context; rules, patterns, constraints and strategies are representable.
    [@anders2007composing, p. 77; @alvaro2005ev, PDF p. 2]
71. **Represent solutions and support search.** Whatever a solution contains must be representable, with
    building blocks predefined and user-extensible. [@anders2007composing, pp. 77–78]
72. **Efficient computation and search.** Efficient access and modification; efficient search in
    databases; graph structure chosen for efficiency; a universal ordering and search algorithm.
    [@dannenberg1986structure, p. 155; @dannenberg1993music, p. 10; @wiggins2009computer, p. 6;
    @mazzola2002topos, p. 58; @pazel2022music, p. vii]
73. **Database compatibility.** [@mazzola2002topos, p. 48; @zahorka1995predibase, p. 203]
74. **Editing support.** Display kept consistent with the data, controllable redisplay, undo, and user
    modifications preserved in saved files. [@dannenberg1986structure, pp. 154–155;
    @selfridgefield1997beyonda, p. 570]

# 10. Encoding, interchange and sustainability

75. **Interchange without loss; interoperability.** Generalised interchange codes filter attributes out,
    so interchange should be layered by level of detail; conformant systems interoperate; interoperate
    with other vocabularies; user-devised schemes kept "compatible in principle" by shared protocols; undocumented extensions "wreak havoc on interoperability". [@selfridgefield1997beyonda, pp. 571–572; @grande1997notation, p. 492;
    @wiggins2009computer, p. 10; @selfridgefield2009abstracts, p. 37; @byrd2003music, p. 46; @huron1992design, p. 36]
76. **Human-readable, open, non-proprietary.** Readable, intelligible markup rather than proprietary
    binary; a lightweight syntax whose document model matches the data. [@dannenberg1993music, p. 10;
    @haus2005music, p. 330; @barate2009ieee, p. 273; @humphrey2014jams, p. 592; @huron2002music, pp. 11, 22; @huron1992design, p. 24 (a transparent working environment)]
77. **Good code design.** Intuitive, not too verbose, mnemonic (seven kinds of
    mnemonic mapping), consistent in its kind of mapping, easier to read than to write, redundant enough to
    catch errors, error-resistant (with an error detector), economical to type,
    fielded; unique, consistent, non-cryptic, non-context-dependent and idiomatic; closely related to
    notation, with the same contexts as the notation; uniform in design; one line, no second pass. [@halperin1997afterword, p. 578; @roland2002music, p. 3;
    @howard1997plaine, p. 363; @byrd2003music, p. 50; @wolff1977problems, p. 3; @balaban1996music, p. 108; @huron1992design, pp. 17–26]
78. **Low context-dependency.** A fragment cut from an encoding keeps its meaning; one sign, one symbol
    (in "C4" vs "C#4" the "C" means two different things); escape sequences and running octave marks
    are context-dependency that complicates software. [@huron1992design, pp. 28–30; @roland2002music, p. 3]
79. **Attributes encoded separately and merged.** Parallel ("co-lateral") encodings of different
    attributes, structurally identical, so a lyrics-and-rhythm encoding and a pitch-and-rhythm encoding
    combine automatically. [@huron1992design, pp. 35–36]
80. **Simple and learnable.** Usable by non-specialists after brief instruction; simple enough to
    adopt. [@howard1997plaine, p. 363; @humphrey2014jams, p. 592; @alvaro2005ev, PDF p. 12;
    @schlemmer2015unifying, p. 292]
81. **Compact.** Terse, traded against memorability: the more often a sign is used, the shorter it may
    be; the more casual its users, the longer. [@grande1997notation, p. 493; @byrd2003music, p. 50; @huron1992design, pp. 24–25]
82. **Structured enough for complex data.** Hierarchies and mixed data types in the format itself;
    structurally isomorphic to the source (a two-dimensional score in a two-dimensional file, not a
    raster-scanned string);
    push the data structures into the data representation rather than program memory.
    [@humphrey2014jams, p. 592; @huron2002music, p. 23; @huron1992design, pp. 26–28]
83. **A body of encoded music.** A large volume of high-quality encodings is itself a reason to adopt a
    representation. [@huron2002music, p. 11; @roland2002music, p. 2; @wolff1977problems, p. 4]
84. **A schema and self-describing data.** A formal schema for automatic validation and forward
    compatibility; data labelled with its type so each tool knows what it may manipulate, what to leave
    untouched and what is an error. [@byrd2003music, p. 46; @huron2002music, pp. 23–24;
    @wiggins2009computer, p. 7]
85. **Durable and sustainable.** Durability, shelf life, use of well-supported technologies from larger
    communities. [@barate2009ieee, p. 273; @roland2002music, p. 4; @humphrey2014jams, p. 592]
86. **Implementable and matched to the programming environment.** Applications implementable;
    code and programming language matched in advance; workflow integration and cross-language support;
    tools callable from any language, with every step open to the user's own scripts.
    [@haus2005music, p. 331; @halperin1997afterword, pp. 574–575; @humphrey2014jams, p. 592; @huron2002music, pp. 23–24; @huron1992design, pp. 30–31 (idiomatic: grounded in existing and plausible resources)]
87. **Documentation, sources, metadata and provenance.** Sources identified with the encoding; the code
    documented thoroughly and externally; methodology and metadata inside annotations; provenance of data
    and method; support for multiple annotations and tasks; extensible bibliographic metadata; a
    statement of how complete the encoding is. [@halperin1997afterword, p. 579;
    @humphrey2014jams, p. 592; @fields2011segment, p. 1; @byrd2003music, p. 49; @huron2002music, pp. 11, 24; @wiering2016digital, pp. 10–11]
88. **Attach things where they belong.** Secondary marks to their note or chord; each syllable to its
    first note. [@halperin1997afterword, pp. 577, 579; @byrd2003music, p. 46]
89. **Reuse before inventing; international acceptance.** Use an existing code if possible; know others'
    work; aim for international acceptability; don't rewrite software that already exists. [@halperin1997afterword, p. 573;
    @selfridgefield2009abstracts, p. 55; @howard1997plaine, p. 363; @huron2002music, p. 24]

# 11. Stance of the designer

- **Acknowledge what is left out; claim no firm ground; stay in your domain; admit your involvement.**
  [@selfridgefield2009abstracts, p. 55]
- **Choose features for the music and the question.** No code is best for all cases; the music, the
  research question and the programming language determine what to encode; every system sacrifices
  something; no representation can carry every property of what it represents, so "one cannot
  meaningfully discuss the design of representation schemes without some knowledge of how such a
  representation is going to be used". [@halperin1997afterword, p. 574; @selfridgefield1997describing, p. 5;
  @selfridgefield1997beyonda, p. 569; @wiggins1993framework, p. 31; @huron1992design, pp. 9–10, 12]
- **Solve the hardest problems first; design for the extremes.** [@dannenberg1989music, p. 73]; Byrd
  and Isaacson calibrate their numerical requirements to the documented extremes of conventional
  notation [@byrd2003music, pp. 46, 49].
- **Rank requirements.** Required, very desirable and desirable, so judgements at the boundaries
  soften gracefully [@byrd2003music, p. 46].
- **State the encoding's completeness.** What was left out (editorial marks, beams, bowings, MIDI)
  should be recorded with the data [@byrd2003music, p. 49].

# Tensions: where the requirements disagree

90. **What is represented: performance, written signs, or logical content?** Represent "music as
    performed" [@harris1991representing, p. 2]; encode "the written sources, not the (sounding) music"
    [@halperin1997afterword, pp. 574, 576]; encode "the logical content of the score"
    [@hewlett1997musedata, p. 403; @grande1997notation, p. 493]. On pitch the split is sharp: Byrd and
    Isaacson require sounding pitch, which "avoids confounding the essence of the music with details of
    performance" [@byrd2003music, pp. 46, 51], where Halperin encodes the written sign. Wiering, Crawford
    and Lewis give a fourth answer for editions: neither the surface nor the logic, but "all the information
    contained in the source" needed to derive views [@wiering2016digital, p. 11]. The
    multiple-domains requirement
    (item 7) is the usual reconciliation [@babbitt2003use, p. 204; @harley2018abstract, p. 67;
    @wiggins2009computer, p. 7].
91. **Comprehensive vs deliberately selective.** A comprehensive code for a permanent database
    [@wolff1977problems, p. 4; @roland2002music, p. 2; @howard1997plaine, p. 363] against "not intended to be fully complete"
    [@hewlett1997musedata, p. 402], attribute selection as the most important decision
    [@selfridgefield1997beyonda, p. 569; @halperin1997afterword, p. 574] for Huron "the objective of a
    complete representation is chimerical and counterproductive" [@huron1992design, p. 34]; and "acknowledge what is left
    out" [@selfridgefield2009abstracts, p. 55]. Hoglund's "open and comprehensive rather than complete"
    is one middle position [@hoglund2014music, p. 33]; Byrd and Isaacson exclude whole repertoires
    (Augenmusik, graphic scores) but fit their numerical requirements to the extremes of what they keep
    [@byrd2003music, pp. 44, 46].
92. **Value-neutral encoding vs interpretation.** Keep pre-analysis to a minimum and leave
    interpretation to the program [@halperin1997afterword, p. 576] against representations that make
    interpretation explicit [@roland2002music, p. 2] and structural representations whose point is
    analysis [@marsden2005generative, p. 411]. Huron makes DARMS the cautionary tale: claiming to encode the score without
    interpretation only hid the interpretation, and users quietly forked it [@huron1992design, pp. 32–33].
    Byrd and Isaacson ask the question outright and answer
    "at the time of encoding", at least for their setting [@byrd2003music, p. 45]. Both sides agree interpretation must be separable from
    the source (item 44).
93. **Declarative vs generative procedures.** Declarative over procedural [@dannenberg1989music, p. 73;
    @roland2002music, p. 2] against references to algorithms that generate a piece
    [@tanguiane1997score, p. 466] and programs as an alternative representation of static data
    [@dannenberg1993music, p. 8].
94. **Flexibility vs standardisation.** "increased flexibility must be carefully weighed against an
    inevitable corresponding decrease in standardization" [@roland2002music, p. 3]; compare
    international acceptability [@howard1997plaine, p. 363] and tolerance of illegal notation
    [@grande1997notation, p. 493]. Byrd and Isaacson take both sides at once: a schema, and no
    undocumented extensions, but "official" ones welcome and the representation extensible
    [@byrd2003music, pp. 46, 50].
95. **Hierarchy everywhere vs hierarchy within limits.** Hierarchy is the common requirement (item 15),
    but music is hierarchical "only within the bounds of certain specific attributes"
    [@selfridgefield1997beyonda, p. 568], and non-hierarchical reference and cycles are needed too
    [@wiggins2009computer, p. 6; @milmeister2009rubato, p. 18].
96. **Simplicity vs expressive power.** Speed, simplicity, a single typed line and lightweight syntax
    [@howard1997plaine, p. 363; @humphrey2014jams, p. 592] against expressive completeness and
    structural generality maximised together [@wiggins1993framework, p. 41; @tymoczko2026concept, p. 82 ("the right balance between too little and too much structure, between graph and algebra")].
97. **One general representation, or many small ones?** The general lists ask for a single system
    whose expressive completeness and structural generality are maximised [@wiggins1993framework, p. 41;
    @wiggins2009computer, p. 5; @harley2018abstract, p. 66] and a comprehensive code for a permanent
    database [@roland2002music, p. 2]. Huron argued for protocols over schemes from the start [@huron1992design, pp. 5, 36] and, from a decade of Humdrum: "Do not attempt to represent
    everything in one gigantic encoding scheme"; segment the problem so encoding, editing and processing
    stay manageable, and let users concoct task-specific representations [@huron2002music, pp. 11, 22]; for editions, "each
    repertoire will require its own specific representation" under shared interchange requirements
    [@wiering2016digital, p. 13].
98. **Guaranteed consistency, or inconsistency as a fact?** Correctness should be provable from the formal
    definition [@roland2002music, p. 2; @honing1993issues, p. 235], but Honing himself doubts that music can
    be formalised in a way "that guarantees consistency" and suggests truth maintenance [@honing1993issues,
    p. 234]; Wolff wants a code that keeps notation's ambiguities, including durations that contradict the
    metre [@wolff1977problems, pp. 3, 11], and Byrd and Isaacson must encode measures that disagree with their
    time signatures and deliberately wrong notation [@byrd2003music, p. 44].
