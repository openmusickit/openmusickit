"""Vocabularies (format specification §6–7), and the encoder and decoder that
write the types of a set of vocabularies as JSON data and read them back.

A vocabulary is a published, versioned set of names.
Here it is a `Vocabulary`: its URI, preferred prefix and version,
one `TypeCodec` per type it defines,
and the identifiers of its tonal and temporal systems.
The codecs are written by hand, one small pair of functions per type,
and never derived from a class's Python fields:
the specification is the source of truth, and a field renamed in Python
must not silently rename it in every document (`_plans/json-serialization.md` §5.3).

An `Encoder` and a `Decoder` each serve one document.
The encoder records which vocabularies the document uses;
the decoder resolves the document's own prefixes.
Both check the specification's domains, so a writer refuses what a reader would reject.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from openmusickit.errors import OmkJsonError, UnexportableError
from openmusickit.io.omk_json import canonical
from openmusickit.values.time.duration import TemporalSystem
from openmusickit.values.tone.tone import TonalSystem

Role = Literal["node", "edge", "value"]
_A = {"node": "a node", "edge": "an edge", "value": "a value"}

_VERSION = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
_PREFIX = re.compile(r"[a-z][a-z0-9-]*")
_TEMPLATE_TOKEN = re.compile(r"\{\{|\}\}|\{root(?::([a-z_]+))?\}|[^{}]")


@dataclass(frozen=True, slots=True)
class TypeCodec:
    """How one type of a vocabulary is written and read.

    `encode` returns the type's fields (without `@type`), and `decode`
    builds the object from them; both are given the encoder or decoder
    so that they can write and read the values the fields hold.
    `fields` names exactly the keys the specification gives the type.
    `kinds` are the kinds a value of this type may stand for (§7.3);
    `display_forms`, for a tone, are the forms a name template may name.
    """

    name: str
    cls: type
    role: Role
    fields: tuple[str, ...]
    encode: Callable[[Any, Encoder], dict[str, Any]]
    decode: Callable[[dict[str, Any], Decoder], Any]
    kinds: frozenset[str] = frozenset()
    display_forms: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True, eq=False)
class Vocabulary:
    """A published vocabulary: its identity, its types, and its systems.

    System identifiers are given unqualified (`"metrical"`);
    in a document they carry the vocabulary's prefix (`"wsmn:metrical"`),
    except for the `omk` vocabulary, whose names are written bare.
    """

    prefix: str
    uri: str
    version: str
    codecs: tuple[TypeCodec, ...]
    temporal_systems: Mapping[str, TemporalSystem] = field(default_factory=dict)
    tonal_systems: Mapping[str, TonalSystem] = field(default_factory=dict)

    def accepts(self, version: str) -> bool:
        """Whether a document requiring `version` of this vocabulary can be read (§6.3):
        the same major version and no later minor one, or, before 1.0, exactly this version.

        >>> from openmusickit.io.omk_json.core import CORE
        >>> CORE.version, CORE.accepts("0.1"), CORE.accepts("0.0"), CORE.accepts("1.0")
        ('0.1', True, False, False)
        """
        wanted, have = _VERSION.fullmatch(version), _VERSION.fullmatch(self.version)
        if wanted is None or have is None:
            return False
        wanted_major, wanted_minor = int(wanted[1]), int(wanted[2])
        major, minor = int(have[1]), int(have[2])
        if major == 0:
            return (wanted_major, wanted_minor) == (major, minor)
        return wanted_major == major and wanted_minor <= minor


class _Lexicon:
    """The vocabularies in use for one document, indexed for lookup."""

    def __init__(self, vocabularies: Iterable[Vocabulary]):
        self.vocabularies = list(vocabularies)
        if not self.vocabularies or self.vocabularies[0].prefix != "omk":
            raise ValueError("The first vocabulary must be the core vocabulary, `omk`.")
        self.by_class: dict[type, tuple[Vocabulary, TypeCodec]] = {}
        self.by_uri: dict[str, Vocabulary] = {}
        for vocabulary in self.vocabularies:
            if vocabulary.uri in self.by_uri:
                raise ValueError(f"The vocabulary {vocabulary.uri} is given twice.")
            self.by_uri[vocabulary.uri] = vocabulary
            for codec in vocabulary.codecs:
                if codec.cls in self.by_class:
                    raise ValueError(f"{codec.cls.__name__} has a codec in two vocabularies.")
                self.by_class[codec.cls] = (vocabulary, codec)


def qualify(vocabulary: Vocabulary, name: str, prefix: str | None = None) -> str:
    """A name as a document writes it (§7.1): bare for `omk`, otherwise `prefix:name`."""
    if vocabulary.prefix == "omk":
        return name
    return f"{prefix or vocabulary.prefix}:{name}"


def check_template(template: str, forms: frozenset[str] | None) -> None:
    """Checks a name template against the grammar of the `omk` vocabulary:
    literal text, `{root}`, `{root:FORM}` with FORM one of `forms`, `{{` and `}}`.
    `forms` is None when the collection has no root, so no placeholder is allowed.

    >>> check_template("{root:ascii}maj7", frozenset({"ascii"}))
    >>> check_template("{root!r}", frozenset({"ascii"}))
    Traceback (most recent call last):
    ...
    ValueError: '{root!r}' is not a name template: only {root}, {root:FORM}, {{ and }} may use braces.

    Raises
    ------
    ValueError
        if the template breaks the grammar, uses `{root}` with no root,
        or names a display form the root does not have.
    """
    position = 0
    while position < len(template):
        match = _TEMPLATE_TOKEN.match(template, position)
        if match is None:
            raise ValueError(
                f"{template!r} is not a name template: "
                "only {root}, {root:FORM}, {{ and }} may use braces."
            )
        token = match.group(0)
        if token.startswith("{root"):
            if forms is None:
                raise ValueError(
                    f"The name template {template!r} uses {{root}}, but there is no root."
                )
            form = match.group(1)
            if form is not None and form not in forms:
                raise ValueError(
                    f"The name template {template!r} names the display form {form!r}; "
                    f"the root's are {sorted(forms)}."
                )
        position = match.end()


class Encoder:
    """Writes the values of one document, and records the vocabularies it uses."""

    def __init__(self, vocabularies: Iterable[Vocabulary]):
        self._lexicon = _Lexicon(vocabularies)
        prefixes = [vocabulary.prefix for vocabulary in self._lexicon.vocabularies]
        if len(set(prefixes)) != len(prefixes):
            raise ValueError(f"Two vocabularies share a preferred prefix: {prefixes}.")
        self.used: set[Vocabulary] = {self._lexicon.vocabularies[0]}

    def codec(self, obj: Any) -> tuple[Vocabulary, TypeCodec]:
        """The vocabulary and codec for `obj`'s exact type.

        Raises
        ------
        UnexportableError
            if no vocabulary defines the type (a subclass of a defined type is not that type).
        """
        found = self._lexicon.by_class.get(type(obj))
        if found is None:
            raise UnexportableError(f"No vocabulary defines {type(obj).__name__}: {obj!r}.")
        return found

    def tagged(self, obj: Any, role: Role) -> dict[str, Any]:
        """`obj` as a tagged object: its fields and its `@type`."""
        vocabulary, codec = self.codec(obj)
        if codec.role != role:
            raise UnexportableError(f"{type(obj).__name__} is {_A[codec.role]}, not {_A[role]}.")
        self.used.add(vocabulary)
        data = codec.encode(obj, self)
        data["@type"] = qualify(vocabulary, codec.name)
        return data

    def value(self, value: Any) -> dict[str, Any]:
        return self.tagged(value, "value")

    def optional(self, value: Any) -> dict[str, Any] | None:
        return None if value is None else self.value(value)

    def array(self, values: Iterable[Any]) -> list[dict[str, Any]]:
        return [self.value(value) for value in values]

    def set(self, values: Iterable[Any]) -> list[dict[str, Any]]:
        """A set's elements, sorted by their canonical text (§9.5)."""
        return sorted(self.array(values), key=canonical.dumps)

    def temporal_system(self, system: TemporalSystem) -> str:
        return self._system(system, "temporal_systems")

    def _system(self, system: Any, table: str) -> str:
        for vocabulary in self._lexicon.vocabularies:
            for name, known in getattr(vocabulary, table).items():
                if known == system:
                    self.used.add(vocabulary)
                    return qualify(vocabulary, name)
        raise UnexportableError(f"No vocabulary declares the system {system!r}.")

    def template(self, template: str | None, root: Any) -> str | None:
        """A name template, checked against the grammar for this root."""
        if template is not None:
            check_template(template, None if root is None else self.codec(root)[1].display_forms)
        return template


