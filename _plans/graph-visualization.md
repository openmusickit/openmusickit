# Graph Visualization

-----
DEV NOTE:
This plan was originally written by ChatGPT after a lengthy discussion of requirements.
While I endorse its general shape, not every idea, decision, or assertion made here is "gospel".
You should read the plan and, in discussion with me, adjust it as needed.
This is also not a development plan (what precisely to do and in what order)
and does not include testing or docs,
so you will need to expand or append to it.
-----


Implement a simple graph visualization layer for Open Music Kit (OMK).

The goal is not to build a general-purpose graph editor or visualization framework. This should provide a useful, legible visualization of an `OmkGraph`, especially for debugging, examples, documentation, and later use by Workbench.

Use Graphviz `dot` as the layout/rendering engine.

## Core design principle

The visual layout should reflect OMK's musical/structural semantics rather than treating the graph as a generic network.

In particular:

- `NEXT` edges establish sequential ordering.
- Events connected by `NEXT` should appear along a primary sequence axis.
- `SIMULTANEOUS` relationships should cause events to align perpendicular to that primary sequence axis.
- Most other edge types should be displayed visually but should not substantially affect node placement.
- Styling and layout configuration belong in the visualization layer, not in the underlying OMK graph objects.

Do not add visualization-specific fields to core graph nodes or edges unless there is already an appropriate abstraction for doing so.

## Sequence direction

Support four user-selectable sequence directions:

- left-to-right
- right-to-left
- top-to-bottom
- bottom-to-top

These map naturally to Graphviz `rankdir` values:

```python
LEFT_TO_RIGHT = "LR"
RIGHT_TO_LEFT = "RL"
TOP_TO_BOTTOM = "TB"
BOTTOM_TO_TOP = "BT"
```

Use a small enum or similarly explicit public type rather than exposing raw Graphviz strings throughout the API.

The default should be left-to-right.

The meaning is:

- `NEXT` advances along the selected primary axis.
- Simultaneous events occupy the same position along the primary axis and spread along the perpendicular axis.

For example, in left-to-right mode:

```text
A ──NEXT──> B ──NEXT──> C
             │
             D
```

where `B` and `D` are simultaneous.

In top-to-bottom mode, the same semantic graph should instead place the NEXT chain vertically and simultaneous events horizontally.

## NEXT edges

`NEXT` is the primary layout relationship.

Graphviz should use `NEXT` edges as ranking constraints so that chains progress monotonically in the selected sequence direction.

A chain such as:

```text
A -> B -> C -> D
```

should reliably appear in that order.

Do not use force-directed placement.

Branching NEXT structures should still be laid out hierarchically by Graphviz.

NEXT edges should have a sensible default visual style, probably a simple solid line with an arrow.

## SIMULTANEOUS relationships

`SIMULTANEOUS` should affect rank/alignment rather than sequence progression.

Nodes belonging to the same simultaneous group should be placed in the same Graphviz rank, likely using `rank=same` subgraphs.

The SIMULTANEOUS edge itself, if shown, should not create an additional ranking constraint.

Think carefully about transitive/group semantics. If:

```text
A simultaneous B
B simultaneous C
```

and OMK semantics imply all three occur simultaneously, they should probably become one rank group rather than two unrelated pairwise constraints.

Do not rely merely on drawing a `SIMULTANEOUS` edge and hoping Graphviz infers the intended alignment.

## Other edge types

Most non-NEXT edges should be visible without influencing the main temporal/structural layout.

For example, edges such as:

- `ANNOTATES`
- `ARTICULATION`
- `LYRIC`
- `ACCOMPANIES`
- `HARMONIZES`
- `VARIATION_OF`
- `DERIVATIVE_OF`
- `REFERENCES`
- `STARTS_AT`
- `ENDS_AT`

should normally use:

```dot
constraint=false
```

unless there is a strong semantic reason for a particular edge type to participate in layout.

Define this behavior centrally so it is easy to change later.

Edge appearance should be configurable by edge type, including at least:

- line style: solid / dashed / dotted / etc.
- color
- line width
- arrow style if useful

Provide sensible defaults.

Do not require users to configure these values merely to get a readable graph.

## Node appearance

Node appearance should be configurable by node type/class.

Support at least:

- shape
- fill color
- border color
- text color
- font size
- width / height or other size controls
- whether the node has a visible surrounding shape at all

Some OMK objects should be renderable as plain text with no visible box or outline. Graphviz's `plain`, `plaintext`, or equivalent node shape can be used for this.

The styling system should make it straightforward to specify rules such as:

```python
NoteEvent -> rounded box
ChordEvent -> box
ContextEvent -> diamond
Lyric -> plain text
Section -> larger rounded box
```

The exact default mapping should be conservative and readable rather than elaborate.

Avoid assigning a unique color to every class. Prefer a small visual vocabulary based on broad semantic categories, for example:

- ordinary sequential musical events
- context events
- structural/grouping nodes
- annotation/text nodes

Use neutral, readable defaults that work reasonably on both light and dark backgrounds where practical.

