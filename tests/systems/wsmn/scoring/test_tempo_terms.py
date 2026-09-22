"""The ready-made tempo terms in `scoring.symbols`: distinct words, each
described, whose aliases never double as names."""


def test_tempo_term_table_invariants(tempo_term_symbols):
    """Names are unique, stripped and non-empty; every term has a
    description; aliases are unique across the table and never collide
    with a name."""
    names = [term.name for term in tempo_term_symbols.values()]
    assert len(set(names)) == len(names)
    aliases = [alias for term in tempo_term_symbols.values() for alias in term.aliases]
    assert len(set(aliases)) == len(aliases)
    assert not set(aliases) & set(names)
    for name, term in tempo_term_symbols.items():
        assert term.name.strip() == term.name and term.name, name
        assert term.description, name
