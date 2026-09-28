# Graph visualization

Status: **implemented 2026-09-28** (`openmusickit.visualization`: `GraphRenderer`,
`VisualizationConfig`, `SequenceDirection`, `NodeStyle`, `EdgeStyle`, `default_label`,
`duration_glyph`, `render_dot`; `OmkGraph.nodes`, `edge_endpoints`, `onsets`;
`RenderingError`, `GraphvizNotFoundError`; docs). Agreed the same day after the dialog below.

Notes from implementation:

- The rendered test fixture matches the target picture in all four directions
  (`graph-visualization-fixture-{LR,RL,TB,BT}.png` were the review renders).
- Rows attached to a line are ordered by closeness, not only by side: a branched line sits
  right beside its parent, then the lyrics sung to it, then the lines pinned to it
  (`BRANCH_DISTANCE`, `LYRIC_DISTANCE`, `PIN_DISTANCE` in `layout.py`). Without that the
  branch voice landed below the lyrics.
- `NodeStyle` has `rounded`, not `bold`: a rounded box is a Graphviz style, bold text is
  a label's business.
- The invisible ordering chain of a column does run beside a visible connector between two
  of its nodes (a note and its syllable); under straight routing that is harmless, and the
  spine, not those edges, orders the columns. The "no invisible edge beside a visible one"
  rule holds for the spine and the columns' order only.
- `OmkGraph.onsets` leaves out a neighbour whose distance is in another temporal system
  rather than raising, so a picture of mixed-system music is still drawn.
- A stint's transposition is spelled as an interval (`stint perfect 5`), since a
  `TonalVector` formats as a pitch.
- The part and stint came out diagonally above-left of the head on their own in the
  tighter layout; no rule places them there.
- The docs stylesheet appends Noto Music through attribute selectors on the exact
  `font-family` strings Graphviz writes (`Helvetica,sans-Serif`, `monospace`), so the
  monospace nodes keep their font.
- The test helpers module is `tests/visualization/dot_helpers.py`: pytest's doctest
  collection imports test modules by basename, and `tests/graph/helpers.py` already exists.
- Python 3.14's `graphviz` package was never needed; nothing was added to `pyproject.toml`.
Written from a requirements memo (drafted by ChatGPT after a requirements discussion,
endorsed in shape by the developer), a planning dialog on 2026-09-28,
the developer's sketch `graph-drawing.jpg`, and two rounds of review of a hand-written example.
The example is the target picture: `graph-visualization-example.{dot,png,svg}` (left to right)
and `graph-visualization-example-tb.png` (top to bottom), beside this file.
§1 condenses the memo; §0 records what was settled and what this plan decided on its own.

## 0. Decisions

Settled with the developer, 2026-09-28:

1. **Package: `openmusickit.visualization`**, a top-level package beside `graph` and `objects`,
   in six modules (§3). It imports from both; nothing imports it.
2. **No Python dependency.** DOT is written by hand; rendering shells out to the system `dot`.
   Graphviz 16 is installed locally, so rendering is verified here.
3. **Docs use Quarto's bundled Graphviz.** Verified on a throwaway page: a Python cell with
   `output: asis` that prints a fenced `{dot}` block renders to inline SVG through
   `quarto_cli/share/js/graphviz-wasm.js`, with no system Graphviz.
   Fallback if it looks poor: `to_svg()` in the cell and a docs build with Graphviz installed.
4. **Content-only labels** (`C⁴ ♩`, `Cmaj`, `Twin -`, `Voice`); the class name only where nothing better exists.
5. **Relational edges are labelled with their type name**; nothing else tells them apart.
6. **Simultaneity is inferred from timing, not only read off pins.** The sequence axis is the order
   of onsets: everything that a timing walk (`relative_onset`) places at one instant shares a column.
   The Fmaj two beats after a pinned Cmaj sits over the note two beats after the pinned one.
   Pins, branches and group memberships are the *evidence*; the walk is what aligns. (Round two.)
7. **The picture follows the sketch and the two review rounds:**
   chords above the line they are pinned to, lyrics below the line they are sung to;
   duration glyphs, large; the octave as a small superscript; a clef drawn as its glyph when it has one;
   chords and lyrics in monospace with no box; tight boxes on notes; tight rows;
   a branch above or below its parent line by pitch, its edge solid, thin, with an open arrowhead;
   lyric lines without visible NEXT edges (the row says it);
   NEXT solid with an arrow, every other edge dotted and lighter;
   a spanner (slur, verse, stint end) drawn as a start marker and an end marker, each in its event's column,
   never as a long edge to the end;
   the score as a title block: top right, boxed, when the whole graph hangs on one score;
   otherwise a small legend block above each score's earliest head; the score's edges never drawn;
   the sync line a long thin bar under everything, spanning the whole graph, its name at its left end,
   each point a dot resting on the bar with its time to the right and its name and description below the bar.
