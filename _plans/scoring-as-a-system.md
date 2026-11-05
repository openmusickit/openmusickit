# Should scoring be a third kind of system?

Status: analysis memo, 2026-11-05, revised the same day after discussion.
No code was changed.
Nothing here blocks release.
The namespace in §8 is decided, as a follow-up after 0.1.0;
the rest is a recommendation.

## 1. The short answer

**Do not add a `ScoringSystem` as a peer of `TonalSystem` and `TemporalSystem`.**
Tonal and temporal systems are independent axes, each with an algebra.
Scoring is a vocabulary that sits on top of them:
it has no operations to protect,
it depends on the tonal axis rather than varying freely against it,
and mixing its members is ordinary musical practice rather than an error.
A system tag would have nothing to check,
and on `Mark` it would claim more than anyone can know.

**Do elevate scoring in a smaller, honest sense.**
Say in the documentation what it is (a scoring vocabulary, layered over the two axes),
write down what an implementer provides,
and test that account with a small non-WSMN vocabulary.
Most of the rest has already happened:
`systems/wsmn/scoring/` already stands beside `tonal/` and `temporal/`,
and `docs/basics.md` already speaks of WSMN's "Scoring" system.

**The reasons to want a `ScoringSystem` are real,
but they point at two narrower problems** that can be solved without one:
a `Mark`'s identity includes its prose, which can already lose ties silently,
and `MarkType` puts a Western taxonomy in the core (§9).

**Give marks and tempo terms a namespace: a plain optional string.**
`wsmn:staccato`, `jianpu:staccato` and `adam:epcot_finish` become different marks,
with no one's name privileged and no class, registry or compatibility check.
This also fixes the tie problem, and it is decided as a follow-up after 0.1.0 (§8).
It gives us what a `Mark` system tag was reaching for, and claims far less.

Waiting on a system tag is also the reversible choice.
A tag can be added later in a small commit.
Once it is on 300 symbols and in a file format, it is hard to take off.

## 2. What "system" means in OMK today

The word covers three separate things,
and the question only makes sense once they are pulled apart.

**A package:** a directory under `systems/` with concrete classes and a `symbols` module.

**A contract:** abstract classes that an implementer must fill in.

**An identity:** a frozen `(name, description, universal)` tag,
a `compatible_with` relation, and a property on every value that reports its tag.

Scoring already has the first.
So "elevating" it can only mean adding the second and third.
It is therefore worth seeing what the third does for the two existing systems.
It turns out to differ sharply between them.

**`TemporalSystem` is load-bearing.**
`compatible_with` guards `Measurable.__eq__` and `__lt__` (`values/time/duration.py:160,175`),
duration addition (`systems/wsmn/temporal/metrical_duration.py:662`),
`TimedEdge.nudge` (`graph/edge.py:110`),
and `OmkGraph.add_sync_point` (`graph/graph.py:1898`).
`SyncLine` stores a system as a field, and the MusicXML writer reads it (`io/musicxml/writer.py:808`).

**`TonalSystem` is close to decorative.**
No production code calls `TonalSystem.compatible_with`; only tests do.
The only production read of a tone's system is `.universal`,
so that `NoteEvent.transform_tones` can skip silence (`objects/note_event.py:138`).
The JSON `tonal_systems` table is declared and never consulted:
`Encoder` and `Decoder` have a `temporal_system` method and no tonal one.
Consumers tell tonal systems apart by type (`isinstance(t, TonalVector)`, `writer.py:604`).

The reason for the difference gives us a usable rule.
Temporal classes such as `TemporalUnit` and `CompoundTemporalUnit` are generic:
one class spans many systems, reporting the system of its members.
Everything reduces to a `Fraction` in its own unit,
so without the tag a quarter note and 250,000 microseconds
would compare as two ordinary numbers and give a wrong answer with no error.
Tonal classes are per-system, so the type already says what the tag says.

> **A system tag earns its place when one class spans several systems
> and some operation goes silently wrong if they are mixed.**

The rule is my inference from the code, not a stated decision,
but it predicts both existing systems correctly, and it can be applied to scoring.

Two more facts about the existing arrangement matter here.

The axes are truly independent.
`systems/wsmn/tonal` and `systems/wsmn/temporal` import nothing from each other,
which is what makes the promise in `TonalSystem`'s docstring
(a tonal system from one culture with a temporal system from another) true.

