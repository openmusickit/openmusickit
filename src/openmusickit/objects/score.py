from dataclasses import dataclass

from openmusickit.objects.omk_object import OmkObject


@dataclass(kw_only=True, slots=True)
class Score(OmkObject):
    """A work, as far as the graph is concerned:
    the metadata a title page carries,
    and a name for one connected component.

    A Score points at the heads of its top-level lines and at its Parts
    with plain CONTAINS edges
    (`OmkGraph.add_line_to_score`, `add_part_to_score`;
    `score_lines`, `score_parts`, `scores_of` and `walk_score` read them back).
    A line need not have a Part (a chord line, a sketch),
    and a Part need not have music yet (an orchestration sketch),
    so both memberships carry information.
    A Score is not a timing origin:
    where its lines fall relative to each other is said by pins and groups, as ever,
    and two lines of one Score with no pin between them have no relative onset.
    The graph as a whole is not a work (`GraphMeta` describes the graph):
    one graph may hold several Scores, or fragments that belong to none.

    Every field is optional; `None` is "not given", not an empty string.

    >>> Score(title="Twinkle, Twinkle, Little Star", lyricist="Jane Taylor")
    Score(title='Twinkle, Twinkle, Little Star', subtitle=None, composer=None, lyricist='Jane Taylor', arranger=None, copyright=None, opus=None, dedication=None)
    >>> Score().title is None
    True
    """

    title: str | None = None
    subtitle: str | None = None
    composer: str | None = None
    lyricist: str | None = None
    arranger: str | None = None
    copyright: str | None = None
    opus: str | None = None
    dedication: str | None = None
