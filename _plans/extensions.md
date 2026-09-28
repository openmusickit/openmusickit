# Planned Extensions

List and short description of planned extension libraries.
The purpose of this list is to help scope the work of OMK Core (this repo);
if something is a better fit for one of these libraries,
and is not needed as either an abstraction or WSMN implementation,
for the majority of "normal" score prep or "average" Western music,
it should not be included in the present library.

- Workbench - UI app for building, manipulating, interacting with OMK graphs

- OMK Theory Graph - Graphs as analysis and composition tool (a Theory Graph is not score, but a representation of theoretical knowledge/capabilities)
- OMK OCR - Optical character recognition (printed score -> OMK Graph)
- OMK Analysis - Harmonic and structural analysis, Roman numerals, Schenker
- OMK Gregorian - Chant and medieval notation, gabc/gregorio interop
- OMK Baroque - Figured bass, continuo realization
- OMK Session - Chord charts, Nashville numbers
- OMK MIDI - Ports, clocks, controllers (OMK Core *may* expose a small amount of MIDI-related functionality)
- OMK Tablature - Fret diagrams, string fingerings
- OMK Education - Exercises, fill-in-the-graph, graded etudes, etc
- OMK Audio - Advanced playback, audio processing, spectral analysis (OMK Core *may* expose a small amount of playback capability)
- OMK Lattice - 20th/21st century post-tonal theory; rows, serialism, tonnetz, aleatoric.
- OMK Orchestral - Instruments, advanced techniques, orchestral patterns. (OMK will include a basic set of Instrument definitions.)
- OMK Counterpoint - Voice leading rules, part-writing utilities
- OMK Jazz - Advanced chord theory, reharmonization utilities, chord scales, modern modal harmony
- OMK Sync - Video, key frames
- OMK Microtonal - tunings, temperament, non 12TET, quarter tones
- OMK Ludo - Video games, interactive compositions, state-driven transitions
- OMK Algo - algorithmic and generative composition tools, including AI
- OMK I/O - MusicXML, Lilypond, ABC, CHARM, interop (OMK will include a baseline MusicXML import/export capability, as well as JSON serialization).
- OMK Console - Terminal tools
- OMK Cloud - remote storage, sharing, and collaboration
- OMK Vector - tokenization and ML training utilities
- OMK Corpus - collections, corpora, search
- OMK Stage - cueing, dance, and live performance tools
- OMK Engrave - printable scores, parts, page layout (we may not implement this, and rely on MusicXML->MuseScore and Lilypond forever)
- OMK Orpheus - ancient music tools
- OMK Quilt - re-implementation of Patchwork/Open Music (possible heavy overlap with Algo)


And if we get subject-matter expert implementers:

- OMK Gamelan
- OMK India
- OMK <every musical system>


Some of these are likely to be dependent on each other:
Theory Graph underpins Counterpoint, Lattice, Algo, Quilt;
Vector is a precursor to serious AI work in Algo;
Education probably uses Analysis tools;
Cloud and Corpus likely have overlapping concerns.
Etc.
