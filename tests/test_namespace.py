"""The convenience namespaces: every package's `__all__` resolves,
re-exports come from inside the package that re-exports them,
the top level stays free of any musical system,
and `wsmn.symbols` merges its sources without a clash.
"""

import importlib
import inspect
import pkgutil
from types import ModuleType

import pytest

import openmusickit
from openmusickit.systems.wsmn import symbols
from openmusickit.systems.wsmn.scoring import symbols as scoring_symbols
from openmusickit.systems.wsmn.temporal import symbols as temporal_symbols
from openmusickit.systems.wsmn.tonal import symbols as tonal_symbols

PACKAGES = [openmusickit] + [
    importlib.import_module(info.name)
    for info in pkgutil.walk_packages(openmusickit.__path__, "openmusickit.")
    if info.ispkg
]

SYMBOL_SOURCES = [tonal_symbols, temporal_symbols, scoring_symbols]


def _exported(package: ModuleType) -> list[tuple[str, object]]:
    """The names a package re-exports, other than its own submodules."""
    return [
        (name, getattr(package, name))
        for name in package.__all__
        if not isinstance(getattr(package, name), ModuleType)
    ]


def _public(module: ModuleType) -> dict[str, object]:
    return {
        name: value
        for name, value in vars(module).items()
        if not name.startswith("_") and not isinstance(value, ModuleType)
    }


@pytest.mark.parametrize("package", PACKAGES, ids=lambda p: p.__name__)
def test_every_name_in_all_resolves(package):
    for name in package.__all__:
        assert hasattr(package, name), f"{package.__name__}.{name}"


@pytest.mark.parametrize("package", PACKAGES, ids=lambda p: p.__name__)
def test_a_reexport_is_the_object_its_own_module_defines(package):
    for name, value in _exported(package):
        if not (inspect.isclass(value) or inspect.isfunction(value)):
            continue  # a constant does not know its module
        assert value.__module__.startswith(package.__name__ + "."), f"{package.__name__}.{name}"
        defining = importlib.import_module(value.__module__)
        assert getattr(defining, value.__name__) is value


def test_the_top_level_holds_nothing_from_a_musical_system():
    for name, value in _exported(openmusickit):
        assert inspect.isclass(value) or inspect.isfunction(value), name
        assert not value.__module__.startswith("openmusickit.systems."), name


def test_wsmn_symbols_holds_every_source_name():
    merged = _public(symbols)
    for source in SYMBOL_SOURCES:
        for name, value in _public(source).items():
            assert merged[name] is value, f"{source.__name__}.{name}"


def test_wsmn_symbol_sources_do_not_clash():
    seen: dict[str, object] = {}
    for source in SYMBOL_SOURCES:
        for name, value in _public(source).items():
            assert seen.setdefault(name, value) is value, f"{source.__name__}.{name}"
