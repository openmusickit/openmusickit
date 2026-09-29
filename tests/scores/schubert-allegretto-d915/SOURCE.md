# Allegretto in C minor, D.915

Composer: Franz Schubert (1827).
Edition: OpenScore, 2017,
typeset from the edition by August Spanuth (IMSLP #03109).
Category: solo piano.

## Source

- Page: https://imslp.org/wiki/Allegretto_in_C_minor,_D.915_(Schubert,_Franz)
- PDF: https://imslp.org/wiki/File:PMLP07743-Schubert_-_Allegretto_in_C_Minor_D.915.pdf
  (download: https://imslp.org/wiki/Special:ImagefromIndex/476002)
- Engraving files zip (MuseScore & MusicXML):
  https://imslp.org/wiki/File:PMLP07743-Schubert_-_Allegretto_in_C_Minor_D.915.zip
  (download: https://imslp.org/wiki/Special:ImagefromIndex/476003)
- MuseScore original, as named in the MusicXML: http://musescore.com/openscore/scores/4040956

License: CC0 1.0, https://creativecommons.org/publicdomain/zero/1.0/

## Files

- `Schubert_-_Allegretto_in_C_Minor_D.915.mxl`: compressed MusicXML (MuseScore 2.1 export), from the zip
- `Schubert_-_Allegretto_in_C_Minor_D.915.mscz`: MuseScore 2 source, from the zip
- `PMLP07743-Schubert_-_Allegretto_in_C_Minor_D.915.pdf`: score, 6 pages (page 1 is a title page)
- `Schubert_-_Allegretto_in_C_Minor_D.915.corrected.musicxml`: **an edited copy**, uncompressed,
  made 2026-09-29 (see "Known flaws" below); the only edits are
  `print-object="no"` on the twelve `<direction>`s holding the hidden metronome marks

The two files from the zip are byte-for-byte as distributed;
the zip's `__MACOSX/` resource forks were dropped.
All three files carry the same export timestamp (2017-06-05 17:26 UTC).

## Notable for testing

6/8, C minor with a key change to A-flat major and back.
Pedal marks throughout, `una corda` text, many hairpins, dynamics from pp to ff, fz, fp.
Second voices in both staves, chords, fermatas, accents, rit./a tempo.
79 of the 94 ties are partial-chord ties (one or two tones of a chord tied).

## Known flaws (kept in the original; the first is fixed in the companion)

- The `.mscz` holds 13 tempo marks, 12 of them invisible
  (playback realizations of rit. and a tempo in bars 7, 8, 15, 16, 17, 36, 37 and 40);
  MuseScore 2.1 exported all 13 as printed `<metronome>` marks
  without `print-object="no"`, so the XML claims twelve metronome marks
  the page does not print.
- 8 of the 35 `<wedge>`s are text lines in the source
  ("cresc. _ _ _", "dim. _ _ _", bars 11 and 17; `<useTextLine>` in the `.mscz`);
  MuseScore 2.1 wrote them as graphic hairpins, MuseScore 3 would write
  `<words>` + `<dashes>`. Not fixed in the companion, since that would re-author them.
- 14 rests carry `print-object="no"`: MuseScore's padding of partial voices.
- Held notes are re-voiced across bar lines (bars 30, 104–105),
  so three ties and two slurs start in one voice and stop in another.
- The 1/8 pickup bar after the repeat is numbered plainly as bar 39,
  with no `implicit="yes"`; bars 38 and 129 are 5/8 to complete it.
