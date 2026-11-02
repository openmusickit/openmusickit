"""The scoring symbol tables as values: no two distinct symbols compare equal.

Symbols are values, so code that looks for one (`mark == scoring.tie`,
`shape == scoring.start_repeat`) compares by equality, and a copy of a
symbol (from `copy.deepcopy`, `materialize`, or a file read back) is still
that symbol. That is only sound while each table's symbols are pairwise
unequal; a new entry equal to an existing one would make the two
indistinguishable.
"""

from itertools import combinations

import pytest

from tests.domains import distinct


@pytest.mark.parametrize(
    "table", ["mark_symbols", "bar_line_symbols", "clef_symbols", "tempo_term_symbols"]
)
def test_no_two_symbols_in_a_table_are_equal(table, request):
    symbols = distinct(request.getfixturevalue(table))
    equal_pairs = [
        (first, second)
        for (first, value), (second, other) in combinations(symbols.items(), 2)
        if value == other
    ]
    assert equal_pairs == []
