# Open Music Kit

Music encoding/decoding tools for computational analysis and machine learning.

## Reading and writing MusicXML

```python
from openmusickit.io.musicxml import canonicalize, compare, read, write
from openmusickit.io.musicxml.container import load

graph = read("score.mxl")              # .musicxml, .xml or compressed .mxl
write(graph, "copy.musicxml")          # MusicXML 4.0; a name ending in .mxl is compressed

# Did the copy keep the music? An empty list means it did.
print(compare(canonicalize(load("score.mxl")), canonicalize(load("copy.musicxml"))))
```

`OmkGraph.from_file` and `export_file` do the same by file suffix.
What the reader cannot place, and the writer cannot write, it reports as an `OmkWarning`.
See `docs/musicxml.qmd` for a walk-through.
