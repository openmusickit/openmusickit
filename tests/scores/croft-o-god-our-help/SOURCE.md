# O God, our help in ages past (St Anne)

Composer: William Croft (tune St Anne, 1708); words: Isaac Watts.
Editor: Andrew Sims, CPDL #61856 (posted 2020-12-06).
Edition notes (CPDL): "The hymn with four-part harmony and underlaid words
in the version published in Hymns Ancient & Modern New Standard."
Category: SATB hymn on two staves with stacked stanzas.

## Source

- Work page:
  https://www.cpdl.org/wiki/index.php/O_God,_our_help_in_ages_past_(William_Croft)
- Files:
  - https://www.cpdl.org/wiki/images/7/74/AMNS_99_St_Anne_Harmony.mxl
  - https://www.cpdl.org/wiki/images/a/a0/AMNS_99_St_Anne_Harmony.pdf

CPDL answered every request with a Cloudflare 403,
so both files were downloaded on 2026-09-29
from the Internet Archive's raw (`id_`) captures of those URLs:
page 20241214050121, mxl 20210615110126, pdf 20210618190629.
Each file's SHA-1 matches the digest in the Wayback CDX index.

License: CPDL (ChoralWiki) license,
https://www.cpdl.org/wiki/index.php/ChoralWiki:CPDL

## Files

- `AMNS_99_St_Anne_Harmony.mxl`: compressed MusicXML 2.0,
  exported from Capella by CapToMusic.py 2.10 (2020-12-06)
- `AMNS_99_St_Anne_Harmony.pdf`: score, 1 page (created 2020-12-06)
- `AMNS_99_St_Anne_Harmony.corrected.musicxml`: **an edited copy**, uncompressed,
  made 2026-09-29 (see "Known flaws" below); the only edits are the
  52 `<syllabic>` values set to match the hyphenation printed in the PDF

Both are rendered from the same Capella file,
kept byte-for-byte under their distributed names.
The edition's Capella source (`AMNS_99_St_Anne_Harmony.capx`)
is listed on CPDL but was not archived, so it is absent.

## Notable for testing

Six stanzas stacked under the treble staff (`<lyric number="1">` to `"6"`),
S/A and T/B sharing staves as voices 1 and 2, C major, 4/4.
Pickup numbered as measure 0 without `implicit="yes"`;
the mid-hymn line break splits a bar into a 3-beat and a 1-beat measure.
A hidden, empty first part (P1) carries only rests.
Breath marks are `<words>,</words>` directions, not `<breath-mark>`.
The PDF sets stanzas 2, 4 and 6 in italics; the MusicXML does not.

## Known flaws (kept in the original; fixed in the companion)

- 52 of the 168 `<syllabic>` flags contradict the hyphenation on the page
  (verse 1 marks "ter" of shel-ter as `single`;
  verse 3's flags mostly belong to a different hyphenation).
  The syllable texts are correct and in order, only the flags are wrong,
  so this is a CapToMusic bug.
  A reader must keep the syllables in order and treat the flags as advisory;
  hyphenation itself is tested on the corrected companion.
- The metadata (title, tune name, author, source, editor) is typed as
  free `<words>` directions; there is no `<work>` or `<creator>`.
- `<sound tempo="120">` is Capella's default playback tempo;
  the page prints no tempo.
- The hidden part `P1` (`<staff-details print-object="no">`)
  holds ten rests and nothing else.
