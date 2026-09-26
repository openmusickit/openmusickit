# Mathy bits

Formal descriptions of the operations that are in the code,
explicitly or implicitly,
with paste-ready MathJax.
Audience: me.
Each entry is *what it is* plus *the markup*.
Source pointers are module-qualified, not file paths.

Claims marked **(checked)** were verified exhaustively over the relevant
finite domain, or over the symbol table, at the time of writing.

---

## 0. Notation used throughout

| symbol | meaning |
|---|---|
| \(T\), \(I\) | tone set, interval set of a tonal system |
| \(V\), \(V^{o}\) | WSMN abstract and octave-qualified tonal vectors |
| \(\chi(d)\) | chromatic value of the natural letter \(d\) (`DIATONES[d].chromatic`) |
| \(\alpha\) | accidental alteration, half-steps from natural |
| \(\iota\) | semitone map (`__int__`) |
| \(\varphi\) | line-of-fifths map (`fifths_position`) |
| \(\mathcal{D}_S\) | durations of temporal system \(S\) |
| \(\ell\) | rational length (`rational_length`) |
| \(G\), \(G_t\) | the score graph, its timing subgraph |
| \(s\) | the NEXT successor partial function |

```latex
\chi(d) \quad \alpha \quad \iota \quad \varphi \quad \ell \quad \mathcal{D}_S \quad G_t
```

---

## 1. The abstract contract

### 1.1 Tonal system

A tone set, an interval set, a transposition action, a distance.
`Tone`, `Interval`, `TonalSystem`.

\[
\operatorname{transpose}: T \times I \to T,
\qquad
\operatorname{distance}: T \times T \to I
\]

The directed version is what round-trips:

\[
\operatorname{transpose}\bigl(a,\ \operatorname{diff}(b,a)\bigr) = b
\]

In OMK, `distance` is the *undirected* magnitude, so this law holds for
`b - a`, **not** for `a.distance(b)`. See §2.5.

### 1.2 Temporal system

A set of notated lengths with a rational measure.
`TemporalSystem`, `TemporalElement`, `Measurable`.

\[
\ell : \mathcal{D}_S \to \mathbb{Q}
\]

### 1.3 System compatibility

The guard that stops two systems being mixed silently.
`TonalSystem.compatible_with`, `TemporalSystem.compatible_with`.

\[
S \frown S'
\;\iff\;
S = S' \ \lor\ \mathrm{univ}(S) \ \lor\ \mathrm{univ}(S')
\]

\(\frown\) is reflexive and symmetric but **not** transitive: the universal
system (`ANY_TONAL_SYSTEM`, `ZeroDuration`) is compatible with everything,
which is exactly what breaks transitivity.

```latex
S \frown S' \iff S = S' \ \lor\ \mathrm{univ}(S) \ \lor\ \mathrm{univ}(S')
```

---

## 2. WSMN tonal algebra

### 2.1 The carrier

A tonal vector is a diatonic and a chromatic coordinate,
optionally with an octave.
`TonalVector`, `tonal_arithmetic`.

\[
V = \mathbb{Z}_{7} \times \mathbb{Z}_{12},
\qquad
V^{o} = \mathbb{Z}_{7} \times \mathbb{Z}_{12} \times \mathbb{Z}
\]

Octave carry comes from the diatonic coordinate alone, so the octave-qualified
vectors are just \(\mathbb{Z}\times\mathbb{Z}_{12}\) in disguise **(checked)**:

\[
\delta : V^{o} \xrightarrow{\ \sim\ } \mathbb{Z}\times\mathbb{Z}_{12},
\qquad
(d,c,o) \longmapsto (d + 7o,\ c)
\]

\(\delta_{1}(x) = d + 7o\) is the staff position; `_diatonic_position`.

### 2.2 Addition

`tonal_sum`, `TonalVector.__add__`. Componentwise, with the diatonic overflow
pushed into the octave.

\[
(d_1,c_1) + (d_2,c_2)
= \bigl(\,d_1 + d_2 \bmod 7,\ \ c_1 + c_2 \bmod 12\,\bigr)
\]

\[
(d_1,c_1,o_1) + (d_2,c_2)
= \Bigl(\,\overline{d_1{+}d_2},\ \ \overline{c_1{+}c_2},\ \
o_1 + \bigl\lfloor \tfrac{d_1+d_2}{7} \bigr\rfloor \,\Bigr)
\]

Under \(\delta\) this is plain componentwise addition in
\(\mathbb{Z}\times\mathbb{Z}_{12}\) **(checked)**.

\(V\) is an abelian group; \(V^{o}\) is a \(V\)-set under \(+\), and the
projection is equivariant. Arities do not mix freely: a qualified vector may
be moved by an abstract interval, but not the other way round
(`TypeError`: an octave cannot be added to an abstract value).

\[
+ \;:\; V^{o} \times V \to V^{o},
\qquad
\pi(x + i) = \pi(x) + i
\]

