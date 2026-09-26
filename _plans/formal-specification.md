# Formal specification: what it would take and what it would be

Status: **scoping only, 2026-09-25. Nothing decided, nothing started.**
Written at the developer's request after `paper/mathy.md`, to make the
question decidable later.

Written for two readers: the developer (to decide), and the agents who would
execute whichever tier is chosen, without this conversation's context.
Every claim marked *(verified)* was reproduced by running code while writing
this; everything else comes from reading the source and tests.

## Context

`paper/mathy.md` states the algebra the code already implements: the tonal
carrier and its two homomorphisms, the duration monoid and its quotient, the
timing graph and its coboundary condition, and the eight distinct equality
relations. The test suite already behaves like an executable specification —
exhaustive sweeps over `tests/domains.py`, Hypothesis properties, a
two-adapter state machine — and four more laws were added on 2026-09-25
(fifths homomorphism, the pitch-pair torsor law, the `distance`-is-a-magnitude
guard, and timing-graph consistency as forest-composition plus cycle
holonomy).

So the useful question is not "should there be a specification" but
**a specification of what, addressed to whom.** OMK's answer is unusual, and
it decides everything else: the library exists to be extended. `Tone`,
`Interval`, `TonalSystem`, `Duration`, `Measurable`, `TemporalSystem`,
`ModalContext`, `UnpitchedTone`, `Clef` and `DivisionShape` are all meant to
be subclassed by someone implementing another musical system, and the
docstrings invite combining "a TonalSystem from one musical culture with the
TemporalSystem from another". Such an implementer currently has docstring
prose and no way to check themselves. That reader — not the paper, not the
maintainer — is who a specification would be for.

## The finding that sets the agenda

*(verified)* The two halves of the library are specified to different depths:

```
Tone             abstract: ['tonal_system']
Interval         abstract: ['tonal_system']
Measurable       abstract: ['rational_length', 'scale', 'temporal_system']
Duration         abstract: ['__neg__', 'temporal_system']
ModalContext     abstract: ['name', 'tones', 'tonic', 'transform']
```

`Measurable` and `Duration` normatively require the operations their laws are
about. `Tone` and `Interval` require nothing but a system tag: no `transpose`,
no `distance`, not even an optional hook (`hasattr(Tone, 'transpose')` is
False). Section 1.1 of `mathy.md` therefore describes a contract the code does
not enforce.

This is not an oversight. `transform_tones` and `ToneCollection.transform`
take the operation as an argument and validate only that the result is a
`Tone` (`apply_tone_operation`), which is exactly what lets an operation
translate *between* systems and lets `SilentTone` pass through untouched. But
it means a tonal system is currently under-specified relative to how the
document describes it, and no conformance kit can be written until this is
settled.

Three ways out, in the order I would consider them:

- **Conventional.** The laws attach to the *operation*, not to the type: a
  tonal system is a tone set together with a monoid of operations acting on
  it, and the conformance kit takes the operation as a parameter alongside the
  domain. Changes no code. Matches how `transform` already works. Makes the
  spec slightly harder to state and much easier to satisfy.
- **A separate optional protocol.** `Transposable` (or similar) that systems
  *may* implement, with the torsor law attached to it; `apply_tone_operation`
  stays the universal path. Systems that implement it get a stronger
  conformance suite; those that do not still conform to the base. Costs one
  small protocol and a branch in the kit.
- **Normative on the ABC.** Add `transpose`/`distance` to `Tone`/`Interval`.
  Strongest guarantee, but every subclass must implement them, including
  `SilentTone`, `UnpitchedTone` and `PercussionTone`, for which transposition
  is meaningless — so it would need an exemption mechanism, which is the
  optional protocol again with extra steps.

My reading is that the middle option is right and the third is wrong, but this
is a design decision with consequences for every future system author, so it
is the developer's to make. It is the one thing that must be settled before
any of the tiers below can start.

## Tier 1 — a normative prose specification

**Product.** A `spec/` directory (or a versioned document beside the paper):
numbered sections, RFC 2119 MUST/SHOULD/MAY, every law with a stable ID —
`TONE-3` for the torsor law, `DUR-7` for scaling exactness, `GRAPH-12` for the
coboundary condition. `mathy.md` is roughly the right content at roughly the
wrong register: it is written to persuade a reader that the model is coherent,
where a spec is written to be conformed to.

**The work is not the writing.** It is deciding, law by law, whether a law is
universal or WSMN's own business. Worked examples of the triage:

- "Transposing preserves octave kind" — WSMN's. Octaves are its carrier's
  third coordinate; another system need not have one.
- "The difference of two tones is an interval carrying the first to the
  second" — universal. This is what makes something a tonal system.
- "Durations compare by rational length" — universal, and already enforced by
  `Measurable`.
- "A dotted value is `2^(k+1)-1` over `2^k`" — WSMN's notation, not a law.
- "An operation on a universal-system tone is the identity" — universal, and
  currently implemented in `NoteEvent.transform_tones` rather than stated
  anywhere.

That last kind is what the exercise is for: laws that live in one
implementation and ought to be promises. Expect the triage to surface a
handful, and expect one or two to be genuine design questions rather than
write-ups.