And "musical system" is not one-to-one with anything.
WSMN has two tonal systems (`WSMN`, `WSMN_PERCUSSION`) and one temporal system,
while `CLOCK_TIME` belongs to no musical system at all.
That looseness is a strength, and it is what §5 would strain.

## 3. What scoring is today

`values/scoring/` holds two different patterns.

**Marker classes: `Clef`, `DivisionShape`, `StackGroupShape`.**
Each is `__slots__ = ()` with no members.
Each has exactly one subclass, in WSMN.
They exist so that `objects/` can type a slot without importing `systems/wsmn`.
Consumers dispatch on the subclass and warn about the rest
(`writer.py:943`: "the shape is not a WSMN bracket; it is not written").

**Concrete records: `Mark`, `TempoTerm`.**
These are never subclassed in `src/`.
(The one subclass in the tests, at `tests/io/omk_json/test_json_values.py:266`,
exists to show that JSON refuses it without a codec.)
WSMN supplies instances: 238 marks and 25 tempo terms.
Anyone can mint another, and the reader and every rehearsal letter do.

The core reads very little of any of this:
`attachment_mode` as a guard (`objects/marking.py:44,71`),
`binds` for lyrics (`graph/graph.py:2339`),
and whether a division's `shape` is `None` (`graph/graph.py:797`).
It never reads `Mark.kind`, and never looks inside a clef.
`MarkType` is read only by `io/musicxml` and the JSON codec.

The contents are also conceptually mixed.
In the terms of the domains literature
[@byrd2003music, p. 45; @harley2018abstract, p. 73]:
marks are recorded signs that a performer or realizer interprets (gestural, roughly),
shapes are drawing (visual),
a clef is a map between the two,
and tempo words and rehearsal letters are text.
They are in one package because they are what a score records
that is neither a tone nor a duration.
That is a real and useful grouping, but it is a residue rather than a principle.

The code already describes itself this way.
Four of the five modules in `values/scoring/` use the word *vocabulary* in their docstrings.

## 4. The case for elevating

Each of these deserves a fair hearing.

**Symmetry and teachability.**
"Tonal, temporal, scoring" is a clean story for documentation and the paper,
and it matches how `basics.md` already talks.
This is the strongest argument, and §6 keeps most of its benefit.

**A checklist for implementers.**
Someone implementing chant should be told that clefs, divisions and marks are their job too.
`TonalSystem`'s "complete musical system" list doesn't mention scoring.
Today this is a documentation gap, and documentation fills it.

**Provenance.**
A `BarLineShape` is `wsmn:BarLineShape` on disk, but a staccato is a bare `omk` `Mark`.
Nothing records that it came from WSMN's table,
and the 238 marks are declared by no vocabulary.
This is a real gap, and a namespace fills it without a system object (§8).

**A way to get WSMN assumptions out of the core.**
Also real (§9), and also achievable without a system object.

**A hook for renderers.**
A renderer might want to dispatch on a scoring system.
No renderer exists yet, and the choice of how to draw a graph
belongs to the renderer's caller rather than to the values (§5.10).

**A home for foreign notation, so that people don't abuse the existing one.**
Encoders of mensural music in tools without a place for it
"devised a workaround by using articulation marks not present in mensural notation
that were used to denote specific mensural features"
[@rizovalero2018white, p. 377].
OMK must not leave people doing that.
What prevents it is a clear extension path, and one largely exists:
subclass the marker, mint or subclass the mark,
and declare a `TypeCodec` whose `kinds` include `Clef`, `DivisionShape` or `Mark`.
It needs documenting, and the spike in §6 needs to prove it.

## 5. The case against

### As a musician

**5.1 What distinguishes real notation systems is mostly not in `values/scoring`.**
Notation systems certainly exist as real things:
staff notation, jianpu, kepatihan, tablature, square chant notation,
Bhatkhande notation, tonic sol-fa, Braille music.
But jianpu differs from staff notation chiefly in how it writes *tones and durations*:
numbers relative to a tonic, with dots and underlines,
where the staff has heads on lines.
Its bar lines, slurs and dynamics are largely the ones in our WSMN table,
and it has no clef at all.
Kepatihan and staff transcriptions of gamelan differ the same way.
So the folder holds what notation systems tend to *share*,
and a `ScoringSystem` built from it would not capture what makes jianpu jianpu.
That part lives, if anywhere, in `PitchRepresentation` and in a renderer that doesn't exist.