```latex
(d_1,c_1,o_1) + (d_2,c_2) = \Bigl(\,\overline{d_1{+}d_2},\ \overline{c_1{+}c_2},\ o_1 + \bigl\lfloor \tfrac{d_1+d_2}{7} \bigr\rfloor \,\Bigr)
```

### 2.3 Alteration and the semitone map

`_tonal_unmodulo`, `tonal_int`, `_PitchRepresentation.alteration`.

The chromatic coordinate is read as the alteration *nearest the letter's
natural*, i.e. lifted into a window of \(\pm 6\):

\[
\tilde{c}(d,c) = \text{the representative of } c \bmod 12
\text{ in } \bigl[\chi(d)-6,\ \chi(d)+6\bigr]
\]

\[
\alpha(d,c) = \tilde{c}(d,c) - \chi(d),
\qquad
\iota(d,c,o) = \tilde{c}(d,c) + 12\,o
\]

So one vector carries up to six half-steps of alteration either way
(D♯ against F𝄫 is a quadruply diminished third).

**Homomorphism, conditionally (checked):**

\[
\iota(x+y) \equiv \iota(x) + \iota(y) \pmod{12}
\quad \text{for all abstract } x,y
\]

\[
\iota(x+y) = \iota(x) + \iota(y)
\quad \text{for qualified } x,y \text{ with } |\alpha| \le 3
\]

It fails only where the \(\pm 6\) window wraps — i.e. where the spelling runs
off the end of the accidental table. Worth saying in the paper: the semitone
map is a homomorphism *on the musically inhabited part of the carrier*, and
the failure is a fact about notation, not about pitch.

### 2.4 Enharmonic equivalence as a quotient

Code equality is equality in the carrier: spelling-sensitive.
Enharmonic equivalence is the strictly coarser quotient by \(\iota\).

\[
x \sim_{\text{enh}} y \iff \iota(x) = \iota(y),
\qquad
V^{o}/{\sim_{\text{enh}}}\ \cong\ \mathbb{Z},
\qquad
V/{\sim_{\text{enh}}}\ \cong\ \mathbb{Z}_{12}
\]

\[
x = y \;\Longrightarrow\; x \sim_{\text{enh}} y,
\qquad
x \sim_{\text{enh}} y \;\not\Longrightarrow\; x = y
\]

C♯ and D♭ are enharmonic and unequal; `hash` agrees with \(=\), not with \(\sim\).

### 2.5 Transposition, difference, distance

`transpose`, `__add__`, `__sub__`, `distance` (`tonal_abs_diff`).

\[
\operatorname{transpose}(a, i, \uparrow) = a + i,
\qquad
\operatorname{transpose}(a, i, \downarrow) = a - i
\]

The directed difference is the one with the torsor law **(checked, all
\(7056\) abstract pairs)**:

\[
a + (b - a) = b
\]

`distance` is the undirected magnitude — the smaller of the two directed
differences, spelled as an interval:

\[
\operatorname{dist}(a,b)
= \min_{\preceq}\bigl\{\, \operatorname{ic}(b-a),\ \operatorname{ic}(a-b) \,\bigr\},
\qquad
\operatorname{dist}(a,b) = \operatorname{dist}(b,a)
\]

**(checked)** symmetric everywhere; on abstract vectors with \(|\alpha|\le 1\)
it is bounded by the tritone:

\[
\bigl|\iota\bigl(\operatorname{dist}(a,b)\bigr)\bigr| \le 6
\]

And the caveat worth a sentence in the paper: \(a + \operatorname{dist}(a,b)
= b\) fails in general (it holds only when \(b\) is above \(a\) and there is no
enharmonic tie), because the magnitude has thrown away the direction and the
spelling. C4 and B♯3 are a distance of a diminished second apart in either
direction, and neither one is the other transposed by it.

### 2.6 Inversion

`tonal_invert`, `TonalVector.inversion`. Reflection through a centre.

\[
\operatorname{inv}_{y}(x) = y - (x - y) = 2y - x
\]

**(checked)** an involution, and equal to the affine reflection, over all
\(7056\) pairs:

\[
\operatorname{inv}_{y} \circ \operatorname{inv}_{y} = \mathrm{id},
\qquad
\operatorname{inv}_{0}(x) = -x
\]

Interval inversion in the classical sense is inversion about the origin, which
in \(V\) is just negation: a major third \((2,4)\) inverts to a minor sixth
\((5,8) = -(2,4)\).

```latex
\operatorname{inv}_{y}(x) = y - (x - y) = 2y - x, \qquad \operatorname{inv}_{y}\circ\operatorname{inv}_{y} = \mathrm{id}
```

### 2.7 Interval class

`abs_interval`: the smaller of an interval and its inversion.

\[
\operatorname{ic}(x) = \min_{\preceq} \{\, x,\ -x \,\}
\]

### 2.8 Order

`__lt__`, `__gt__` compare by semitone only, so they are a **preorder** whose
induced equivalence is exactly enharmonic equivalence:

\[
x \prec y \iff \iota(x) < \iota(y)
\]

`tonal_higher_of` / `tonal_lower_of` break the enharmonic tie by staff
position, which refines it to a **total order (checked, injective on both
\(V\) and \(V^{o}\))**:

