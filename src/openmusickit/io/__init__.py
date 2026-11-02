"""Readers and writers for interchange formats.

Each format is a subpackage that turns a file into an `OmkGraph` and back:
`io.musicxml` for MusicXML (`.musicxml`, `.xml`, compressed `.mxl`),
and `io.omk_json` for OMK's own JSON format (`.json`), which holds a whole graph.
A format module may know one musical system well
(MusicXML is Western Standard Music Notation),
which is why these live outside `objects` and `graph`,
which know none.
`OmkGraph.from_file`, `import_file` and `export_file` dispatch here by suffix.
"""

from openmusickit.io import musicxml, omk_json

__all__ = ["musicxml", "omk_json"]