**5.2 OMK's tonal and temporal systems are already notational.**
`TonalVector` distinguishes C♯ from D♭, which is a fact about writing.
`MetricalDuration` has `dots`.
`TimeSignature` keeps its printed numerals (`('4', '4')`),
and `KeySignature` is in `tonal/`.
Both `WSMN` and `WSMN_TEMPORAL` are named "Western Standard Music *Notation*".
So a third system cannot be "the notation" as opposed to the music.
Notation was factored across all of it,
with whatever had an algebra going to the two axes.

**5.3 Marks have several owners, and notation system is rarely the main one.**
Bowing marks belong to bowed instruments:
erhu parts in jianpu use the same down-bow and up-bow signs as a violin part on a staff.
Pipa signs in jianpu belong to the pipa.
`mf` has travelled nearly everywhere.
The right grouping for a mark cuts across instrument, tradition, period and notation,
and a single `system` field would pick one of these and misdescribe the others.

**5.4 Mixing is normal and carries no error.**
A modern edition of a Renaissance motet may open with a preparatory staff in original clefs,
then continue on a modern staff with Mensurstriche
(a value already in our `GroupBarLines`).
Modern-note editions of chant keep the Solesmes rhythmic signs.
A guitar part gives staff and tablature together.
Putting tones from two tonal systems into one chord is a musical claim that needs justifying.
Putting a chant episema beside a modern bar line makes no claim at all.
Nobody would want an exception for it.

**5.5 Many of the borderline signs refuse to be filed.**
A tie is a curve, a sum of durations (`TiedDuration`), and a binding for lyrics.
Byrd and Isaacson place "beams, ties, octave signs, etc."
"only in the graphical domain" [@byrd2003music, p. 45],
yet our `tie` has `binds=True`, and an octave line changes what sounds.
Ficta marks are about tones, and `rit.` is about time.
Sam and khali in Bhatkhande notation are signs on the page
and also the structure of the tala;
gong signs in kepatihan are signs and also the colotomic layer.
And tablature is the sharpest case.
`TonalSystem`'s own doctest makes "Lute tablature" a *tonal* system,
while `ClefSign.TAB` is in *scoring*.
Both are defensible:
Huron notes that such notations are "closely aligned with the means of performance"
[@huron1992design, p. 14].
A loose folder lets such things be several things at once.
Three named peer systems would make every one of them a dispute about ownership.

### As a system designer

**5.6 There is no algebra.**
A tonal or temporal system is a many-sorted algebra:
sorts (tone, interval; duration) with operations and laws
that `test_tonal_arithmetic` can test exhaustively.
This is the point of abstract data types in the representation literature,
where one represents things
"by way of precisely choosing the mathematical properties which are required of it"
[@harley2018abstract, p. 70].
Scoring has sorts and constants but no operations:
no staccato plus a fermata, no distance between bar lines.
The same source says what non-mathematical information does need:
"the ability to explicitly name the type of such information
and specify how it is accessed" [@harley2018abstract, p. 70].
That is a namespace, and OMK already has one: `Vocabulary`, in `io/omk_json`.

(The nearest thing to a future algebra is the clef,
a map from tones to staff positions.
If a second implementer needs the same operation, that is a trigger; see §7.)

**5.7 Applying the rule from §2, the tag fails both ways.**
On the marker classes, one subclass per system means the type already is the system,
so the tag is redundant: the tonal situation again, with nothing to gain.
On `Mark` and `TempoTerm`, one class does span systems,
so a tag would carry information.
But no operation goes wrong when they mix.
`compatible_with` would have no caller.
The check people imagine is "can this consumer handle this value",
which relates a value to a consumer rather than one value to another,
and it is already handled by type dispatch plus a warning
(`writer.py:943`, `writer.py:1649`).

**5.8 On `Mark`, a system tag claims too much.**
A `system` field says a mark is a member of a system,
and that raises questions with no good answer.
Which system owns the rehearsal letter "A", or a composer's private sign?
They would all fall back to an `ANY_SCORING_SYSTEM`,
so the tag would say nothing in exactly the open part of the vocabulary.
And the compatibility relation would have no use (§5.7).