\[
x \sqsubset y
\iff
\bigl(\iota(x),\ \delta_{1}(x)\bigr)
<_{\mathrm{lex}}
\bigl(\iota(y),\ \delta_{1}(y)\bigr)
\]

`tonal_larger_of` / `tonal_smaller_of` are the same thing on magnitudes
(interval size rather than pitch height).

### 2.9 Octave qualification

`qualify_octave`, `unqualify_octave`, `conditional_qualify_octave`:
a projection and a family of sections.

\[
\pi : V^{o} \to V,\ (d,c,o)\mapsto(d,c);
\qquad
\sigma_{o} : V \to V^{o},\ (d,c)\mapsto(d,c,o);
\qquad
\pi \circ \sigma_{o} = \mathrm{id}_{V}
\]

### 2.10 Nearest instance

`tonal_nearest_instance`: pick the representative of \(b\)'s fibre closest to
\(a\), ties to the smaller diatonic step (Lilypond's relative-octave rule).

\[
\operatorname{near}(a,b)
=
\operatorname*{arg\,min}_{\,b' \in \pi^{-1}(\pi(b))}
\ \bigl(\, \bigl|\iota(a)-\iota(b')\bigr|,\ \ \bigl|\delta_{1}(a)-\delta_{1}(b')\bigr| \,\bigr)
\]

\[
\pi\bigl(\operatorname{near}(a,b)\bigr) = \pi(b),
\qquad
\bigl|\iota(a) - \iota(\operatorname{near}(a,b))\bigr| \le 6
\]

### 2.11 The line of fifths

`fifths_position`. Naturals step by 2 (mod 7, re-centred on C), each sharp
adds 7. The line does **not** wrap — B♯ is 12, not 0 — because spelling is
what is being counted.

\[
\varphi(d,c) = \bigl((2d+1) \bmod 7\bigr) - 1 + 7\,\alpha(d,c)
\]

**A group homomorphism (checked, exact for all \(|\alpha| \le 3\), which is
the whole representable key-signature range):**

\[
\varphi(x + y) = \varphi(x) + \varphi(y),
\qquad
\varphi : V \to \mathbb{Z}
\]

Read as a pitch, \(\varphi\) is the signed number of sharps in the major key
on that tonic. Read as an interval, it is how far a key signature travels
around the circle when its tonic moves by that interval. This is the cleanest
statement in the tonal half: *transposition acts on key signatures by
translation on the line of fifths.*

```latex
\varphi(d,c) = \bigl((2d+1) \bmod 7\bigr) - 1 + 7\,\alpha(d,c), \qquad \varphi(x+y) = \varphi(x)+\varphi(y)
```

---

## 3. Lifting a tonal operation

### 3.1 Pointwise action

Every `transform` / `transform_tones` in the codebase is the same thing: a
tone operation pushed through a structure pointwise.
`apply_tone_operation` is the single guard (`TypeError` unless the result is a
`Tone`).

\[
f_{*}(t_1,\dots,t_n) = \bigl(f(t_1),\dots,f(t_n)\bigr),
\qquad
(g \circ f)_{*} = g_{*} \circ f_{*},
\qquad
(\mathrm{id})_{*} = \mathrm{id}
\]

Carriers: `ToneCollection.transform`, `NoteEvent.transform_tones`,
`Chord.transform`, `KeySignature.transform`, `Key.transform`,
`ModalContextEvent.transform_tones`, `OmkGraph.transform_tones`.

Universal-system tones are fixed points (a rest stays a rest):

\[
f(t) = t \quad \text{whenever } \mathrm{univ}\bigl(\mathrm{sys}(t)\bigr)
\]

### 3.2 Tone collections

`ToneCollection`: an *ordered* tuple with an optional root and a name
template. Order is musically significant (added 2nd vs. added 9th), so this
is a sequence, not a set.

\[
\mathbf{t} = (t_1,\dots,t_n),\ r \in T \cup \{\bot\}
\]

\[
f_{*}(\mathbf{t}, r) = \bigl(f_{*}\mathbf{t},\ f(r)\bigr)
\]

Equality ignores the name:

\[
(\mathbf{t}, r, \nu) = (\mathbf{t}', r', \nu')
\iff
\mathbf{t} = \mathbf{t}' \ \land\ r = r'
\]

Subsets: `combinations(k)` and `all_combinations` are order-preserving
\(k\)-subsets.

\[
\binom{\mathbf{t}}{k},
\qquad
\Bigl| \bigcup_{k=2}^{n-1} \binom{\mathbf{t}}{k} \Bigr|
= 2^{n} - n - 2
\]

### 3.3 Chords

`ChordType` is an interval pattern rooted at the origin; `Chord` is that
pattern realized at a root. Realization is the group action.

\[
\tau \subseteq V,\ \ 0 \in \tau,\ \ b \in \tau
\qquad
\tau(r) = \{\, r + t : t \in \tau \,\},\ \text{bass } b + r
\]

Transposition commutes with realization — which is why `ChordType.transform`
raises rather than doing anything:

\[
T_{i}\bigl(\tau(r)\bigr) = \tau(r + i)
\]

Inversion is a change of bass, not a change of tones; arpeggiation is the
cyclic rotation that brings the bass to the front.

\[
\rho_{b}(t_1,\dots,t_n) = (t_k,\dots,t_n,t_1,\dots,t_{k-1}),
\qquad t_k = b
\]

Slash notation \(C/E\) is `__truediv__`, i.e. \(\tau \mapsto (\tau, b')\).

### 3.4 Key signatures

`KeySignature`: an alteration per letter.

\[
\kappa : \mathbb{Z}_{7} \to \{-3,\dots,3\}
\]

`fifths` is defined only on *standard* signatures — those whose values, read
in sharp order \(F\,C\,G\,D\,A\,E\,B\), take at most two distinct values
differing by one and are non-increasing:

\[
\mathrm{fifths}(\kappa) = \sum_{d\in\mathbb{Z}_7} \kappa(d)
\qquad (\kappa \text{ standard})
\]

`from_alts` is its section: \(\mathrm{fifths}(\kappa_n) = n\).

Transformation runs each letter through \(f\) as a pitch and reads the
alteration back off the image letter; it is defined only when the induced
letter map is a bijection of \(\mathbb{Z}_7\) (otherwise two letters collide
and there is no signature):

\[
\kappa'\bigl(\pi_{1}f(d,\ \chi(d)+\kappa(d))\bigr)
= \alpha\bigl(f(d,\ \chi(d)+\kappa(d))\bigr)
\]

### 3.5 Keys and modes

`ModePattern` is an interval pattern through the origin; a `Key` is a mode at
a tonic, plus a signature.

\[
M \subseteq V,\ 0 \in M
\qquad
K = (r,\ M,\ \kappa),
\qquad
\mathrm{tones}(K) = M(r)
\]

`Key.transform` **keeps the mode**:

\[
f \cdot (r, M, \kappa) = \bigl(f(r),\ M,\ f_{*}\kappa\bigr)
\]

Worth a remark in the paper: for translations this agrees with transforming
the tones, and for everything else it does not. C major inverted about C is C
major by "keep the mode" and C Phrygian by "transform the tones". The code
picks the first; the divergence is exactly the statement that a mode is a
pattern, not a set.

A bare signature (no tonic) moves with the music; `NoKey` (no tonic, no
signature) is a fixed point of every \(f\).

---

## 4. Temporal algebra

### 4.1 Length

`Measurable.rational_length`. Additive, sign-preserving, surjective onto the
positives.

\[
\ell : \mathcal{D}_S \to \mathbb{Q},
\qquad
\ell(a + b) = \ell(a) + \ell(b),
\qquad
\ell(-a) = -\ell(a),
\qquad
\ell(\mathbf{0}) = 0
\]

**(checked over the symbol table)** addition is commutative and associative,
\(a + (-a) = \mathbf{0}\), and \(\mathbf{0}\) is a two-sided identity across
systems.

\((\mathcal{D}_S, +, \mathbf{0})\) is a commutative monoid with negation;
\(\ell\) is a monoid homomorphism to \((\mathbb{Q}, +, 0)\).

### 4.2 Equality as a quotient

Durations compare and hash by length, not spelling: a dotted quarter *is*
three eighths *is* `TemporalUnit(3, eighth)`.

\[
a \equiv b \iff \ell(a) = \ell(b),
\qquad
a < b \iff \ell(a) < \ell(b),
\qquad
\mathcal{D}_S / {\equiv}\ \cong\ \ell(\mathcal{D}_S) \subseteq \mathbb{Q}
\]

Sequences are measured by their sum, so a `Measurable` compares against any
iterable of them:

\[
\ell\bigl(\langle a_1,\dots,a_n\rangle\bigr) = \sum_{i} \ell(a_i)
\]

Only within compatible systems (§1.3): incompatible elements are never equal,
and ordering them is an error rather than a `False`.

\[
\neg(S \frown S') \;\Longrightarrow\;
a \ne b \ \text{ and } \ a < b \ \text{ undefined}
\]

### 4.3 Scaling

`Measurable.scale`: a partial action of the positive rationals.

\[
\cdot : \mathcal{D}_S \times \mathbb{Q}_{>0} \rightharpoonup \mathcal{D}_S,
\qquad
\ell(a \cdot k) = k \cdot \ell(a),
\qquad
(a \cdot k) \cdot k^{-1} = a
\]

**(checked)** exact for every symbol and every positive rational scalar;
`ScalingError` for \(k \le 0\) or where the system cannot spell the result.
Powers of two preserve the spelling; other scalars may change the notation
(quarter \(\times 3\) is a dotted half, quarter \(\times \frac{2}{3}\) is a
triplet quarter, quarter \(\times 5\) is a tie).

### 4.4 The notatable values

The set of lengths writable as **one symbol**: a power-of-two base with
\(k\) dots.

\[
N = \Bigl\{\, 2^{\,j}\,\bigl(2^{\,k+1}-1\bigr)\,2^{-k}
\;\Bigm|\;
j \in \mathbb{Z},\ k \in \mathbb{Z}_{\ge 0} \,\Bigr\}
\]

### 4.5 Notation as a section of length

`MetricalDuration.from_length`: every positive rational gets a canonical
spelling.

\[
\nu : \mathbb{Q}_{>0} \to \mathcal{D}_{\text{WSMN}},
\qquad
\ell \circ \nu = \mathrm{id}_{\mathbb{Q}_{>0}}
\]

**(checked)** \(\nu\) is a section of \(\ell\), and a right inverse on single
symbols: \(\nu(\ell(a)) = a\) with the same nominal value, dots and ratio.

The three rules, as a case split:

\[
\nu(x) =
\begin{cases}
\text{the symbol } x & x \in N \\[4pt]
\text{tuplet } k : 2^{\lfloor \log_2 k \rfloor}
  & k = \mathrm{odd}\bigl(\mathrm{den}(x)\bigr) > 1 \\[4pt]
\text{greedy tie} & \text{otherwise}
\end{cases}
\]

Greedy tie split, largest single symbol first:

\[
x = \sum_{i=1}^{m} n_i,
\qquad
n_i = \max\Bigl\{\, n \in N \;\Bigm|\; n \le x - \textstyle\sum_{j<i} n_j \,\Bigr\}
\]

\(\nu\) is canonical, not context-aware: it ignores the meter and the beat
position, which is the honest limit to state in the paper.

### 4.6 Ratios: tuplets, tempo, modulation

`TemporalRatio`. One object for three jobs, distinguished only by which
systems the two sides live in.

\[
R = \bigl(\text{nominal},\ \text{contextual}\bigr),
\qquad
m(R) = \frac{\ell(\text{contextual})}{\ell(\text{nominal})}
\]

\[
\ell_{\text{real}}(d) = \ell_{\text{nom}}(d)\cdot m(R)
\]

Equality and hashing are by multiplier, so a sextuplet \(6{:}4\) is the same
ratio as a triplet \(3{:}2\) on any base **(checked)**:

\[
R \equiv R' \iff m(R) = m(R')
\]

The three readings:

\[
\begin{aligned}
\text{tuplet:} &\quad S \to S \ \text{within one line} \\
\text{metric modulation:} &\quad S \to S \ \text{across a boundary} \\
\text{tempo:} &\quad S \to \text{clock time}
\end{aligned}
\]

Tempo is the ratio against real time; the multiplier comes out in
microseconds per whole note.

\[
\mathrm{Tempo}(n,\beta)
= \bigl(\langle n,\beta\rangle,\ \langle 1, \text{60\,s}\rangle\bigr),
\qquad
m = \frac{6 \times 10^{7}}{n \cdot \ell(\beta)}
\]

Conversion is then \(\mathbb{Q}\)-linear — a change of unit, nothing more:

\[
\mathcal{C}_{R} : \mathcal{D}_{S} \to \mathcal{D}_{\text{clock}},
\qquad
\mathcal{C}_{R}(d) = \ell(d)\cdot m(R)
\]

```latex
m(R) = \frac{\ell(\text{contextual})}{\ell(\text{nominal})}, \qquad \mathcal{C}_{R}(d) = \ell(d)\,m(R)
```

### 4.7 Meters

`TemporalUnit`, `CompoundTemporalUnit`, `TimeSignature`. A bar is an ordered
series of counted units; additive meters are several.

\[
U = (n, \beta),\ \ \ell(U) = n\,\ell(\beta)
\qquad
M = \langle U_1,\dots,U_k\rangle,\ \ \ell(M) = \sum_i \ell(U_i)
\]

\[
\mathrm{rem}\bigl(M, \langle s_i \rangle\bigr) = \ell(M) - \sum_i \ell(s_i)
\]

\[
\mathrm{oob}\bigl(M, \langle s_i \rangle\bigr)
= \min\Bigl\{\, i \;\Bigm|\; \textstyle\sum_{j \le i} \ell(s_j) > \ell(M) \,\Bigr\}
\]

Time signatures compare by total length alone: \(4/4 = 2/2 = 8/8\)
**(checked)**.

### 4.8 The zero and the graces

`ZeroDuration` is the identity of every system; `GraceDuration` is an element
of \(\ker \ell\) that still carries a notated symbol.

\[
\ell(g) = 0,
\qquad
a + g = g + a = a,
\qquad
-g = g
\]

So all graces are equal to each other and to zero; `nominal` is the extra
datum that distinguishes them. A run of graces adds nothing to the length of
a line — which is precisely the statement that they live in the kernel.

---

## 5. Graph operations

### 5.1 The object

`OmkGraph` over a `GraphAdapter`. A labelled multidigraph whose nodes are
score objects.

\[
G = \bigl(N,\ E,\ \mathrm{src},\ \mathrm{tgt},\ \tau\bigr),
\qquad
\tau : E \to \Lambda
\]

\(\Lambda\) is `EdgeType`; at most one edge of a given type between an ordered
pair.

Node identity is a UUID; node *equality* is musical content, with id and
`meta` excluded. So two separately built B♭ quarter notes are equal and
distinct:

\[
u = v \ \not\Longrightarrow\ u \equiv_{\mathrm{id}} v
\]

### 5.2 Lines

NEXT is a partial injective function: in-degree and out-degree at most one.

\[
\deg^{+}_{\mathrm{NEXT}}(v) \le 1,
\qquad
\deg^{-}_{\mathrm{NEXT}}(v) \le 1
\]

so the NEXT-components are paths or cycles, and a *line* is a maximal chain.
`walk_line` is the orbit of the successor \(s\), truncated at the first
repeat, which is what makes a cyclic line (a gamelan cycle) terminate:

\[
\mathrm{line}(v) = \bigl\langle v,\ s(v),\ s^{2}(v),\ \dots \bigr\rangle
\]

### 5.3 Spans

`walk_span`: the line, plus everything branched off it, transitively. Pins are
never crossed, so a span is the reachability closure under
\(\mathrm{NEXT} \cup \mathrm{BRANCHES}\).

\[
\mathrm{span}(v)
= \mathrm{line}(v) \ \cup
\bigcup_{u \in \mathrm{line}(v)} \ \bigcup_{h \in B(u)} \mathrm{span}(h)
\]

The shared visited-set makes this idempotent and terminating even when two
lines branch into each other.

\[
\mathrm{line}(v) \subseteq \mathrm{span}(v)
\]

### 5.4 The timing graph

This is the one I most want to get right in the paper.

Timing is a weight function on a subgraph, and a position is *always*
relative — there is no origin.

\[
w(u,v) =
\begin{cases}
\mathrm{dur}(u)
  & v = s(u) \\[4pt]
\mathrm{disp}(e)
  & e : u \to v \text{ timed},\ \mathrm{anchor}(e) = \text{onset} \\[4pt]
\mathrm{dur}(u) + \mathrm{disp}(e)
  & e : u \to v \text{ timed},\ \mathrm{anchor}(e) = \text{offset}
\end{cases}
\]

with \(w(v,u) = -w(u,v)\), and the edge simply **absent** where
\(\mathrm{dur}\) is undefined: an event of unknown duration is opaque, and
nothing after it or hanging from its offset has a known position.

\[
w : E_t \to \mathcal{D},
\qquad
\mathrm{dur}(u) = \bot \ \Longrightarrow\ (u, s(u)) \notin E_t
\]

Relative onset is a path sum (`_relative_onset`, breadth-first):

\[
\mathrm{on}(r, v) = \sum_{e \in P} w(e),
\qquad P : r \leadsto v
\]

\[
\mathrm{on}(r,r) = \mathbf{0},
\qquad
\mathrm{on}(u,v) = -\,\mathrm{on}(v,u)
\]

**(property-tested)** antisymmetric, zero on the diagonal, and equal to the
sum of the intervening durations along a line.

### 5.5 Consistency as a coboundary

The timing graph is consistent exactly when \(w\) is a coboundary — when a
global potential exists.

\[
\exists\, \phi : N \to \mathcal{D}
\ \text{ with }\
w(u,v) = \phi(v) - \phi(u)
\quad\iff\quad
\sum_{e \in C} w(e) = \mathbf{0}
\ \text{ for every cycle } C
\]

NEXT, BRANCHES and group CONTAINS edges form a **forest**, so a potential
always exists and no check is needed. Pins (`Simultaneous`) are the only
edges that can close a cycle, so they are the only source of inconsistency.

`check_alignment` measures the holonomy of each such cycle, edge by edge:

\[
\mathrm{conflict}(e)
\iff
w(e) \ne \mathrm{on}_{\,G_t \setminus e}\bigl(\mathrm{src}(e),\ \mathrm{tgt}(e)\bigr)
\]

and reports rather than raises: a disagreement between a pin and the durations
is a musical fact about an incomplete source, not a malformed graph.

```latex
\exists \phi:\ w(u,v) = \phi(v)-\phi(u) \iff \sum_{e\in C} w(e) = \mathbf{0} \ \ \forall C
```

### 5.6 Simultaneity, asserted and derived

Two notions, deliberately distinct.

**Asserted** — a pin with no displacement, symmetric in meaning, stored
directed:

\[
u \parallel v
\iff
\exists\, e : u \to v,\ \tau(e) = \mathrm{SIMULTANEOUS},\
\mathrm{anchor}(e) = \text{onset},\ \mathrm{disp}(e) = \bot
\]

**Derived** — equal onsets, computed:

\[
u \equiv_{t} v \iff \mathrm{on}(u, v) = \mathbf{0}
\]

\(\equiv_t\) is an equivalence relation on each connected component of
\(G_t\); \(\parallel\) is not transitive and not an equivalence — it is a
*claim*, and \(\parallel \subseteq \equiv_t\) is exactly the condition
`check_alignment` verifies.

\[
u \parallel v \ \Longrightarrow\ u \equiv_{t} v
\quad\text{(when consistent)}
\]

### 5.7 Containment, ownership, origin

Three different containments, distinguished by what they assert about timing:

\[
\begin{aligned}
\mathrm{BRANCHES} &:\ \text{same performer; span-inclusive; timed} \\
\mathrm{CONTAINS}\ (\text{LineGroup}) &:\ \text{timing origin; not span-inclusive} \\
\mathrm{CONTAINS}\ (\text{Score}) &:\ \text{membership only; untimed}
\end{aligned}
\]

A `Score` is deliberately *not* a timing origin: two of its lines with no pin
between them have no relative onset at all.

\[
\mathrm{on}(u,v) = \bot
\quad\text{for } u,v \text{ in the same Score, unlinked in } G_t
\]

### 5.8 Stints and materialization

A `Stint` is a closed interval of a line in span order, a `Part`'s run on it.

\[
S = [a, b] \subseteq \mathrm{span}(a),
\qquad
b = \bot \ \Rightarrow\ \text{to the end of the line}
\]

`materialize` forks a doubled line: it copies the **induced subgraph** on the
covered content and re-points the stint at the copy.

\[
H = G[\,\mathrm{content}(S)\,],
\qquad
H' \cong H,
\qquad
G \rightsquigarrow G \sqcup H'
\]

with the stint's STARTS_AT/ENDS_AT moved to \(H'\). Content is the events plus
their transitive attachments (marks, spanners, annotations, syllables); a
spanner with an endpoint outside \(\mathrm{content}(S)\) is dropped, because
the copy has no node for its other end. Not copied: relations to the rest of
the graph. So the fork is exact and *local*:

\[
\mathrm{span}(a) \text{ in } G \text{ unchanged},
\qquad
f_{*} \text{ on } H' \text{ does not touch } H
\]

### 5.9 Transformation over a span

`OmkGraph.transform_tones`: the pointwise action of §3.1, indexed by the span.

\[
f \cdot G
\ :\
\forall\, u \in \mathrm{span}(a,b) \cap \mathrm{TonalObject},
\quad
u \mapsto f_{*}(u)
\]

**(property-tested)** up then down is the identity, for every interval, over
the line and its branches together; the pinned line is untouched, which is the
graph-level statement that transposition follows ownership, not coincidence.

\[
T_{-i} \cdot \bigl(T_{i} \cdot G\bigr) = G
\]

### 5.10 Lyric binding

A LYRIC edge marks a syllable's **onset**, so the binding is a partial,
order-preserving, injective map from events to syllables.

\[
\lambda : E_{\text{line}} \rightharpoonup \Sigma
\]

\[
\mathrm{dom}\,\lambda
= \bigl\{\, e \;\bigm|\;
\ell(\mathrm{dur}(e)) \ne 0,\
\lnot\,\mathrm{rest}(e),\
e \notin \mathrm{interior}(\text{binding span}) \,\bigr\}
\]

What is actually *sung* at an event is the step function that carries the last
onset forward — which is what makes a melisma a fibre rather than a special
case:

\[
\hat{\lambda}(e)
= \lambda\Bigl(\max\bigl\{\, e' \le e \;\bigm|\; e' \in \mathrm{dom}\,\lambda \,\bigr\}\Bigr)
\]

\[
\text{melisma at } \sigma
= \hat{\lambda}^{-1}(\sigma),
\qquad
\bigl|\hat{\lambda}^{-1}(\sigma)\bigr| > 1
\]

A reciting tone is the dual case: several syllables at one event, added
explicitly with `connect_lyric_to_object`, so \(\lambda\) is injective only on
the zipped construction, not by fiat.

---

## 6. Translation across systems

### 6.1 Temporal

A `TemporalRatio` whose two sides are in different systems is a change of
unit. This is the *only* way durations cross a system boundary; without one,
comparison returns `False` and ordering raises.

\[
R_{S \to S'},
\qquad
\mathcal{C}_{R} : \mathcal{D}_{S} \to \mathcal{D}_{S'},
\qquad
\mathcal{C}_{R}(d) = \ell_{S}(d) \cdot m(R)
\]

\[
\mathcal{C}_{R'} \circ \mathcal{C}_{R} = \mathcal{C}_{R''},
\qquad
m(R'') = m(R)\,m(R')
\]

One punctum of chant to one quarter note is the same construction as
\(\text{quarter} = 120\); only the codomain differs.

### 6.2 Tonal

Any \(f : T_{S} \to T_{S'}\) may be pushed through the structures of §3 —
`transform_tones` does not require the result to be of the same type, only to
be a `Tone`. So translation between tonal systems is the same machinery as
transposition, with a different \(f\).

\[
f : T_{S} \to T_{S'},
\qquad
f_{*} : \mathcal{C}(T_{S}) \to \mathcal{C}(T_{S'})
\]

Universal tones are fixed (§3.1), so silence survives any translation.

### 6.3 Reading maps

`Stint.transposition` is not applied to the events — it is a map the consumer
applies while reading. Two parts over one line read it differently without
either owning it:

\[
\mathrm{read}_{S}(e) = T_{i_{S}}\bigl(\mathrm{content}(e)\bigr),
\qquad
i_{S} = \mathrm{transposition}(S)
\]

\[
\mathrm{read}_{S_1} \ne \mathrm{read}_{S_2}
\quad \text{over the same } e
\]

A clarinet in A and a concert-pitch flute are two readings of one event, which
is the point: the transposition lives on the relationship, not on the note.

---

## 7. Equality, collected

The paper will need this in one place: OMK uses at least seven distinct
equality relations, each a quotient of something.

\[
\begin{aligned}
\text{Tone / Interval} &:\ \text{equality in the carrier (spelling-sensitive)} \\
\text{enharmonic} &:\ \ker \iota,\ \text{strictly coarser} \\
\text{Duration} &:\ \ker \ell,\ \text{spelling-\textit{in}sensitive, within } \frown \\
\text{TemporalRatio} &:\ \ker m \\
\text{ToneCollection} &:\ (\mathbf{t}, r),\ \text{name excluded} \\
\text{Chord} &:\ (\mathbf{t}, r, b),\ \text{name and suffix excluded} \\
\text{OmkObject} &:\ \text{musical content; id and meta excluded} \\
\text{OmkEdge} &:\ (\tau, \mathrm{origin});\ \text{id and meta excluded}
\end{aligned}
\]

The pattern worth naming: **values are equal when they mean the same thing,
and the "same thing" is chosen per type.** Durations quotient away notation;
tones do not. That asymmetry is a claim about the two domains, not an
inconsistency: a dotted quarter and three tied eighths sound identical, C♯ and
D♭ do not behave identically.

Two invariants that go with it:

\[
a = b \ \Longrightarrow\ \mathrm{hash}(a) = \mathrm{hash}(b)
\]

\[
\text{value types are hashable and frozen};
\quad
\text{graph objects are mutable and unhashable}
\]

---

## 8. Formatting scraps

Things I keep re-deriving.

Inline and display:

```latex
\(x + i\)
\[ \operatorname{transpose} : T \times I \to T \]
```

Named operators (avoids italic run-together):

```latex
\operatorname{transpose} \quad \operatorname{dist} \quad \operatorname{inv}_y \quad \operatorname*{arg\,min}_{x \in X}
```

Maps and arrows:

```latex
f : A \to B \qquad A \xrightarrow{\ f\ } B \qquad A \hookrightarrow B \qquad A \twoheadrightarrow B
\qquad A \rightharpoonup B \quad\text{(partial)} \qquad A \xrightarrow{\ \sim\ } B \quad\text{(iso)}
```

Modular and floor:

```latex
d_1 + d_2 \bmod 7 \qquad \overline{d_1 + d_2} \qquad \bigl\lfloor \tfrac{d}{7} \bigr\rfloor
\qquad x \equiv y \pmod{12} \qquad \mathbb{Z}_{12} \quad \mathbb{Z}/12\mathbb{Z}
```

Cases:

```latex
\[
w(u,v) =
\begin{cases}
\mathrm{dur}(u) & v = s(u) \\
\mathrm{disp}(e) & \mathrm{anchor}(e) = \text{onset} \\
\mathrm{dur}(u) + \mathrm{disp}(e) & \mathrm{anchor}(e) = \text{offset}
\end{cases}
\]
```

Aligned multi-line:

```latex
\[
\begin{aligned}
\ell(a+b) &= \ell(a) + \ell(b) \\
\ell(-a)  &= -\ell(a) \\
\ell(a \cdot k) &= k\,\ell(a)
\end{aligned}
\]
```

Set-builder with sized delimiters:

```latex
\[
N = \Bigl\{\, 2^{\,j}\bigl(2^{\,k+1}-1\bigr)2^{-k} \;\Bigm|\; j \in \mathbb{Z},\ k \ge 0 \,\Bigr\}
\]
```

A commuting square without tikz (MathJax-safe):

```latex
\[
\begin{array}{ccc}
V & \xrightarrow{\ T_i\ } & V \\
\downarrow{\scriptstyle \varphi} & & \downarrow{\scriptstyle \varphi} \\
\mathbb{Z} & \xrightarrow{\ +\varphi(i)\ } & \mathbb{Z}
\end{array}
\]
```

Spacing, smallest to largest: `\,` `\:` `\;` `\quad` `\qquad`.
Text inside math: `\text{...}`, or `\mathrm{...}` for short operator-ish names.

### Not portable between MathJax and LaTeX

Things that compile in LaTeX but render as a red error in MathJax, so they
cannot go in the markdown source:

```latex
\textsc{...}    % LaTeX only — use \mathrm{NEXT} for enum-ish names
\text{\emph{}}  % LaTeX only — use \textit{...} inside \text{...}
```

MathJax has no small caps at all, which is why the edge types are set as
\(\mathrm{NEXT}\), \(\mathrm{BRANCHES}\), \(\mathrm{CONTAINS}\),
\(\mathrm{SIMULTANEOUS}\) — all-caps roman, matching how `EdgeType` spells
them in the code.
