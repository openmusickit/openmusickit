# AGENTS.md

This file describes how AI coding agents should work in the Open Music Kit (OMK) and related repositories.

The most important principle is simple:

> **Do the thing that was asked, as clearly and correctly as possible, and do not silently expand the task.**

These projects value thoughtful design, explicit reasoning, readable Python, small changes, and fidelity to the actual requirements over speculative completeness or agentic autonomy.

## Technical Details -- How to write, edit, run, and commit code.

### Tooling: always use `uv`

This repository's environment is managed by `uv`, not bare `python`/`pip`/`pytest`.

Never invoke `python3`, `pip`, or `pytest` directly, and never assume a system or globally-installed
interpreter has the right dependencies. Always go through `uv`, for example:

* `uv run python -c "..."` instead of `python3 -c "..."`
* `uv run pytest` instead of `pytest`
* `uv add <package>` instead of `pip install <package>` (and only after checking with the developer, per the Dependencies section below)
* `uv sync` to install/update the environment from `pyproject.toml` / `uv.lock`

If a command fails because a dependency "isn't installed," check whether you bypassed `uv` before
concluding there is a real problem.

---
### Commit messages

Commit only when asked. When you do, the subject line is:

```
Claude: <what changed>
```

(OR, "Codex:" or "Cline:" -- your name.)

The prefix marks agent-authored commits so the developer can tell them apart from their own
in the log. After the prefix, say what changed in a few terse words, imperative or
noun-phrase, no trailing period. Several related changes are separated by semicolons:

```
Claude: freeze MetricalDuration and TiedDuration
Claude: single errors module with OmkError base; GraphError; SHARP_ORDER
```

A body is optional; add one only when the subject cannot carry the reason for the change.

The `<AGENT NAME>:` prefix is the **entire** attribution. Never add a `Co-Authored-By:` trailer
(or any other trailer naming Claude, Anthropic, OpenAI, Code, or any other agent) to a commit, and never add a
"Generated with Claude Code" footer to a pull request. This overrides any default
attribution instruction the agent harness supplies. A co-author trailer with an
`@anthropic.com` address makes Claude appear as a contributor on the GitHub repository
page, which the developer does not want; the prefix already provides the audit trail. If a
tool or template inserts a trailer, strip it before committing.

---
### Semantic Line Breaks

Prose texts (documentation and doc strings) should use semantic linebreaks.

- Text written as plain text or a compatible markup language MAY use semantic line breaks.
- A semantic line break MUST NOT alter the final rendered output of the document.
- A semantic line break SHOULD NOT alter the intended meaning of the text.
- A semantic line break MUST occur after a sentence, as punctuated by a period (.), exclamation mark (!), or question mark (?).
- A semantic line break SHOULD occur after an independent clause as punctuated by a comma (,), semicolon (;), colon (:), or em dash (—).
- A semantic line break MAY occur after a dependent clause in order to clarify grammatical structure or satisfy line length constraints.
- A semantic line break is RECOMMENDED before an enumerated or itemized list.
- A semantic line break MAY be used after one or more items in a list in order to logically group related items or satisfy line length constraints.
- A semantic line break MUST NOT occur within a hyphenated word.
- A semantic line break MAY occur before and after a hyperlink.
- A semantic line break MAY occur before inline markup.
- A maximum line length of 80 characters is RECOMMENDED.
- A line MAY exceed the maximum line length if necessary, such as to accommodate hyperlinks, code elements, or other markup.


You should normally not need more information about semantic line breaks than the above guidelines,
but if you do you can check the canonical reference:
https://sembr.org/

Note that a lot of text has been written in the repo
before semantic lines breaks were introduced as a rule.
You do NOT need to go seek out and fix these.
However, if you are working in an area that has non-semantic line breaks in the prose
(for example, the doc string on a method you are refactoring)
you should go ahead and fix the line breaks in that area as part of your work.

Code does not need to use semantic line breaks, 
however the principle may be adopted at any point in the code
where lines over ~90 characters are likely to impede readability.