My first draft went further and said that any such field was harmful,
because a jianpu staccato would be unequal to WSMN's.
That was wrong.
Those are different entries, so inequality is what we want,
and consumers cope by falling back on `kind`.
The problem lies in claiming membership of a *system*.
A namespace claims only which set an entry comes from, and avoids all of this (§8).

**5.9 Scoring is a layer, not an axis.**
The test of an axis is that every combination is valid.
`systems/wsmn/scoring` imports `systems/wsmn/tonal`,
because `StaffClef.reference_tone` returns a `TonalVector`.
This is a single import, and nothing calls `reference_tone` yet,
but it isn't incidental:
the abstract `Clef` is defined as "so that a position on the staff is a pitch".
A staff clef in a 19-tone tonal system cannot return that `TonalVector`.
Calling scoring a peer would extend the mix-and-match promise to something that can't keep it.

**5.10 Part of scoring is a view, and a tag would store the view on the values.**
SMDL's founding move was that
"the visual or gestural domains may consist of any existing or future data-content notation
and may be linked to any piece of logical information in the cantus"
[@sloan1997hytime, p. 471],
and Huron separates "common musical notations (abstractly conceived)"
from their "specific visual ... renderings" [@huron1992design, p. 14].
One graph may be drawn several ways,
so which scoring to use is partly the caller's choice at output time.
But OMK also records what sources assert,
so a clef change in a manuscript is data, and the values stay.

This suggests that the real future pressure lies elsewhere.
A `ClefEvent` sits in the line's `NEXT` chain.
A viola and a cello doubling through `Stint`s read one line and so one clef,
though on paper they have alto and bass.
`Stint.transposition` lets a Part read shared events differently,
and nothing similar exists for how they are written.
A staff with tablature beneath raises the same question.
A `ScoringSystem` tag would not help with any of this.
I have not tried to solve it here;
it needs its own discussion when a renderer exists.

**5.11 It makes the boundary expensive.**
Today, misfiling something costs a file move.
With a contract and a format entry behind it,
each case from §5.5 becomes an API and file-format decision.
It would also make a `MusicalSystem` triple the obvious next step,
then "a score has a scoring system",
which contradicts both "there is no `MusicalSystem` class"
and the graph's freedom to hold objects from any system together.

## 6. Recommendation: what we would do

1. **Say what scoring is.**
   Change the documented definition to something like:
   a musical system is realized as one or more tonal systems, temporal systems,
   and a scoring vocabulary.
   The first two are independent axes with an algebra;
   the vocabulary is a layer that records everything else a score states.
   This touches the "Musical System" and "Scoring" sections of
   `docs/abstract_music_primitives.md` (the latter is a stub),
   the wording at `docs/basics.md:73`,
   and the "complete musical system" list in `TonalSystem`'s docstring.
   That list omits scoring,
   and its "base classes for these do not exist yet" is partly out of date.
   The two docs are your uncommitted drafts, so I left them alone.

2. **Settle the words.**
   Keep `scoring` as the package name, and say "scoring vocabulary" in prose.
   Avoid `ScoringSystem` on naming grounds alone:
   a programmer reads it as something that awards points,
   and a musician may hear "scored for strings".
   `docs/overview.md` also uses "scoring" differently ("Time, Space, and Event-driven scoring").
   Stop saying "notation system" in `values/scoring` docstrings,
   since by §5.2 tones and durations are notation too.

3. **Write the implementer's contract in prose.**
   For each slot (`ClefEvent.clef`, `DivisionEvent.shape`, `StackGroup.shape`,
   `Marking.mark`, `MarkSpanner.mark`, `TempoEvent.term`):
   what it means, what to subclass or mint, how to declare a codec,
   and that every part is optional and foreign values are expected.
   Consumers dispatch on type and warn.
   Leave the marker classes empty for now,
   since with one implementer any abstract member would just be WSMN's shape.

