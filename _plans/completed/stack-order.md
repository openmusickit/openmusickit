# Stack order and stack groups (MusicXML pre-plan P1)

Status: **done 2026-10-19**.
Gates stage 6 (the writer) of `_plans/musicxml.md`.

Written for the developer (to approve)
and for the agent who builds it.

## 1. The problem

A `Score`'s CONTAINS edges are unordered,
so nothing says which part is drawn first,
`score_parts` returned a quartet reversed,
and a bracket or brace over a run of parts (MusicXML `<part-group>`)
has no home.
The lines of a piano's `LineGroup` are unordered too,
so nothing says the right hand is above the left.
The reader stopgaps are `Part.meta["musicxml"]` `index` and `groups`
and the head's `staff` meta.

## 2. Decisions (developer, 2026-10-19)

1. **Order is its own edge set, `STACKS_ABOVE`,** not a position on CONTAINS
   and not part of membership.
   Membership says what is in a score;
   `STACKS_ABOVE` says how it is arranged when stacked.
   Reasons, in order:
   order may be partial (an incomplete sketch says only what it knows);
   one mechanism covers everything that stacks;
   arrangement can be read or stripped without touching membership;
   inserting and removing are local edits, as on a NEXT chain.
   Accepted cost: the order is not relative to a container,
   so one Part cannot sit differently in two Scores.
   If that is ever needed it belongs to a layout object, not the Score.
2. **An edge asserts immediate neighbours,** as NEXT does:
   `a STACKS_ABOVE b` means b is directly below a.
   A node has at most one `STACKS_ABOVE` out and one in;
   cycles are refused.
   Several unconnected chains are allowed;
   that is how partial knowledge is said.
3. **Anything that stacks may be chained:**
   a `Part`, a `LineGroup`, a line head, a `SyncLine`.
   The edge never says two things share a staff:
   a drum kit's lines share one staff and are not chained;
   which lines share a staff stays with P11 (staff assignment).
4. **A bracket is a `Spanner` over the chain,**
   `StackGroup`, with STARTS_AT its first member and ENDS_AT its last,
   as a slur spans a NEXT chain.
   Score membership stays flat;
   a group's members are contiguous by construction;
   nesting is spans inside spans,
   and MusicXML's overlapping (non-nested) groups are representable.
5. **The symbol is a WSMN value.**
   Core has an abstract `StackGroupShape`
   (as `DivisionShape` is to `BarLineShape`);
   WSMN has `BracketShape` with the symbol and how bar lines join.
   Core never reads a shape.

## 3. Model

### 3.1 `EdgeType.STACKS_ABOVE`

Plain `OmkEdge`, from the upper node to the one directly below.
Added to `EdgeType` in `graph/edge.py`
and to `DEFAULT_EDGE_STYLES` in `visualization/config.py` (`_DOTTED`).
The layout needs no other change; whether stacked members should be laid out
in their stack order is a separate visualization question, not done here.

### 3.2 `StackGroup(Spanner)` in `objects/part.py`

Beside `LineGroup`, with which it is easily confused, so each docstring
says what the other is for: a `LineGroup` is lines played together and
measured from one origin; a `StackGroup` is a run of the stack drawn as
one unit.

```python
@dataclass(kw_only=True, slots=True)
class StackGroup(Spanner):
    name: str | None = None
    abbreviation: str | None = None
    shape: StackGroupShape | None = None   # None: no particular drawing
```

`Spanner`'s docstring is widened:
its span is a run of a NEXT chain or of a stack.

### 3.3 `values/scoring/stack_group_shape.py`: `StackGroupShape`

Abstract, empty, frozen; mirrors `DivisionShape` exactly.

### 3.4 `systems/wsmn/scoring/bracket_shape.py`: `BracketShape`

```python
class BracketSymbol(StrEnum):    # MusicXML group-symbol
    BRACKET, BRACE, LINE, SQUARE

class GroupBarLines(StrEnum):    # MusicXML group-barline
    SEPARATE      # "no": each staff's bar lines are its own
    JOINED        # "yes": drawn through the gaps between staves
    MENSURSTRICH  # only in the gaps, not through the staves

@dataclass(frozen=True, slots=True)
class BracketShape(StackGroupShape):
    symbol: BracketSymbol | None = None    # None: MusicXML "none"
    bar_lines: GroupBarLines = GroupBarLines.SEPARATE
```

Ready-made in `systems/wsmn/scoring/symbols.py`:
`bracket`, `brace`, `bracket_joined`, `brace_joined`.
Repr round-trips (`BracketShape(symbol=BracketSymbol.BRACE, bar_lines=...)`).

## 4. Graph API (`OmkGraph`, new section "Stacks")

Named after the NEXT-chain methods they mirror.

