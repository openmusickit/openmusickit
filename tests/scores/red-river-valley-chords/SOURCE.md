# Red River Valley (chords-over-lyrics chart)

- **Song:** "Red River Valley", traditional North American folk song
  (lyrics printed 1887 in *The Weekly Wisconsin*;
  sheet music 1896 as "In the Bright Mohawk Valley");
  public domain.
- **Chart:** from the GuitarMan project by Dave Robins (2026),
  a guitar-karaoke firmware whose built-in songs are plain text files.
- **Test category:** lyrics-and-chords-only chart,
  plain monospace "chords above lyrics" text.

## Sources

- Repository: <https://github.com/freewili/guitarman>
  (pinned commit `ebcda5168a9dc876a4c37c19be2da4ae220c8683`)
- Chart file:
  <https://raw.githubusercontent.com/freewili/guitarman/ebcda5168a9dc876a4c37c19be2da4ae220c8683/songs/red_river_valley.txt>
- License file:
  <https://raw.githubusercontent.com/freewili/guitarman/ebcda5168a9dc876a4c37c19be2da4ae220c8683/LICENSE>
- Format description (repository docs):
  <https://github.com/freewili/guitarman/blob/master/docs/song-and-playlist-format.md>

## License

MIT License, Copyright (c) 2026 Dave Robins,
stated in the repository's `LICENSE` file and README.
The MIT notice requires the copyright and permission notice to accompany copies,
so it is kept here verbatim as `LICENSE-guitarman.txt`.
<https://opensource.org/license/mit>

## Files

`red_river_valley.txt` (chart, as distributed), `LICENSE-guitarman.txt`.

## Notable features for testing

`key: value` header (title, artist, key, scroll) before the first section;
bracketed section labels `[Verse 1]`, `[Chorus]`, `[Verse 2]`;
two verses and a chorus; the final `[Chorus]` has an empty body,
which in this format means "repeat the chorus defined earlier".
Chords G, C, G7, D7 aligned over syllables by column position.