4. **Test it with a small non-WSMN vocabulary.**
   Do this before adding any more abstraction.
   `_plans/json-serialization.md` and `_plans/formal-specification.md`
   both already want a non-WSMN example, so this can serve all three.
   Two cases stress it in opposite directions:
   square chant notation, which needs its own clefs, divisions and marks,
   and jianpu, which should reuse WSMN's marks and bar lines and has no clef.
   Things to find out:
   whether the slots fit;
   whether the empty markers need a member;
   whether `MarkType` hurts;
   whether jianpu's reuse is comfortable;
   where the signs that don't fit end up;
   and above all, whether a tag would have caught any real mistake.

5. **Add the namespace after 0.1.0 (§8), and let the spike decide `MarkType` (§9).**
   The namespace doesn't need to wait for the spike.

## 7. What problems this creates

The recommended path has real costs.

**An asymmetry that has to be explained.**
Readers will ask why there are two system classes and a third thing that isn't one.
The answer is good but takes a paragraph, while "three systems" takes three words.

**No enforcement.**
Empty markers give implementers no help from the type checker,
and the conformance suite in `formal-specification.md` would have nothing to test here.
Mistakes will show up as warnings from consumers.

**Two related ideas share similar words.**
A JSON `Vocabulary` is published and versioned, and defines types.
A namespace is a bare string that names a set of marks, with no version.
Neither replaces the other, but readers will confuse them,
and `wsmn` spells both (§8.5).

**A grab bag stays a grab bag.**
Signs that are performed and shapes that are only drawn remain in one package.
They may want separating, but with one implementer I can't tell where the line should go.

**The layer claim could turn out wrong.**
It rests on one implementation plus my reasoning about others.
The spike exists to test it, and may never get done, since nothing forces it.

The namespace has its own problems, listed in §8.8.

### If we went ahead with a full `ScoringSystem` anyway

The code is not large:
the tag and `ANY_SCORING_SYSTEM` in `values/scoring`, a `WSMN_SCORING`,
an abstract `scoring_system` property on the three markers (which become ABCs),
a field on `Mark` and `TempoTerm`,
a third table on `Vocabulary`, updates to `io/omk_json` and the two spec pages, and tests.

The problems it would create are the ones in §5:
a field on `Mark` claiming membership that no one can establish (§5.8),
when a namespace already does the useful part (§8);
a policy for all minted marks, including every mark the MusicXML reader mints;
a `compatible_with` nothing calls, and another JSON table nothing reads,
repeating `TonalSystem`'s situation;
boundary disputes that are now API questions (§5.11);
and a promise of mix-and-match that a clef can't keep (§5.9).

### What would change my mind

Any of these would be strong evidence, and I would reopen the question if one appeared:

- A real case where values from two scoring vocabularies meet and something goes
  *silently wrong*, in a way that type dispatch can't catch.
- An operation shared by two or more implementers,
  such as a clef's map from tones to positions, so that there is an algebra to guard.
- A generic class in the core whose behaviour must vary by vocabulary.
- A second implementer reporting that the missing system object actually got in their way.

## 8. A namespace for marks and tempo terms

This came out of discussing the first draft of this memo.
The developer's decision on 2026-11-05: do it, as a quick follow-up after 0.1.0.
What follows is the design as I would build it, with its consequences.

### 8.1 The two problems it solves

**A `Mark`'s identity includes its prose, which silently loses ties.**
`Mark` compares on all fields, including `description`.
JSON writes those fields inline,
and the MusicXML writer recognizes marks by equality with the table
(`mark == scoring.tie`, `io/musicxml/writer.py:1309`, and many others).
So if a later release rewords a description in `scoring/symbols.py`,
marks in files saved earlier stop equalling the table's marks,
and no vocabulary version changes to signal it.

I tested the writer half of this directly,
by building a small graph (not by reading an old JSON file)
with `tie` and with `replace(tie, description=...)`:

- As shipped: two `<tie>` and two `<tied>` elements.
- Description reworded: no `<tie>` or `<tied>` at all.
  The tie comes out as the word "tie" in a `<words>` direction with dashes,
  and the only warning is the same one about bar lines that the control case gives.

The JSON plan identified this very hazard for systems (§2.3):
"Writing a system out as its three fields would put prose into data".
Marks and tempo terms didn't get the same treatment.

**Nothing can tell WSMN's staccato from anyone else's.**
Today a jianpu `Mark(name="staccato", ...)` differs from WSMN's only by accident,
through its prose.
Fixing the first problem by dropping prose from equality would make the two equal.
The usual way out is a prefixed name such as `jianpu_staccato`,
which makes WSMN the unmarked default, the very thing OMK exists to avoid.