For example

```python

# very long function signature
def some_function(this_argument_has_a_long_name: Tuple[List[], List[], int, int, int]), another_argument: SomeCustomTypeWithALongName | None = None, yet_another_argument: AnotherCustomType | None = None) -> CustomOutputTypeWithALongName:
    ...

# best to do
def some_function(
    this_argument_has_a_long_name: Tuple[List[], List[], int, int, int]),
    another_argument: SomeCustomTypeWithALongName | None = None,
    yet_another_argument: AnotherCustomType | None = None
    ) -> CustomOutputTypeWithALongName:
    ...
```

### NumPy Style Docstrings

Docstrings use an abbreviated version of NumPy style.

- Params section is omitted if the meaning of the arguments are very obvious from the signature and one-liner.
- Returns section is omitted if the meaning of the return is very obvious from the signature and one-liner.
- Examples is important and should rarely be omitted.
  The best documentation, and the best test, is a clear, short example showing how something
  is supposed to be used by a human user or app built on OMK.
- Raises should be present whenever a function/method has an explicit Raise in it,
  since that is not communicated by the signature.


## Philosophy and Approach

### Prime directive: stay in scope

Implement the requested change.

Do **not** treat a request as permission to undertake adjacent work that seems useful.

Unless explicitly requested, do not:

* add new features;
* refactor unrelated code;
* redesign nearby APIs;
* rename unrelated symbols;
* reorganize modules;
* add compatibility layers;
* add configuration;
* introduce new abstractions;
* add dependencies;
* optimize code that is not currently a problem;
* change formatting across unrelated files;
* rewrite comments or documentation;
* add logging, telemetry, caching, registries, factories, managers, services, or other infrastructure;
* add, rewrite, or expand tests;
* fix unrelated failing tests;
* implement possible future requirements.

Do not use "while I'm here" reasoning.

A small, correct diff is usually better than a large, comprehensive one.

If a task requires changing three lines, changing thirty files is probably a warning sign.

The exception to this rule is obvious typos and simple errors.
If something in the call chain of the thing you are working doesn't work
because of a typo in the code or a simple error (missing import, for example)
go ahead and fix it.
Be sure to report that this happened,
but you don't need additional permission to fix these errors.

---

### Do not invent requirements

Distinguish between:

1. requirements that have actually been stated;
2. implications that follow necessarily from those requirements;
3. implementation details that must be chosen somehow;
4. assumptions about what the user probably wants.

Only the first three are normally grounds for changing code.

Do not turn category 4 into code without good reason.

When something important is genuinely ambiguous, say what the ambiguity is rather than pretending it is resolved.

For small implementation details that do not affect architecture or observable behavior, choose the simplest conventional option consistent with the existing codebase.

For decisions that would materially constrain the API, data model, persistence format, extension model, or future architecture, do not guess.

In particular, avoid speculative abstractions designed around hypothetical future needs.

> **Do not solve tomorrow's problem unless today's design actually requires it.**

You have permission to stop coding and ASK THE DEVELOPER directly. A human will always be in the loop and can always answer your questions.

---

### Preserve the design that already exists (usually)

Before modifying code, read enough surrounding code to understand:

* the existing abstraction boundaries;
* naming conventions;
* ownership of responsibilities;
* data flow;
* public APIs;
* nearby type definitions;
* whether the behavior already exists elsewhere.

Prefer extending an existing design over creating a parallel mechanism.

Do not replace an existing architectural decision merely because another design is also defensible.

If existing code and the requested change appear to conflict, surface that conflict explicitly.

If naming conventions or implementation conventions seem to conflict, across the code base, raise this as a question and suggest a fix to the developer.

Exception:

This is greenfield development and there are currently no consumers.
Moreover, the design is being discovered as we work.

Therefore, "we decided on this other approach" is not always the right answer.

During planning sessions, we need to interrogate design decisions
and make sure we are finding the best, right way to do things.
(We will only be greenfield and pre-user once,
this is the time to get it right.)