- `add_stacked(upper, lower)`: one edge (as `add_next`).
  Raises `GraphError` if `upper` already has a node below it,
  `lower` already has one above it,
  the edge would close a cycle,
  either node is not stackable (§2.3),
  or a line head is not a head or is branched
  (the `add_to_group` rule).
- `add_stack(members)`: chains a sequence top to bottom (as `add_line`).
- `insert_stacked(node, upper, lower)`: puts `node` between two neighbours
  (as `insert_event`).
- `stacked_below(node)` / `stacked_above(node)`: the neighbour or None
  (as `get_next` / `get_previous`).
- `walk_stack(node)`: from `node` down to the bottom of its chain
  (as `walk_line`).
- `remove_from_stack(node)`: takes `node` out of its chain and splices its
  neighbours together, so a → b → c becomes a → c.
  A `StackGroup` with `node` as an endpoint moves that endpoint one step
  inward; a group whose only member was `node` is removed.
  `remove_node` itself is unchanged
  (it drops edges and does not splice NEXT either).
- `add_stack_group(group, first, last)`: STARTS_AT `first`, ENDS_AT `last`.
  Raises `GraphError` unless `last` is `first` or is reached from it
  by walking down.
  Both ends are required:
  MusicXML always closes a group, and no other consumer asks for an open one.
- `stack_group_members(group)`: the members from first to last, in order.
- `stack_groups_of(node)`: the groups whose span includes `node`.

Not added: any score-level "page order" query.
The writer walks the chain from the top of its score's members (§6).

## 5. Reader changes (`io/musicxml/reader.py`)

- Every `<score-part>` in part-list order is chained with `add_stack`:
  the `Part`, or for a drum kit its `LineGroup`
  (the kit's `PercussionPart`s share one staff, so they are not chained).
- A multi-staff part's `LineGroup` heads are chained in staff order.
  The head's `staff` meta stays (P11's business, and voices need it).
- `<part-group>` start/stop pairs by `number` become `StackGroup`s
  from the first to the last member opened and closed under them,
  with `name`, `abbreviation` and a `BracketShape` from
  `group-symbol` and `group-barline`;
  `group-time` is ignored (counted).
  A group that never stops, or contains no part, warns and is dropped.
- The bar grid's `SyncLine` is not chained (it is not drawn).
- `Part.meta["musicxml"]` loses `index` and `groups`;
  the reader docstring's meta schema and `_plans/musicxml.md` §5.2, §5.11,
  §7 P1 and stage 5 are updated to match.

## 6. Writer contract (for stage 6; not built here)

`<part-list>` order is the score's chain read from its top member;
each `StackGroup` over parts becomes a `<part-group>` start before its
first part and stop after its last, numbered by nesting depth.

When the score's parts are not one chain
(several chains, or unchained parts),
the writer writes the chains in turn,
ordered by their top member's name,
an unchained part being a chain of one,
and warns, naming the parts whose order it chose
(developer, 2026-10-19; `_plans/musicxml.md` §12).

## 7. Tests

- `tests/graph/test_stack.py`, example-based:
  each method, each `GraphError` branch,
  splicing on removal, endpoint moves and group removal,
  nested and overlapping groups,
  a group whose last member is above its first refused.
- Same file, a Hypothesis property:
  random `add_stack` / `insert_stacked` / `remove_from_stack` sequences
  against a list-of-lists model; after every step
  each chain's `walk_stack` equals the model,
  no node has two neighbours in either direction,
  and every `StackGroup`'s members are a contiguous run of one model chain.
- `BracketShape`: doctests (repr round trip, equality); no exhaustive test,
  since it has no arithmetic.
- `tests/io/musicxml/test_reader.py`, one small document per rule:
  part-list order, nested part-groups with symbols and Mensurstrich,
  group name and abbreviation, an unclosed group warns,
  piano staves chained in staff order, a kit's group chained and its lines not.
- `tests/io/musicxml/test_corpus.py`: the quartet's chain is
  Violin 1 → Violin 2 → Viola → Violoncello under one bracket `StackGroup`.
- Graph equivalence and JSON round trip carry the new edge type unchanged;
  checked by the existing round-trip tests, with a stacked fixture added
  to one of them if none already covers an arbitrary edge type.

## 8. Execution

0. Heavy baseline (`uv run pytest --hypothesis-profile=thorough -m ""`).
1. Model and graph: §3, §4, `tests/graph/test_stack.py`.
   `Claude: STACKS_ABOVE edges and StackGroup; BracketShape; stack methods on OmkGraph; tests`
2. Reader: §5 and its tests; `_plans/musicxml.md` updated.
   `Claude: MusicXML reader chains parts and staves, reads part-groups as StackGroups; tests`
3. Heavy run; this plan to `_plans/completed/`;
   the revisit entry "Part order and bracketing have no home on a Score"
   moved to `_plans/completed/small-items.md`.