Each problem makes the other worse, so they should be solved together.

### 8.2 The design

`Mark` and `TempoTerm` gain one optional field, a plain string:

```python
# what WSMN's table does
staccato = Mark(name="staccato", namespace="wsmn", description=..., kind=..., ...)

# a tradition's own entry: same name, a different mark
staccato = Mark(name="staccato", namespace="jianpu", description=..., kind=..., ...)

# a composer's private sign
epcot_finish = Mark(name="epcot_finish", namespace="adam", description="...", ...)

# no published set at all: a rehearsal letter, a word from a file
Mark(name="A", kind=MarkType.REHEARSAL)
```

In prose, these can be written `wsmn:staccato` and `adam:epcot_finish`.

The rules:

- **Identity.** `description` and `aliases` leave equality and hashing
  (`field(compare=False)`).
  Equality is then `namespace`, `name`, `kind`, `attachment_mode` and `binds`.
  For `TempoTerm` it is `namespace` and `name`.
  There is precedent for stored fields that `==` ignores:
  `ToneCollection` leaves out `name_template`, and `Chord` leaves out `suffix`.
- **`None` means no published set.**
  This matches how OMK reads `None` elsewhere.
  It is the default, so everything minted today stays valid,
  and it privileges no one.
  There is no `ANY` placeholder.
- **A grammar.** A namespace matches `[a-z][a-z0-9-]*`,
  the grammar JSON already uses for vocabulary prefixes,
  checked in `__post_init__`.
  This catches `"WSMN"` and `"wsmn "` and rules out colons,
  so `adam:epcot_finish` is never ambiguous.
  Starting strict is the reversible choice:
  a grammar can be relaxed later, and can't be tightened.
- **Nothing resolves it.**
  There is no registry and no lookup, and no declaration is needed.
  Anyone may make one by using it.
  A module of constants is a convenience and is never required.
- **The core never reads it.**
  `graph/` and `objects/` keep acting on `binds` and `attachment_mode`,
  so a jianpu slur with `binds=True` works with lyrics exactly as WSMN's does.
  Only modules that know a format or a system may look at a namespace.
- **WSMN's constant** is `WSMN_SCORING = "wsmn"` in a new `systems/wsmn/scoring/wsmn.py`,
  alongside the `wsmn.py` modules of `tonal/`, `temporal/` and `percussion/`.
  Keeping it out of `symbols.py` keeps it out of `from ... import *`.
  `wsmn` is reserved by documentation only.

### 8.3 Why a string rather than a class

The developer's instinct is right, for four reasons.

**A class would have nothing to hold.**
Its only field would be the name.
A description is exactly the prose we are removing from identity,
and there is no behaviour to put on it.

**A self-contained document stays self-contained.**
The spec says marks are "written in full, never by name,
so a document does not depend on any table of marks".
That is what lets a score full of Adam's marks open on any machine,
with no code of Adam's and with all of his descriptions.
A declared object would need a table on `Vocabulary`,
and `Decoder` refuses any vocabulary it wasn't given,
so private marks would make scores unreadable by others.

This retracts two costs I raised in discussion:
with a string, `Vocabulary` needs no third table,
and using a ready-made mark doesn't oblige a document to declare `wsmn`.
It also retracts the option in my first draft of writing marks by name,
which the spec had already rejected.

**Reprs stay short and evaluable.**
`Mark(name='staccato', namespace='wsmn', ...)` needs no imports.

**Making one is trivial,** which is the point for a private sign.

What we give up: a typo such as `"wsnm"` is a valid and different namespace,
and the type checker sees only `str`.
Going through a symbols module or a constant avoids most of that.

### 8.4 Why a field rather than `name="adam:epcot_finish"`

The name is what gets printed.
Visualization labels use it,
and the MusicXML writer puts it in `<other-articulation>` and `<words>`,
so a prefix would leak onto the page, and every consumer would have to parse it.
It would also be ambiguous,
because minted names are arbitrary text from files,
and a word in a score can contain a colon.

### 8.5 What a namespace does not mean

These limits are what keep it from growing back into a `ScoringSystem`.