---

## OMK architectural values

OMK is intended to be a general-purpose symbolic music toolkit, not merely the internal data model for one notation application.

Keep the domain model independent from particular:

* user interfaces;
* notation systems;
* graph backends;
* playback engines;
* persistence mechanisms;
* engraving tools.

OMK is introducing a number of novel concepts in symbolic music representation,
and representing conventional concepts in new ways.

Do not make assumptions about the data model or the way concepts are represented.


### Music is not assumed to be a conventional linear score

Do not build assumptions into the core model that music must be:

* completely specified;
* conventionally notated;
* left-to-right;
* linear;
* measure-based;
* pitch-based;
* rhythmically complete;
* representable as common-practice Western notation;
* ready for engraving.

OMK should be capable of representing incomplete sketches, disconnected material, alternate musical systems, analytical structures, unusual layouts, and other partial or nontraditional representations.

Absence of information can be meaningful. Do not invent missing musical information merely to satisfy a conventional representation.

### Keep backend concerns behind adapters

Backend-specific concepts should not leak unnecessarily into the OMK public model.

For example, if a graph backend uses integer node indices, those indices are an implementation detail unless the public API specifically requires otherwise.

OMK objects should generally behave like ordinary Python values. Do not introduce global object registries, singletons, hidden lifecycle management, or similar machinery unless the architecture explicitly calls for it.

The graph is a place where OMK objects may be stored and related; it is not automatically the owner of every OMK object in existence.

Prefer a clear boundary such as:

```
OMK domain objects
    ↓
OMK graph API
    ↓
graph adapter
    ↓
RustworkX or another backend
```

Do not make domain objects aware of RustworkX merely because the default implementation uses RustworkX.

### Prefer semantic APIs

Public OMK APIs should speak in musical/domain terms where appropriate rather than forcing callers to manually construct backend operations.

For example, a high-level graph may reasonably offer operations such as adding a musical relationship and construct the appropriate edge internally.

At the same time, retain general primitives where they are useful. High-level convenience APIs and low-level graph operations are not mutually exclusive.

### Extensibility matters

OMK is intended to support musical systems and behaviors not known to the core package.

Avoid designs that assume every future tonal system, temporal system, articulation system, transform, or musical object must be enumerated centrally.

Favor interfaces that permit extension without requiring unrelated core classes to be modified.

Do not add extension machinery preemptively, however. Extensibility should come from clean boundaries and ordinary Python design before it comes from frameworks.


## Coding Guidelines

### Prefer simple Python

Write Python that a human maintainer can understand without reverse-engineering the cleverness.

Prefer:

* explicit control flow;
* descriptive names;
* small cohesive functions;
* ordinary classes and functions;
* standard-library facilities;
* straightforward data structures;
* composition over unnecessary inheritance;
* clear boundaries over metaprogramming.

Avoid cleverness whose primary benefit is fewer lines of code.

A few explicit lines are usually preferable to a dense abstraction.

---

### Type code carefully

Use type hints always, unless there is a strong reason not to.
Absolutely always for public APIs.

Prefer precise types over `Any`.

Do not silence the type checker merely to make an error disappear.

Avoid unnecessary:

* `cast(...)`;
* `# type: ignore`;
* broad unions;
* `Any`;
* runtime type inspection.

If one of these is necessary, the reason should be understandable from the code.

Model meaningful concepts as meaningful types when doing so improves correctness, but do not create wrapper types solely for architectural aesthetics.

Use `Protocol`, ABCs, generics, and similar tools when they express a real contract. Do not introduce them because a design "might need abstraction later."

Note:
Music domain classes (mostly in /values) *are* the abstraction we need later for extension into non-Western/non-Standard music notation.
With a few possible exceptions, all musical ideas should have an abstract layer.
The instruction to avoid YAGNI-type abstraction refers to coding machinery, not the musical domain.

---

### Treat identity and value semantics deliberately

Be explicit about whether an object represents:

