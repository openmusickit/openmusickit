"""Opening and packing a MusicXML file: plain XML or the compressed `.mxl` zip.

An `.mxl` is a zip whose `META-INF/container.xml` names the score file
inside it (`<rootfile full-path="...">`). The file's suffix is not trusted;
a zip is recognised by its magic bytes, so a `.xml` that is really an `.mxl`
still opens.
"""

from __future__ import annotations

import io
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import IO

from openmusickit.errors import MusicXmlError

MIMETYPE = "application/vnd.recordare.musicxml"
MEDIA_TYPE = "application/vnd.recordare.musicxml+xml"


def load(source: str | Path | IO[bytes]) -> ET.Element:
    """The `<score-partwise>` root of `source`, a path or a binary stream.

    Raises
    ------
    MusicXmlError
        if the file is not XML, has no score in its container, or is not a
        partwise score (`<score-timewise>` is not read).
    """
    data = _bytes(source)
    if data[:4] == b"PK\x03\x04":
        data = _unzip(data)
    try:
        root = ET.fromstring(data)
    except ET.ParseError as error:
        raise MusicXmlError(f"Not well-formed XML: {error}") from error
    if root.tag == "score-timewise":
        raise MusicXmlError(
            "This is a <score-timewise> file; only <score-partwise> is read. "
            "Notation programs export partwise; convert with the timewise-to-partwise XSLT first."
        )
    if root.tag != "score-partwise":
        raise MusicXmlError(f"Not a MusicXML score: the root element is <{root.tag}>.")
    return root


def zipped(document: bytes, name: str = "score.musicxml") -> bytes:
    """`document` packed as an `.mxl` archive: an uncompressed `mimetype`
    first, the container manifest naming `name`, and the score itself.

    >>> archive = zipped(b'<score-partwise version="4.0"><part-list/></score-partwise>')
    >>> load(io.BytesIO(archive)).tag
    'score-partwise'
    """
    manifest = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<container><rootfiles>"
        f'<rootfile full-path="{name}" media-type="{MEDIA_TYPE}"/>'
        "</rootfiles></container>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("mimetype", MIMETYPE, compress_type=zipfile.ZIP_STORED)
        archive.writestr("META-INF/container.xml", manifest, compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr(name, document, compress_type=zipfile.ZIP_DEFLATED)
    return buffer.getvalue()


def _bytes(source: str | Path | IO[bytes]) -> bytes:
    if isinstance(source, (str, Path)):
        return Path(source).read_bytes()
    return source.read()


def _unzip(data: bytes) -> bytes:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        try:
            manifest = ET.fromstring(archive.read("META-INF/container.xml"))
        except KeyError as error:
            raise MusicXmlError("The .mxl archive has no META-INF/container.xml.") from error
        rootfile = manifest.find(".//rootfile")
        if rootfile is None or not rootfile.get("full-path"):
            raise MusicXmlError("The .mxl container names no rootfile.")
        try:
            return archive.read(rootfile.get("full-path"))
        except KeyError as error:
            raise MusicXmlError(
                f"The .mxl container names {rootfile.get('full-path')!r}, which is not in the archive."
            ) from error