- **Not a system.** It has no `compatible_with`, and there is nothing to refuse.
  Marks from any namespaces may sit together on one note.
- **Not ownership of the sign.**
  It says which set this entry comes from, not whose sign it is (§5.3).
- **Not authorship of the placement.**
  `adam:epcot_finish` names a vocabulary entry.
  It doesn't say Adam put it on this note.
  Whether a slur is the composer's or the editor's is a fact about the `Marking`,
  and must not be pushed in here.
- **Not a JSON prefix.**
  A document's prefixes are local and stand for URIs.
  A namespace is an ordinary string value, compared as written.
  `wsmn` happens to spell both, and the spec must say they are unrelated.
- **Not on clefs or shapes.**
  Those have a subclass per system, so the type already says this (§5.7).
  A private clef or bar line still needs a subclass and a codec.

### 8.6 Borrowing or defining

Every vocabulary author now makes a real musical decision for each sign:
is this the same mark as an existing one?

The rule of thumb: reuse an entry when you mean the same sign with the same meaning,
and define your own when either differs.
A jianpu symbols module should simply re-export WSMN's `mf` and `tie`.
It should define its own staccato if, as I recall, jianpu writes it as a wedge.

This has teeth, because the choice decides what consumers can do.
A `jianpu:tie` is not a tie to the MusicXML writer,
which would write it as words and lose the tie.

### 8.7 Implications

**Equality.**
Two marks differing only in prose become equal,
in sets, in dict keys and in `OmkGraph.is_equivalent`.
Each `Marking` still holds its own record, so nothing is lost from the graph,
but two graphs differing only in a mark's description will now count as equivalent.
Two private marks with no namespace that relied on prose to differ will merge;
that is now what a namespace is for.

**JSON.**
`Mark` and `TempoTerm` gain a required `namespace: string?`,
since a codec's fields must match exactly (`io/omk_json/vocabulary.py:323`).
This changes the `omk` vocabulary, so 0.1 becomes 0.2.
Before 1.0 a reader accepts one exact version,
so files saved in format 0.1 are refused with a clear error naming the version.
We won't write a migration, by the developer's decision:
there will be about zero such files.
The JSON tests compare structure rather than `==` (`_plans/json-serialization.md` §2.4),
so they keep seeing `description` and `aliases`.
Files to update: `docs/spec/vocabulary-omk.qmd`, `docs/spec/schema/omk.schema.json`,
and the two example documents, which `tests/io/omk_json/examples.py` regenerates.

**MusicXML, writing.**
MusicXML is a WSMN format with no place for a namespace.
In my probe, a foreign mark and a private mark both went out with no warning
about what they lost.
Two warnings fix this:
- A mark in another namespace falls back by `kind`, as now,
  and the writer warns that the namespace is not carried.
- A mark claiming `wsmn` that doesn't match the table
  means either a stale file or a mark from a newer table.
  Today that case can't even be detected, because it looks like a minted mark.
  This turns the failure in §8.1 from silent into reported,
  including when a later release edits a shipped mark's `kind`.

**MusicXML, reading.**
I tested the round trip with marks made today:
a foreign `staccato` is written as `<other-articulation>staccato</other-articulation>`,
and on reading back it comes out *equal to WSMN's staccato*,
because the reader looks text up in its tables.
A private mark comes back with its description gone.
With namespaces, both would also lose the namespace.
This is inherent to the format, and the write-time warning is the honest answer.
JSON is the format that keeps these marks.

Marks the reader re-mints with a changed attachment mode
(`io/musicxml/reader.py:1393`, `1540`, `1544`, `1589`) should stay `None`.
They aren't table entries, and they don't keep the description today either.

**Tests.**
- Every shipped mark and term has `namespace == WSMN_SCORING`.
- Equality and hashing ignore prose and respect namespace.
- The namespace grammar, with Hypothesis on both sides of it.
- JSON round-trips the field, and refuses a bad one.
- The probe from §8.1 becomes a regression test: a reworded `tie` is still a tie.
- The new MusicXML warnings fire.
- `test_repr_round_trips` picks up the new field by itself,
  and `tests/strategies.py` needs to generate it.