User overrides should be easy.

A likely shape is some configuration object or mapping keyed by class/type, for example conceptually:

```python
NodeStyle(
    shape=...,
    fill_color=...,
    border_color=...,
    font_color=...,
    font_size=...,
)
```

and corresponding edge styles.

Do not bake styling into graph model classes.

## Labels

Provide useful default labels for OMK objects.

Prefer concise labels rather than dumping full `repr()` output.

The implementation should have a clear hook/callback for determining a node label from the OMK object.

Users should be able to override label generation.

Do not make this implementation dependent on every OMK class already having a perfect display string.

## API shape

Keep the public API small.

A reasonable starting point would be something conceptually like:

```python
from omk.visualization import (
    GraphRenderer,
    SequenceDirection,
    VisualizationConfig,
)

renderer = GraphRenderer(
    graph,
    config=VisualizationConfig(
        direction=SequenceDirection.LEFT_TO_RIGHT,
    ),
)

renderer.to_dot()
renderer.render("svg")
```

Do not assume these exact names if something fits the existing codebase better, but preserve the conceptual separation:

1. OMK graph
2. visualization configuration
3. DOT generation
4. optional Graphviz rendering

DOT generation should be independently usable.

## Dependency strategy

OMK Core should NOT bundle the native Graphviz runtime.

Generating DOT should not require a system Graphviz installation.

Rendering DOT into SVG/PNG/etc. may require a locally installed Graphviz executable.

In other words:

```python
renderer.to_dot()
```

should work without native Graphviz installed.

But:

```python
renderer.render("svg")
```

may call the local `dot` executable and should produce a clear, friendly error if Graphviz is unavailable.

Do not silently substitute a different layout engine.

Do not implement a fallback renderer whose layout semantics differ from Graphviz.

Consistency is preferable to silently producing a lower-quality or semantically different visualization.

The Python `graphviz` package may be used as an optional dependency if useful, but remember that it does not itself contain the Graphviz executable.

Consider putting visualization support behind an optional package extra if that matches the current packaging structure, e.g. conceptually:

```toml
[project.optional-dependencies]
visualization = ["graphviz>=..."]
```

However, if DOT generation can be implemented trivially without the Python `graphviz` package, prefer minimizing dependencies.

The actual native Graphviz executable should remain an external/system dependency for OMK.

A future Workbench application may bundle Graphviz with the desktop application, but that is outside this task.

## Error handling

If a user requests rendering and the Graphviz executable cannot be found, raise a specific, useful exception rather than exposing a raw `FileNotFoundError`.

The message should explain that:

- Graphviz is required for rendering.
- DOT generation still works without it.
- the user needs to install Graphviz using their operating system's package manager.

Keep installation instructions generic enough that they won't become a maintenance burden.

## Output formats

At minimum support:

- DOT
- SVG

PNG is useful if Graphviz makes it essentially free.

SVG should be the preferred/default rendered format because it is scalable and useful for documentation and UI embedding.

Do not add a large matrix of Graphviz output formats merely because Graphviz supports them.

## Architecture

Please inspect the existing OMK graph abstraction and adapt to it rather than bypassing it.

In particular:

- respect the existing graph adapter abstraction
- do not couple visualization directly to RustworkX internals if the adapter already exposes enough information
- if visualization needs capabilities that the graph adapter does not currently expose, add the smallest generally useful abstraction rather than poking through to private implementation details
- keep the visualization package isolated from core musical semantics

The resulting direction should look roughly like:

```text
OmkGraph
   |
   v
OMK visualization semantics
   |
   v
DOT
   |
   +------> returned directly
   |
   v
local Graphviz `dot`
   |
   v
SVG / PNG
```

## Implementation priorities

Optimize for a small, understandable first implementation.

The first useful version should:

1. traverse an OMK graph
2. assign IDs and readable labels
3. apply default node styles by type
4. apply default edge styles by edge type
5. use NEXT for primary ordering
6. group simultaneous nodes into equal ranks
7. keep most other edges out of layout constraints
8. support LR / RL / TB / BT
9. emit valid DOT
10. optionally render SVG through local Graphviz
11. expose straightforward user overrides

Avoid speculative abstractions for advanced interactive graph editing.

## Tests

Add tests for the semantic DOT output rather than relying only on image snapshots.

Important cases include:

- a simple NEXT chain preserves order
- changing direction changes `rankdir`
- simultaneous nodes are emitted in the same rank
- simultaneous grouping works for groups larger than two
- non-layout edges use `constraint=false`
- node styling dispatches correctly by node type
- edge styling dispatches correctly by edge type
- plain-text nodes can be emitted without a visible shape
- user style overrides replace defaults
- DOT generation works without Graphviz installed
- render gives a useful error when Graphviz is unavailable

If Graphviz is installed in the test environment, add a small integration test that renders a valid SVG, but do not make the entire test suite dependent on Graphviz being present.

Before implementing, inspect the existing graph classes, edge types, adapters, packaging, and test conventions, and adjust names/API placement to match the codebase rather than creating a parallel style.