class Decoder:
    """Reads the values of one document, resolving its prefixes."""

    def __init__(self, vocabularies: Iterable[Vocabulary], declared: Any):
        """`declared` is the document's `vocabularies` object, unchecked.

        Raises
        ------
        OmkJsonError
            if it is malformed, lacks `omk`, repeats a URI, or requires a
            vocabulary that was not given or a version that is not accepted;
            every missing vocabulary is named.
        """
        self._lexicon = _Lexicon(vocabularies)
        if type(declared) is not dict:
            raise OmkJsonError("`vocabularies` must be an object.")
        self.prefixes: dict[str, Vocabulary] = {}
        missing, seen = [], set()
        for prefix, entry in declared.items():
            if not _PREFIX.fullmatch(prefix):
                raise OmkJsonError(f"{prefix!r} is not a vocabulary prefix.")
            if type(entry) is not dict or set(entry) != {"uri", "version"}:
                raise OmkJsonError(
                    f"The vocabulary {prefix!r} must have exactly `uri` and `version`."
                )
            uri, version = entry["uri"], entry["version"]
            if type(uri) is not str or type(version) is not str:
                raise OmkJsonError(
                    f"The vocabulary {prefix!r} has a `uri` or `version` that is not a string."
                )
            if uri in seen:
                raise OmkJsonError(f"The vocabulary {uri} is listed twice.")
            seen.add(uri)
            vocabulary = self._lexicon.by_uri.get(uri)
            if vocabulary is None or not vocabulary.accepts(version):
                missing.append(f"{uri} version {version}")
            else:
                self.prefixes[prefix] = vocabulary
        if missing:
            raise OmkJsonError(
                f"This document requires vocabularies that were not given: {'; '.join(missing)}."
            )
        core = self._lexicon.vocabularies[0]
        if self.prefixes.get("omk") is not core:
            raise OmkJsonError(
                f"The core vocabulary must be listed under the prefix `omk` ({core.uri})."
            )
        self.codecs: dict[tuple[Vocabulary, str], TypeCodec] = {}
        for vocabulary in self.prefixes.values():
            for codec in vocabulary.codecs:
                self.codecs[vocabulary, codec.name] = codec

    def resolve(self, name: Any) -> tuple[Vocabulary, str]:
        """The vocabulary and local name of a qualified name (§7.1).

        Raises
        ------
        OmkJsonError
            if `name` is not a string, or its prefix is not declared.
        """
        if type(name) is not str:
            raise OmkJsonError(f"{name!r} is not a name.")
        prefix, colon, local = name.partition(":")
        if not colon:
            return self.prefixes["omk"], name
        vocabulary = self.prefixes.get(prefix)
        if vocabulary is None or prefix == "omk":
            raise OmkJsonError(f"{name!r} uses a prefix the document does not declare.")
        return vocabulary, local

    def tagged(self, data: Any, role: Role, kind: str | None = None) -> Any:
        """The object a tagged object stands for, checked against the role and kind
        (`kind` None accepts any type of the role).

        Raises
        ------
        OmkJsonError
            if `data` is not a tagged object of a type of that role and kind,
            if its keys are not exactly the type's fields,
            or if its fields are outside the type's domain.
        """
        if type(data) is not dict or "@type" not in data:
            raise OmkJsonError(
                f"Expected a {kind or role} (an object with `@type`), found {data!r}."
            )
        name = data["@type"]
        vocabulary, local = self.resolve(name)
        codec = self.codecs.get((vocabulary, local))
        if codec is None:
            raise OmkJsonError(f"{name!r} is not a type of {vocabulary.uri}.")
        if codec.role != role:
            raise OmkJsonError(f"{name!r} is {_A[codec.role]}, not {_A[role]}.")
        if kind is not None and kind not in codec.kinds:
            raise OmkJsonError(f"{name!r} is not a {kind}.")
        if role == "value":
            fields = {key: item for key, item in data.items() if key != "@type"}
        else:
            fields = {key: item for key, item in data.items() if not key.startswith("@")}
        if set(fields) != set(codec.fields):
            raise OmkJsonError(
                f"{name!r} has the fields {sorted(fields)}; it must have exactly {sorted(codec.fields)}."
            )
        try:
            return codec.decode(fields, self)
        except OmkJsonError:
            raise
        except (ValueError, TypeError) as error:  # a constructor refusing an out-of-domain value
            raise OmkJsonError(f"{name!r}: {error}") from error

    def value(self, data: Any, kind: str) -> Any:
        return self.tagged(data, "value", kind)

    def optional(self, data: Any, kind: str) -> Any:
        return None if data is None else self.value(data, kind)

    def array(self, data: Any, kind: str) -> list[Any]:
        if type(data) is not list:
            raise OmkJsonError(f"Expected an array of {kind}, found {data!r}.")
        return [self.value(item, kind) for item in data]

    def set(self, data: Any, kind: str) -> set[Any]:
        """A set's elements; two equal elements are refused (§4.7)."""
        values = self.array(data, kind)
        unique = set(values)
        if len(unique) != len(values):
            raise OmkJsonError(f"A set holds the same {kind} twice: {data!r}.")
        return unique

    def temporal_system(self, data: Any) -> TemporalSystem:
        vocabulary, local = self.resolve(data)
        system = vocabulary.temporal_systems.get(local)
        if system is None:
            raise OmkJsonError(f"{data!r} is not a temporal system of {vocabulary.uri}.")
        return system

    def template(self, data: Any, root: Any) -> str | None:
        """A name template (or null), checked against the grammar for this root."""
        if data is None:
            return None
        if type(data) is not str:
            raise OmkJsonError(f"{data!r} is not a name template.")
        forms = None
        if root is not None:
            found = self._lexicon.by_class.get(type(root))
            forms = found[1].display_forms if found else frozenset()
        try:
            check_template(data, forms)
        except ValueError as error:
            raise OmkJsonError(str(error)) from error
        return data