8. Part and stint sit one and two columns before the head. In the example dot happens to place them
   diagonally above-left of the head, which is the developer's wish, but no rule enforces it.

Calls this plan makes on its own (open to objection):

9. Layout participation (ranks, rows) is decided per edge and node in `layout.py`, never in the styles.
10. **Rows** (position across the sequence axis) are a first-class layout concept beside ranks (§2.2):
    every NEXT chain is a row, attached nodes are satellites of a row, the conventions in decision 7 are
    "above" relations between rows, and dot is told the order with invisible flat chains.
11. **`layout.py` computes the ranks itself** from onsets and constraint edges, emits every rank as a
    `rank=same` subgraph listing *every* node of that column in row order, and fixes the order of the
    columns with an invisible spine (one invisible node per rank, chained). Leaving ranks to dot was tried:
    a node that lands in a column by NEXT alone was missing from its chain and the lyric row bent.
    A second invisible edge beside a visible one was tried for the spine: under straight routing dot
    bends one of the pair (the bar's last segment). Ranks become numbers the tests can assert.
12. **Straight edge routing** (`splines=line`) is the default, as a config field. With dot's default
    splines a connector between two nodes of one column is a wide loop around everything between them.
13. The sync bar is edges, since a Graphviz node cannot span ranks: a head block at rank 0, a block per
    point in offset order, an end block at the last rank, joined by thick unarrowed constraint edges
    through each block's bar port. Each block also paints its own stretch of the bar (a filled cell of
    the bar's thickness and colour), because dot clips the last segment at its tail block's boundary
    whatever `tailclip` says; the filled cell hides the seam. The blocks are HTML-like table labels of
    equal height, transposed for TB and BT (the bar runs down their first column).
14. A label that starts with `<` and ends with `>` is an HTML-like label (Graphviz's own convention);
    that is how superscripts, glyph sizes, the title block and the sync blocks are written, and how a user
    hook can write one.
15. Duration glyphs come from the Unicode Musical Symbols block, which needs a font that has them
    (Noto Music is installed here; the docs site loads it as a webfont). No glyph: a fraction of a whole note.
16. `OmkGraph` gains `nodes()`, `edge_endpoints()` and `onsets()` (§2.6).
17. Errors: `RenderingError(OmkError, RuntimeError)` and `GraphvizNotFoundError(RenderingError)`, in `errors.py`.
18. The top-level package imports `visualization` as a submodule (`omk.visualization`) and re-exports none of its names.
19. Every node and edge carries SVG `id` and `class` attributes so the Workbench, or a stylesheet, can find them.
20. No fills by default: the sketch is line art. The `fill_color` field exists for anyone who wants them.

## 1. Requirements (condensed from the memo)

- A legible picture of an `OmkGraph` for debugging, examples, docs, and later the Workbench.
  Not a graph editor, not a visualization framework.
- Graphviz `dot` is the layout engine. No force-directed layout, no fallback engine with different semantics.
- Layout reflects OMK semantics: NEXT advances along a primary axis; simultaneous events align across it;
  most other edges are drawn without moving anything.
- Four sequence directions (LR default, RL, TB, BT), as an explicit enum, not raw Graphviz strings.
- Node appearance configurable by class, edge appearance by edge type; conservative defaults on a few
  broad categories; overrides easy; nothing in the model classes.
- Concise default labels with a user-overridable hook.
- Small API: graph, config, DOT generation, optional rendering, each independently usable.
- DOT generation needs no Graphviz. Rendering needs the local `dot` and fails with a specific,
  friendly error when it is missing. Outputs: DOT, SVG (preferred), PNG.
- Go through the graph adapter abstraction; add the smallest generally useful abstraction if it lacks something.
- Tests on the semantic DOT output, not image snapshots; a rendering integration test only where Graphviz is present.

## 2. The design

### 2.1 Public API

```python
from openmusickit.visualization import (
    EdgeStyle, GraphRenderer, NodeStyle, SequenceDirection, VisualizationConfig,
)

renderer = GraphRenderer(graph)                        # left-to-right, default styles
renderer = GraphRenderer(
    graph,
    VisualizationConfig(
        direction=SequenceDirection.TOP_TO_BOTTOM,
        node_styles={NoteEvent: NodeStyle(shape="circle")},   # replaces the default for NoteEvent only
        edge_styles={EdgeType.LYRIC: EdgeStyle(color="steelblue")},
        label=my_label,                                      # Callable[[OmkObject], str]
    ),
)
renderer.to_dot()   # str; no Graphviz needed
renderer.to_svg()   # str; runs `dot -Tsvg`
renderer.to_png()   # bytes; runs `dot -Tpng`
```

`SequenceDirection` is a `StrEnum` whose values are the Graphviz `rankdir` strings
(`LEFT_TO_RIGHT = "LR"`, `RIGHT_TO_LEFT = "RL"`, `TOP_TO_BOTTOM = "TB"`, `BOTTOM_TO_TOP = "BT"`).

`VisualizationConfig` (dataclass, `kw_only`):

- `direction: SequenceDirection = LEFT_TO_RIGHT`
- `node_styles: Mapping[type[OmkObject], NodeStyle] = {}`: overrides, consulted before the defaults;
  both tables are looked up along the node's MRO, most specific class first.
- `edge_styles: Mapping[EdgeType, EdgeStyle] = {}`: overrides by edge type.
- `sync_bar: EdgeStyle`: the bar edges of a sync line (§2.2); default thick, light gray, no arrowhead.
- `label: Callable[[OmkObject], str] = default_label`
- `font_name: str = "Helvetica"`: the graph's font; node styles may name their own.
- `splines: str = "line"`: Graphviz edge routing (`line`, `polyline`, `spline`, `ortho`, ...).
- `node_sep: float = 0.15`, `rank_sep: float = 0.35`: Graphviz `nodesep` and `ranksep`, in inches.

`NodeStyle` and `EdgeStyle` are frozen dataclasses of optional fields (`None` means "Graphviz default"):

- `NodeStyle`: `shape`, `fill_color`, `border_color`, `font_color`, `font_name`, `font_size`,
  `width`, `height`, `margin`, `bold`. `shape="plain"` is a text-only node.
- `EdgeStyle`: `style` (solid, dashed, dotted, invis), `color`, `pen_width`, `arrowhead` (normal, empty, none, ...),
  `arrow_size`, `show_type` (label the edge with its type name).

Nothing in either style says anything about layout.

`GraphRenderer(graph, config=VisualizationConfig())` builds the DOT model on demand and caches nothing
(the graph is mutable; a renderer is cheap). `dot_graph()` exposes the model (§2.3).

### 2.2 Layout semantics (`layout.py`)

The one place that knows what OMK's edges mean for placement.
Input: an `OmkGraph` and a `VisualizationConfig`; output: a `DotGraph` (§2.3).
Two axes: the **rank** is the position along the sequence axis, computed here and handed to dot as
`rank=same` subgraphs plus a spine; the **row** is the position across it (dot orders each column's nodes;
we tell it the order).

**Ranks.**

- **Onsets.** The timing graph is walked component by component with `graph.onsets(reference)` (§2.6):
  from an unvisited node, every node reachable through known deltas (NEXT through a known duration;
  a branch, pin or group membership through its anchor and displacement; a pin to a sync point)
  gets an onset relative to the reference. Repeat until every node has been offered a reference.
  A node no walk reaches (an event after an unknown duration, an unrelated fragment) has no onset.
- **Alignment.** Within one component, nodes with equal onsets share a rank, with one exception:
  members of one NEXT chain never share a rank (a chain is a sequence), so where several events of a
  chain have one onset (a clef, a meter, then the note), the *last* of them stands for that onset and the
  others take the ranks before it. Attached nodes take their event's rank: a syllable (LYRIC), a mark
  (MARKS), an annotation (ANNOTATES), a spanner's start and end markers (STARTS_AT, ENDS_AT),
  a sync point (its pin). Alignment groups are merged with union-find.
- **Order.** A DAG over the alignment groups: NEXT edges; the onset order within each component
  (each onset class to the next); PERFORMS (a part before its stint or group) and a stint's STARTS_AT
  (the stint before the head); the bar edges of a sync line. A longest path from the sources gives each
  group its rank, so every constraint spans at least one rank. A cycle (music whose pins disagree;
  `check_alignment` is the musical check) is broken by dropping the edge that closes it, silently.
  Nodes without an onset are ranked by these edges alone.
- **Emission.** Every rank is a `rank=same` subgraph holding all its nodes, with an invisible flat chain
  in row order (below), and one invisible spine node; the spine nodes are chained by invisible constraint
  edges, which is what orders the columns. A visible edge between two nodes of one column
  (a pin, a LYRIC, a MARKS) is drawn beside the chain with `constraint=false`. No other invisible edge
  is ever emitted beside a visible one.
- **Drawn without constraining** (`constraint=false`): every alignment edge (the rank says it);
  a displaced or offset-anchored timed edge, labelled with its displacement (a signed fraction for a
  `Measurable`, `str()` for a clock duration, prefixed "from offset" when offset-anchored), since the walk
  has already placed its ends; ENDS_AT; the relational types (ACCOMPANIES, HARMONIZES, VARIATION_OF,
  DERIVATIVE_OF, REFERENCES, IMPLEMENTS, REALIZES, USER_DEFINED). A `Score`'s CONTAINS edges and a
  `SyncLine`'s CONTAINS edges are not drawn at all (the title block and the bar say the same thing).
- **Sync line.** A bar along the sequence axis: a head block carrying the line's name at rank 0,
  a block per point in offset order (a pinned point at its events' rank, an unpinned one between its
  neighbours by the bar edges), an empty end block at the last rank, so the bar spans the graph.
  Consecutive blocks are joined by *bar edges*: `constraint=true`, `tailclip=false`, `headclip=false`,
  through each block's `bar` port, styled by `config.sync_bar`, `class="omk-edge sync-bar"`; the port
  cell itself is filled in the bar's colour at the bar's thickness, so the bar is continuous under every
  block. All bar nodes share `group="<sync line id>"`. The block's layout is in §2.4.
- **No clusters.** Graphviz cannot put nodes of different clusters on one rank, and alignment is the point.

**Rows.**

- Every node belongs to a row. A NEXT chain is a row (a branched line is its own chain); a `Part`,
  `Stint`, `Marking`, annotation, spanner marker or score legend is a *satellite* of the row it attaches
  to, on one side of it; a sync line (head, points, end) is a row of its own. Each chain's members and
  each sync line's bar nodes share a Graphviz `group` (the head's id), which keeps the chain straight.
- The conventions are "above" relations between rows, collected into a small DAG and sorted
  topologically (ties by first appearance; a cycle drops the later relation):
  - a line whose head is a `ChordEvent` goes above the line it is pinned to; any other pinned line goes below;
  - a branched line goes above its parent's line when its head sounds higher than the parent event
    (the highest tone of each, when the tones are comparable), below otherwise or when in doubt;
  - a lyric line goes below the line its syllables are sung to;
  - the lines of a group keep their group order (the order of the group's CONTAINS edges);
  - marks, annotations and mark-spanner markers sit just above their line, lyric-section markers just
    below theirs; a part and its stint sit above the head's line; a score legend above the earliest head's line;
  - the sync line is last.
- "Above" means "before" along the perpendicular axis: the top in LR and RL, the left in TB and BT.

**Node order** in the DOT: each row in walk order from its head, rows in row order, then anything left,
in the adapter's order; edges in the adapter's order. Stable for one graph, not across processes (ids are UUIDs).

### 2.3 DOT model and text (`dot.py`)

A tiny generic model with no OMK imports, so tests inspect structure rather than parse text:

```python
@dataclass(frozen=True, slots=True)
class DotNode:  id: str; attrs: dict[str, str]
@dataclass(frozen=True, slots=True)
class DotEdge:  source: str; target: str; attrs: dict[str, str]
@dataclass(slots=True)
class DotGraph:
    attrs: dict[str, str]; nodes: list[DotNode]; edges: list[DotEdge]
    ranks: list[list[str]]            # index = rank; each list is that column's node ids in row order
    def to_text(self) -> str
```

`to_text` writes `digraph { <graph attrs>; <nodes>; <one rank=same subgraph per rank, with its invisible
chain and spine node>; <spine edges>; <edges> }`. Every id and attribute value is double-quoted,
`"` and `\` escaped, a newline in a label written `\n`; except that a `label` (or `xlabel`) that starts
with `<` and ends with `>` is written as it is, an HTML-like label. Attribute order is insertion order.
`to_dot()` is `dot_graph().to_text()`.

### 2.4 Styles and labels (`config.py`, `labels.py`)

Default node styles (line art, no fills; most specific class wins):

- `SequentialEvent` (a note, a division, a context event): a rounded box with a tight margin.
  `ContextEvent`: `plain` when its label is a glyph (a clef), else a plain box with a smaller font.
  `DivisionEvent`: a plain box with the shape's name.
- `ChordEvent` and `LyricSyllable`: `plain`, monospace.
- `Marking`, `Part`, `Stint`, `LineGroup`, spanner markers: `plain`, small, mid-gray text.
- `Score` (legend case), `SyncLine` head, `SyncPoint`: `plain`, HTML-like table labels (below).
- Anything else (`OmkObject`): Graphviz's default ellipse, so an unknown class still appears.

Default edge styles: NEXT solid, dark (`#303030`), normal arrowhead, except that NEXT between two
`LyricSyllable`s is `invis`. BRANCHES solid, dark, `pen_width` 0.7, `arrowhead="empty"`.
Every other type dotted, light (`#b0b0b0`), small arrowhead; SIMULTANEOUS with no arrowhead
(its meaning is symmetric); the relational types with `show_type=True`.
The sync bar: solid, `pen_width` 4, light, no arrowhead. Ordering edges and the spine: `invis`.

`default_label(obj)`:

- `NoteEvent`: each tone as letter, accidental and octave as a small superscript, then the duration
  glyph two sizes larger: `<C♯<SUP><FONT POINT-SIZE="6">4</FONT></SUP> <FONT POINT-SIZE="14">♩</FONT>>`,
  from the pitch representation's `letter`, `alteration`, `accidental.unicode` and the vector's `o`;
  unpitched or unqualified tones as `format(tone)`; tones sorted. A rest: the rest glyph for its duration.
- `ChordEvent`: `str(chord)` and the duration glyph. `LyricSyllable`: `str()`.
- `ClefEvent`: the clef's glyph when its sign has one (G 𝄞, F 𝄢, C 𝄡, percussion 𝄥, TAB as text),
  with the octave change as small text beside it (`8`, `15`, above or below); else `clef` and its repr.
  `MeterEvent`: `meter` and the meter; `TempoEvent`: the term or the ratio; `ModalContextEvent`: `key` and its name.
- `DivisionEvent`: the shape's name. `Marking`: the mark's name. `Part`: its name; `LineGroup`: name or `group`.
  `Stint`: `stint`, plus the transposition if any.
- Spanner markers, two per spanner, made by the layout: `⌈slur` and `slur⌉` for a `MarkSpanner`
  (the mark's name), `⌊verse 1` and `verse 1⌋` for a `LyricSection` (type and number, or name),
  `stint⌉` for a stint's end when it has one. The start marker carries the spanner's id; the end marker's
  id is the spanner's id with `-end`.
- `SyncLine` head block, `SyncPoint` block, end block: HTML tables of equal height, four rows in LR/RL:
  the dot `●` and the time; the bar row (the port, filled in the bar's colour, as thick as the bar);
  the name; the description (mid-gray, smaller); empty cells keep the height. Time: `HH:MM:SS.ffff` for a `ClockDuration` (four fractional digits), else the duration
  label (glyph, or fraction). The head block has the line's name in the first row and empty rows below;
  the end block is empty. In TB/BT the block is transposed: the bar port is a thin first column spanning
  the rows, the dot beside it, the text to the right.
- `Score`: the title block, an HTML table with a border: title in bold; subtitle; composer, lyricist and
  arranger each on a line, labelled; opus; dedication; whatever is set. When the graph has exactly one
  `Score` and every node is weakly connected to it, the block is the graph's label, top right
  (`labelloc="t"`, `labeljust="r"`), and no Score node is drawn. Otherwise each Score is a small legend
  node with the same block, a satellite above its earliest line head.
- Fallback: the class name. Text that goes into an HTML-like label has `&`, `<`, `>` escaped.

`duration_glyph(duration) -> str | None`, public, so a custom hook can reuse it:
`MetricalDuration` with numerator 1 and a power-of-two denominator up to 64 gets its note glyph
(𝅜 𝅝 𝅗𝅥 ♩ ♪ 𝅘𝅥𝅯 𝅘𝅥𝅰 𝅘𝅥𝅱), one augmentation dot per `dots`, and a tuplet ratio as small text after it (`♪ 3:2`);
a rest the matching rest glyph (𝄻 𝄼 𝄽 𝄾 𝄿 𝅀 𝅁); a `TiedDuration` its members joined by `‿`;
a `GraceDuration` `grace` and the base glyph; anything else `None`, and the label falls back to
`rational_length` as a fraction (`1/4`). A clock duration is `str()`.

Fonts: `♩` and `♪` are in nearly every font; the rest of the Musical Symbols block is not.
Graphviz's PNG output uses fontconfig fallback (Noto Music here); an SVG in a browser falls back per glyph to
the viewer's fonts, so the docs site loads Noto Music (§5). A viewer without such a font sees boxes for those glyphs.

Every node carries `id="<uuid>"` and `class="omk-node <ClassName> <Base> ..."` (its MRO up to `OmkObject`),
every edge `class="omk-edge <type>"`. Graphviz passes both into the SVG.

### 2.5 Rendering (`graphviz.py`)

`render_dot(dot: str, format: str) -> bytes`:
`shutil.which("dot")`; `None` raises `GraphvizNotFoundError`.
`subprocess.run([dot, f"-T{format}"], input=dot.encode(), capture_output=True)`;
a non-zero exit raises `RenderingError` carrying Graphviz's stderr.
`to_svg()` decodes UTF-8; `to_png()` returns the bytes.

In `errors.py`:

```python
class RenderingError(OmkError, RuntimeError):
    """Raised when rendering a visualization fails: Graphviz is missing or `dot` rejected the input."""

class GraphvizNotFoundError(RenderingError):
    """Raised when the Graphviz `dot` executable is not on the PATH."""
```

The not-found message says that rendering needs Graphviz's `dot`, that `to_dot()` works without it,
and to install Graphviz with the operating system's package manager (linking graphviz.org/download).
No per-platform commands.

### 2.6 Graph API additions (`graph.py`)

```python
def nodes(self, node_type: type[OmkObject] | None = None,
          predicate: Callable[[OmkObject], bool] | None = None) -> Iterator[OmkObject]
def edge_endpoints(self, edge: OmkEdge) -> tuple[OmkObject, OmkObject]
def onsets(self, reference: OmkObject) -> dict[UUID, Duration]
```

The first two are passthroughs to the adapter, beside `edges()`. `onsets` is the breadth-first walk of
`_relative_onset` without a target: every node whose onset is a known distance from `reference`'s,
with that distance, the reference itself at `ZeroDuration()`; the same rules (a sync line met, not crossed;
the first arrival wins). `_relative_onset` keeps its early exit and its `ignoring` edge, so the two share
`_timing_neighbours` and nothing else. Each with a doctest.

### 2.7 Tuning map: where to change what, later

The defaults are expected to be tweaked once the machinery exists. Each kind of tweak has one home:

- **How a class of node or a type of edge looks** (shape, colour, width, font, arrowhead, margin):
  `DEFAULT_NODE_STYLES` and `DEFAULT_EDGE_STYLES` in `config.py`, one entry per class or type.
  Spacing (`node_sep`, `rank_sep`), routing (`splines`) and the graph font: `VisualizationConfig` defaults.
- **What a node says** (the note label's parts and their sizes, the glyph tables, the clef glyphs,
  the clock format, the marker brackets, the rows of a sync block, the lines of the title block):
  `labels.py`, as small named functions and module constants (`OCTAVE_POINT_SIZE`, `GLYPH_POINT_SIZE`, ...).
- **What aligns and what goes above what** (the row conventions, which edge types align, which are
  invisible, where parts and stints go, the score placement rule): one clearly marked "conventions"
  section at the top of `layout.py`, tables and short predicates, no logic mixed in.
  The rank computation and the DOT emission below it should not need touching for a convention change.
- **The target pictures**: `graph-visualization-example.{dot,png,svg}` and `-tb.png`. A tweak is checked by
  rendering the test fixture and comparing.

## 3. Files

New package `src/openmusickit/visualization/`:

1. `__init__.py`: package docstring (what it is, the pipeline, what it does not do); re-exports.
2. `config.py` (~180 lines): `SequenceDirection`, `NodeStyle`, `EdgeStyle`, `VisualizationConfig`,
   `DEFAULT_NODE_STYLES`, `DEFAULT_EDGE_STYLES`, `node_style_for(cls, config)`, `edge_style_for(type, config)`.
3. `labels.py` (~220): `default_label`, `duration_glyph`, `clef_glyph`, `clock_label`, the HTML escaping,
   the title, legend and sync block tables, the spanner markers.
4. `layout.py` (~380): onsets and alignment, the rank DAG and its longest path, rows and satellites,
   the sync bar, the spanner markers, the score placement, the chains and the spine; produces a `DotGraph`.
5. `dot.py` (~100): `DotNode`, `DotEdge`, `DotGraph`, `to_text`, quoting, HTML-like labels.
6. `graphviz.py` (~40): `render_dot`.
7. `renderer.py` (~60): `GraphRenderer`.

Changed:

- `src/openmusickit/errors.py`: the two exceptions.
- `src/openmusickit/graph/graph.py`: `nodes`, `edge_endpoints`, `onsets`.
- `src/openmusickit/__init__.py`: `from . import visualization` and the `__all__` entry.
- `docs/examples.qmd`, `docs/_quarto.yml`, `docs/index.qmd`, a `docs/styles.css` (§5).

## 4. Tests

`tests/visualization/`, with a `conftest.py` holding the example's graph: the docs' Twinkle melody
under a treble clef, the chord line pinned to the first note, the lyrics with a verse section, a staccato,
a slur, a branched second voice, a Voice part with a stint, a Score, and a sync line with two pinned
points (one named and described) and one unpinned; plus small graphs where a rule needs one.

`test_layout.py`, on the `DotGraph` model (ranks as numbers):

- ranks: a NEXT chain of known durations gets ranks 0, 1, 2, ...; a zero-duration clef precedes its note;
  the Fmaj two beats after the pinned Cmaj shares the rank of the note two beats after the pinned one,
  with no pin of its own; a pin with `displacement=-quarter` aligns the pinned event with the note a quarter
  earlier; an offset-anchored branch puts the head at the rank of the parent's successor; the second note
  of an eighth-note branch under a quarter-note melody gets a rank of its own between two melody ranks;
  a LYRIC, a MARKS, a slur's STARTS_AT and ENDS_AT each give both ends one rank; a group's heads share a
  rank; a sync point ranks with its pinned events; after an event of unknown duration the next event is
  ranked by NEXT alone (one after) and a pin from it still aligns; a stint is one rank before its head and
  the part one before that; a pair of pins that disagree still yields ranks; direction sets `rankdir` (all four);
- the spine: one invisible node per rank, chained; no invisible edge between two nodes that a visible edge joins;
- the sync bar: head at rank 0, end at the last rank, bar edges in offset order, `constraint` true,
  unclipped, through the `bar` ports, every block's bar cell filled in the bar's colour, one `group`,
  the line's CONTAINS not drawn, an unpinned point between its neighbours;
- the score: with one connected score, the graph label is the title block and no Score node is drawn;
  with two scores, or a disconnected line, each score is a legend node above its earliest head;
  no CONTAINS edge from a Score is drawn;
- spanners: a start and an end marker, each in its event's column; no edge from the start to the end;
- rows: a chord line is above the line it is pinned to and another note line below; a branch is above its
  parent when its head is higher and below when lower or unpitched; lyrics below their notes; a mark above
  its note; a slur's markers above, a verse's below; the sync line last; each rank's chain lists every node
  of that rank once, in row order; the same chains come out for TB;
- every event of a line carries the head's id as its `group`; a branched line has its own;
- every drawn edge is `constraint=false` unless it is a NEXT, a PERFORMS, a stint's STARTS_AT or a bar edge;
- every node of the fixture appears exactly once; the syllables' NEXT edges are `invis`.

`test_config.py`: style lookup follows the MRO (a `Rest` is a `NoteEvent` is a `SequentialEvent`);
an override replaces the default for that class only; a `plain` shape emits no fill or border;
`show_type` labels the edge; the BRANCHES default is solid with an empty arrowhead; a user label hook is used.

`test_labels.py`: a note with a sharp and an octave gives the HTML-like label with the small superscript
and the large glyph; an unqualified pitch has no superscript; a rest gives the rest glyph;
`duration_glyph` for the quarter, the dotted half, a triplet eighth, a tied duration, a grace duration,
and `None` for `MetricalDuration(3, 8)`; the treble, bass, alto and percussion clefs give glyphs and a
TAB clef text; `clock_label` gives `HH:MM:SS.ffff`; a chord, a syllable with `&` in it (escaped), a part,
the sync blocks (with and without name and description, LR and TB), the title block with every field
and with only a title, a plain `OmkObject`.

`test_dot.py`: quoting of `"`, `\`, newlines and unicode; an HTML-like label is written unquoted;
one `rank=same` subgraph per rank with its invisible chain and spine node; the graph label;
`splines`, `nodesep`, `ranksep`; `id` and `class` attributes; attribute order;
`to_dot()` works with `shutil.which` patched to return `None` (it must never look for Graphviz).

`test_render.py`: `GraphvizNotFoundError` when `shutil.which` returns `None`, and its message names `to_dot`;
`RenderingError` with stderr when a stub `dot` exits non-zero;
integration, `skipif` no `dot` on the PATH: `to_svg()` contains `<svg` and the node ids,
`dot -Tcanon` accepts the DOT (well-formedness), `to_png()` starts with the PNG signature.

`test_properties.py` (Hypothesis, `tests.strategies.lines`, `metrical_durations`):

- for any line of known durations, the ranks are 0, 1, 2, ... in walk order; with unknown durations
  mixed in, ranks still increase along the line;
- for two lines pinned at random events with a random anchor and displacement (`None` or a
  `MetricalDuration`), two events share a rank iff `relative_onset` between them is zero;
- for any such graph, the ranks partition the drawn nodes, every NEXT edge spans at least one rank,
  and each rank's chain is a permutation of that rank.

Doctests: `SequenceDirection`, `NodeStyle`, `VisualizationConfig`, `GraphRenderer.to_dot` (a two-note line),
`default_label`, `duration_glyph`, `clef_glyph`, `clock_label`, `OmkGraph.nodes`, `OmkGraph.edge_endpoints`,
`OmkGraph.onsets`.

## 5. Docs

- `docs/examples.qmd`: a "Drawing the graph" section right after "A small score graph",
  rendering the Twinkle graph (LR) through Quarto's Graphviz:

  ```
  ```{python}
  #| output: asis
  from openmusickit.visualization import GraphRenderer
  print("```{dot}\n" + GraphRenderer(graph).to_dot() + "\n```")
  ```
  ```

  and, at the end of "A drum kit", the kit top-to-bottom, showing the direction switch and a group.
  A sentence each on columns as instants, rows as conventions, and that `to_svg()` needs Graphviz installed.
- `docs/_quarto.yml`: a "Visualization" section in the reference after "Graph", listing the six modules;
  `format.html.css: styles.css`.
- `docs/styles.css`: loads Noto Music from Google Fonts and appends it to the font fallback of SVG text
  in cell output, so the duration and clef glyphs render for every reader.
- `docs/index.qmd`: one line under Installation: rendering diagrams needs Graphviz; the docs and `to_dot()` do not.

## 6. Commits

1. `Claude: OmkGraph.nodes, edge_endpoints and onsets`
2. `Claude: visualization package: config, labels, layout, DOT model; tests`
3. `Claude: render through local Graphviz; RenderingError, GraphvizNotFoundError; tests`
4. `Claude: visualization docs; omk.visualization; plan to completed`

## 7. Verification

Baseline before starting, so an end failure can be placed on one side of the work:

    uv run pytest --hypothesis-profile=thorough -m ""

Per commit:

    uv run pytest
    uv run ruff check src tests && uv run ruff format --check src tests

After commit 2, render the fixture in all four directions and compare with
`graph-visualization-example.png` and `-tb.png`; show the developer before writing the docs;
adjust rows, margins and fonts then.
At the end, the heavy set again, the coverage diagnostic, and the docs build
(`cd docs && uv run python build_reference.py && uv run quarto render`),
then look at the two rendered diagrams in `docs/_site/examples.html`.

## 8. Out of scope (deliberately)

- **Word braces under the syllables** (in the sketch). A `Word` is a value, not a node; drawing the word
  its syllables belong to is a satellite row of its own, added when the picture is otherwise settled.
- **Proportional spacing.** Columns are instants in order, not distances; a whole note and a sixteenth
  are one column apart. A time-proportional axis is a different layout engine's job.
- **Configurable row conventions** (chords above, lyrics below, ...). They are one table in `layout.py`;
  exposing them is a config field when someone needs the other way round.
- **A dark theme.** The line art is dark on transparent; a second default table when wanted.
- **Clusters**, **a `dot_executable` parameter** for a bundled Graphviz (the Workbench),
  **`_repr_svg_`** for notebooks, edge label hooks, hiding edge types, filtering nodes, more Graphviz formats.
- **Consistency checks in the picture.** `check_alignment` is the musical check.