**Effort.** The writing is largely work the paper needs anyway. The triage is
the real cost and is not parallelizable — it wants the developer's judgement
per law. Call it the dominant term.

## Tier 2 — a conformance kit

**Product.** An importable suite a third party points at their own types:

```python
from openmusickit.conformance import TonalSystemSuite, TemporalSystemSuite

class TestLuteTablature(TonalSystemSuite):
    tones = st.sampled_from(COURSES_AND_FRETS)
    intervals = st.sampled_from(FRET_SPANS)
    transpose = LuteTone.transpose        # or omitted, per the decision above

class TestGongCycle(TemporalSystemSuite):
    durations = st.sampled_from(CYCLE_UNITS)
```

Each law ID from Tier 1 becomes one test method. This is the tier that makes
the specification real: an implementer runs it and gets pass or fail, rather
than reading prose and hoping.

**The work.** Much of the logic exists, but every existing law test is written
against concrete `TonalVector` / `MetricalDuration` and against hardcoded
domains. Two generalizations are needed: the types become parameters, and the
domain becomes a supplied strategy rather than `tests/domains.py`. The
existing split between `tests/domains.py` (finite sweeps) and
`tests/strategies.py` (Hypothesis) is the right shape to copy — the kit needs
both, because some laws want exhaustiveness over a small carrier and others
want sampling over an unbounded one.

Two things worth building in from the start:

- **Traceability.** A CI check that every law ID in the spec has a test method
  and every test method names a law ID. Cheap, and it is the only thing that
  stops the two drifting.
- **A worked non-WSMN example** in the repo — something small and genuinely
  different, a gong cycle or lute tablature — implemented and passing the kit.
  Without one, the kit will silently encode WSMN assumptions, and nobody will
  find out until an outsider tries.

**Effort.** Moderate and mostly mechanical once Tier 1's triage is done. The
risk is not effort but premature generality: writing the kit against a single
implementation is how you get a kit that only that implementation can pass.
Hence the second bullet.

## Tier 3 — machine-checked

Worth it in exactly two places, and not worth it elsewhere.

**Not worth it: the group theory.** Mechanizing the tonal carrier in Lean is
mostly re-deriving `ZMod 7 × ZMod 12` from Mathlib. The interesting content is
not that the group is a group.

**Worth it: the alteration window.** The semitone map and the line-of-fifths
map are homomorphisms *conditionally* — they hold while spellings stay inside
the ±6 window and fail outside it *(verified: exact for all |α| ≤ 3, and
`fifths_position` is exact over all 915 in-domain pairs)*. Proving the exact
boundary, rather than sweeping a finite domain and asserting it holds there,
is a real result and the kind of thing a paper can lead with: the conditions
under which notation's spelling algebra is a homomorphic image of pitch.

**Worth it: the timing graph.** Soundness and completeness of
`check_alignment` with respect to cycle holonomy, that branches and groups
keep the graph a forest, and that `materialize` preserves the induced
subgraph. Alloy suits this well — finite, relational, small scopes — and is
the likeliest of anything here to find an edge case. The new property test
covers the two-line, two-pin case by construction; three or more lines with
overlapping cycles is exactly where a model checker earns its keep and a
property test starts guessing.

**Effort.** A research project, not a maintenance task. Justified only if the
paper's claim becomes "a verified model of notation" rather than "a coherent
one".

## Recommendation

Tier 1 and Tier 2, in that order, gated on the ABC decision. Tier 3 confined
to the alteration window and the timing graph, and only if the paper wants it.

The cheapest first step toward all of it has already been taken: the
pitch-pair torsor law added on 2026-09-25 is the first law written in the form
a *system implementer* must satisfy rather than the form WSMN happens to
satisfy. Rewriting three or four more existing laws in that form, in place,
would prove out the triage criterion before any `spec/` directory exists.

## What it would cost afterwards

A specification is a compatibility surface. Every law becomes a public
promise, changing one becomes a breaking change, and the conformance kit
becomes an API with its own versioning. That is the point — it is what makes
the extensibility claim real — but it is a commitment that outlasts whoever
writes it, and it should be entered knowingly rather than by accumulating
documents.

## Open questions for the developer

1. Does the transposition action become normative on `Tone`/`Interval`,
   optional via a protocol, or stay a property of the operation? (Blocks
   everything.)
2. Is the audience really third-party system implementers, or is it the
   paper's readers? A spec for readers is Tier 1 alone and much cheaper.
3. Does a non-WSMN reference implementation get built, and if so which?
   Without one, Tier 2 is unfalsifiable.
4. Is `spec/` versioned separately from the library, or pinned to it?

## How this analysis was verified

- The ABC table was produced by reading `__abstractmethods__` off the live
  classes, not from the source text.
- Test coverage claims came from grepping `tests/`; `fifths_position` had no
  test-file mention before 2026-09-25, and `test_key.py`'s existing fifths
  test re-implements the formula rather than calling the property.
- The homomorphism boundaries were swept over the full carrier and over
  `tests/domains.py` with its own `in_domain` guard.
- The four laws added on 2026-09-25 were mutation-tested: breaking
  `check_alignment`, making `distance` directed, and wrapping
  `fifths_position` mod 12 each fail the intended tests and nothing else.