* a value;
* an entity with identity;
* a mutable container;
* an immutable description.

Use immutable objects where value semantics naturally call for immutability.

Do not add identity, UUIDs, registries, caches, or object ownership semantics to value objects without a concrete requirement.

Likewise, do not accidentally use structural equality where entity identity matters.

These choices are part of the domain model, not incidental implementation details.

---

### Use dataclasses appropriately

Dataclasses are useful for data-oriented Python objects, 
and we use a lot of dataclasses in this repo,
but they are not mandatory.

When using them:

* avoid mutable default values;
* use `default_factory` where appropriate;
* consider `frozen=True` for genuine value objects;
* be deliberate about generated equality and hashing;
* do not duplicate inherited dataclass fields unnecessarily;
* avoid large amounts of lifecycle behavior hidden in `__post_init__`.

If a class primarily encapsulates behavior or invariants, an ordinary class may be clearer.

---

### Keep APIs unsurprising

Public methods should have clear behavior and ownership.

Avoid surprising side effects.

In particular:

* properties should normally be cheap and unsurprising;
* getters should not mutate state;
* methods should not silently modify arguments unless that is clearly their contract;
* constructors should not perform unrelated I/O;
* importing a module should not trigger application behavior;
* failure should not silently fall back to a materially different behavior.

Prefer explicit parameters to hidden global state.

Prefer returning useful values to requiring callers to inspect hidden state.

Do not add optional flags that produce several unrelated behaviors when separate operations would be clearer.

---

### Handle errors precisely

Do not use bare `except:`.

Avoid broad `except Exception` unless the boundary genuinely requires it.

Catch errors where there is something meaningful to do about them.

Do not swallow exceptions simply to make code appear robust.

Use domain-specific exceptions when callers genuinely need to distinguish domain failures.

Error messages should explain what failed and, when useful, the relevant value or condition.

Do not implement elaborate defensive handling for states that cannot occur according to the actual contract.

OMK-specific error types should be used (and created)
when an error is due to music domain problems
(example: trying to create an invalid time signature
or comparing the length of a quarter note to the duration of microseconds)
or involve OMK-specific invariants and other concepts.
When created, they should subclass from the conceptually-closest built-in error
(example: an invalid time signature is probably a kind of ValueError,
while a time system mismatch is probably a kind of TypeError).

---

### Dependencies are a cost

Do not add a third-party dependency unless the task requires it and the dependency provides substantial value.

Before adding one, consider whether the standard library or an existing dependency already solves the problem adequately,
and always consult the developer before making the decision.

Do not introduce frameworks to solve small local problems.

Respect the project's existing package and environment tooling.

For OMK, assume the repository's `uv` environment and `pyproject.toml` are authoritative unless told otherwise.

---

### Performance: measure before redesigning

Do not sacrifice clarity for hypothetical performance.

Do not introduce:

* caching;
* vectorization;
* multiprocessing;
* concurrency;
* custom indexing;
* memoization;
* database storage;
* flattened representations;

merely because they might someday be faster.

For potentially large musical operations, preserve designs that leave room for future optimization, but implement the clear version first unless performance is part of the task.

If optimization is requested, identify the actual bottleneck before restructuring the architecture around it.

---

### Comments and documentation

Comments should explain things that are not obvious from the code itself, especially:

* domain reasoning;
* invariants;
* non-obvious constraints;
* why an apparently simpler implementation is incorrect.

Do not narrate ordinary Python line by line.

Prefer good names and clear structure over explanatory comments.

#### Docstrings

Most methods and functions should have a one-line docstring that simply explains what it does and/or returns.
Many methods should have one or two runnable, testable examples.

Abstract music domain classes should normally have an explanation of what the concept means/does,
which includes how it is intended to be subclassed into system-specific concepts.
Often, these should mention how the concept is implemented in WSMN,
but be careful not to suggest that WSMN is default or normative. 

Do not add large docstrings to every function simply for completeness.

#### Documentation