**Mechanical changes.**
263 symbols gain the field,
reprs and their doctests grow slightly,
and `Mark`'s and `TempoTerm`'s docstrings explain the idea.
The docstrings say "notation system" today, which §6 wants changed anyway.

### 8.8 Problems this creates

**Collisions have no authority behind them.**
Two packages can both choose `chant`.
The format's rigorous answer is a URI, and I am deliberately not using one here.
The stakes are low:
two marks are only equal if name, kind, mode and `binds` all match too,
and marks are descriptive, so the worst outcome is two similar signs compared as one.
If that ever matters, the grammar can be relaxed to allow longer names.

**Finding a sign across vocabularies gets harder, on purpose.**
`==` no longer finds "every staccato" across traditions.
`kind` is the only rough route, and a real mapping would be separate work,
perhaps with the conversion class in `_plans/ideas.md`.
This also means §9 now has a cost it didn't have before.

**Borrow-or-define decisions can fragment data.**
Authors who define where they should borrow
produce marks that no tool recognizes (§8.6).

**A shipped mark's `kind`, `attachment_mode` and `binds` become part of its identity.**
Editing one still makes old records unequal to the table.
That is correct, since it changes what the mark means,
and the new warning reports it, but only in the MusicXML writer.
A namespaced mark could instead be identified by namespace and name alone.
I decided against that because it needs a hand-written `__eq__`,
and because two marks that are equal but disagree on `binds` would behave differently.

**ASCII-only namespaces.**
Non-Latin scripts can't be used,
which sits awkwardly with OMK's aims, though only for the identifier:
`Mark(name="跳音", namespace="jianpu")` is fine.
JSON prefixes make the same choice.
I'd start strict, but this is a judgement call the developer may want to reverse.

**It will be tempting to use it for more.**
Each thing in §8.5 is an obvious next idea.
The rule that the core never reads a namespace is the main protection.

### 8.9 Timing

0.1.0 ships today without this.
The hazard in §8.1 stays dormant as long as nothing in the marks table changes,
so **don't edit any `description` or `aliases` in `scoring/symbols.py` until this lands.**
The follow-up should land soon, because each file saved in format 0.1
is one that the version bump will refuse.

It is a multi-commit piece of work, so run the heavy test set at the start and end.
A sensible order:
equality, then the field and the WSMN table,
then JSON and the spec with the version bump,
then the MusicXML warnings,
then the docs.

This does not depend on the spike in §6, and can come first.
The spike would be the first real user of a second namespace,
and might show this design needs adjusting.
With only one published namespace,
the design's main claim, that it disambiguates without privileging anyone,
remains untested until then.

## 9. `MarkType` is a Western taxonomy in the core

`MarkType` is a closed enum in `values/scoring`,
with members such as `BOWING`, `FICTA` and `REHEARSAL`,
and the JSON codec decodes it against that closed set.
So an extension can't add a kind without changing the core and the `omk` vocabulary,
which is what the architecture section of `AGENTS.md` asks us to avoid.

It also makes small theoretical claims on other traditions' behalf.
Filing a Carnatic gamaka under `ORNAMENT` calls it decoration,
when it is widely regarded as constitutive of the raga.
`kind=None` and `OTHER` give an escape, but a second-class one.

The core never reads `kind`;
only `io/musicxml`, which knows WSMN anyway, acts on it.
So there is room to move it.
One option is to make `kind` an open value on the marker-class pattern, with WSMN's enum in WSMN.

Namespaces add a consideration in the other direction.
Once `==` stops matching across vocabularies (§8.8),
a shared `kind` is the only thing that lets a query find
"every articulation" across traditions, and it is what the MusicXML writer falls back on.
An open or per-namespace `kind` would give that up.
I'd let the spike decide whether the enum actually hurts.

## 10. Limits of this analysis

The code claims above were checked against the current tree,
and the quotations were verified against the research corpus.
The MusicXML results in §8.1 and §8.7 come from small probes run against the current code.
The design in §8 has not been built, so its effects are reasoned rather than observed.

My claims about jianpu (including its staccato), kepatihan, Bhatkhande notation,
erhu and pipa signs, gamaka, and editorial practice in chant and mensural editions
come from general knowledge and were not checked against sources.
They should be checked, ideally with practitioners, before any of this reaches the paper.

The rule in §2 is my own reading of why the two tags differ,
and no earlier plan states it.