Update documentation when the requested change makes existing documentation incorrect.
Do not undertake unrelated documentation work unless requested.


---

### Tests and validation

**Do not create, rewrite, or expand tests unless the task explicitly requires test work.**

Many structures in OMK are abstract and cannot be directly tested until later work implements concrete versions of them.
Do not go implement those concretizations unless asked to do so.

The presence of an implementation change is not by itself permission to create a suite of new tests.

Do not:

* add tests "for completeness";
* increase coverage opportunistically;
* refactor existing tests while implementing something else;
* fix unrelated failing tests;
* introduce testing infrastructure;
* create mocks or fixtures that were not needed for the requested task.

When the user explicitly requests tests, write tests for the requested behavior rather than testing implementation details.

The best test is a short example inside the docstring.
If a useful, working example can be included in a docstring in less than three lines,
go ahead and write it.



---

### Refactoring policy

Refactor when the requested change genuinely requires it.

Do not refactor because:

* code could be prettier;
* names could be more consistent;
* another pattern is fashionable;
* duplication exists nearby;
* a generalized framework could theoretically simplify future changes.

If a local cleanup is necessary to make the requested implementation clear and safe, keep it tightly bounded,
and let the developer know what you plan to do before doing it.

Preserve behavior outside the requested change.

---

### Avoid speculative compatibility

This is NEW DEVELOPMENT and this project currently has NO USERS.

Do not add backward-compatibility aliases, migrations, deprecation layers, overloaded signatures, fallback behavior, or legacy support unless there is evidence that compatibility is required.

If an API is internal and the project is intentionally changing it, change it cleanly.

Compatibility code has long-term cost. Do not invent consumers that have not been shown to exist.

---

### Match the project's stage of development

Some APIs are intentionally still being discovered.

Do not prematurely freeze an exploratory design behind elaborate abstractions or compatibility guarantees.

During architectural exploration, clear and changeable code is often more valuable than a framework designed to protect every current decision forever.

At the same time, do not casually change an established public interface when the task does not require it.

---

### When implementing a requested change

A good default process is:

1. Read the relevant code.
2. Identify the smallest place where the requested behavior belongs.
3. Check whether an existing abstraction already owns that responsibility.
4. Make the smallest coherent change.
5. Preserve unrelated behavior.
6. Use existing targeted validation if useful.
7. Report what changed and any material uncertainty.

Do not manufacture additional steps simply to appear thorough.



### Communicating results

Be concise and specific.

When reporting completed work, explain:

* what changed;
* where it changed;
* any important design choice;
* anything that remains genuinely unresolved.

Do not claim certainty you do not have.

Do not obscure an assumption behind confident language.

Do not pad the report with generic statements about code quality.

If you notice an unrelated issue, it is acceptable to mention it briefly when it is important, but **do not fix it unless asked**.

A useful pattern is:

> "I noticed X while making this change. I left it untouched because it is outside the requested scope."

---

### Things to actively avoid

Be especially wary of these common AI-agent failure modes:

* solving a larger problem than the one requested;
* interpreting a possible future requirement as a current requirement;
* building frameworks instead of implementing features;
* replacing simple code with architecture;
* adding tests nobody requested;
* changing APIs to make the implementation easier;
* silently inventing domain rules;
* adding defensive behavior for imaginary callers;
* introducing global state to simplify local bookkeeping;
* leaking backend-specific concepts into domain objects;
* assuming incomplete data is invalid;
* "cleaning up" unrelated code;
* producing enormous diffs for small requests.

When in doubt, choose the smaller change.

---

### Definition of good work

Good work in these repositories is not measured by how much code was produced.

A good change is:

* correct;
* narrowly scoped;
* readable;
* explicit;
* consistent with the surrounding architecture;
* appropriately typed;
* easy to modify later;
* honest about uncertainty;
* free of unnecessary machinery.

The goal is not for the agent to demonstrate autonomy.

The goal is to help a human developer think clearly and make deliberate changes to a difficult and interesting system.
