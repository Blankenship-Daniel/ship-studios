"""Deliverable tag/format verification — the QC piece no MCP tool covers.

The stemmy/gemini tools check loudness, true-peak, clipping and streaming targets;
nothing verifies that exported deliverables actually carry their metadata. This
catches the silent failures hit in practice: ``export-deliverables tag=true``
dropping the RIFF INFO ``LIST`` chunk, and missing ``.tags.json`` sidecars. Parse
chunk headers only (cheap, no full read) and confirm a metadata chunk + sidecar.

Both deliverable containers are handled: WAV (``RIFF``, little-endian; metadata in
the ``LIST`` chunk) and AIFF (``FORM``, big-endian; metadata in the text chunks
``NAME``/``AUTH``/``ANNO``/``(c)``/``COMT``/``ID3``) — AIFF is a first-class
drum_prep output, so a chunk parser that only understood RIFF reported every AIFF
as untagged.
"""
from __future__ import annotations

import json
import os
import struct

import soundfile as sf

from drum_prep import io

#: AIFF text/metadata chunk IDs (after trailing-space strip) that count as tags.
_AIFF_TAG_CHUNKS = frozenset({"NAME", "AUTH", "ANNO", "(c)", "COMT", "ID3"})


def container_chunks(path: str) -> tuple[str | None, list[str]]:
    """Return ``(container, chunk_ids)`` reading headers only (seeks past data).

    ``container`` is ``"WAVE"`` for a RIFF/WAVE file, ``"AIFF"``/``"AIFC"`` for a
    FORM/AIFF file, or ``None`` if neither magic matches. Chunk sizes are
    little-endian for RIFF and big-endian for AIFF.
    """
    ids: list[str] = []
    with open(path, "rb") as fh:
        fh.seek(0, os.SEEK_END)
        file_size = fh.tell()
        fh.seek(0)
        magic = fh.read(4)
        if magic == b"RIFF":
            endian, container = "<I", fh.read(8)[4:8].decode("latin1")
        elif magic == b"FORM":
            endian, container = ">I", fh.read(8)[4:8].decode("latin1")
        else:
            return None, ids
        while True:
            head = fh.read(8)
            if len(head) < 8:
                break
            # Chunk IDs are 4 printable ASCII chars (0x20-0x7E) in both specs. A
            # byte outside that range means we've lost chunk alignment (corruption
            # or a misread size) — stop rather than mis-decode garbage as a tag and
            # silently report the file "untagged".
            if any(b < 0x20 or b > 0x7E for b in head[:4]):
                break
            cid = head[:4].decode("ascii").strip()
            size = struct.unpack(endian, head[4:8])[0]
            # Don't trust the declared size past EOF: a truncated/corrupt header
            # whose body isn't actually present must NOT count as a tag (this is
            # the QC gate). Check overflow BEFORE recording the id, else a file
            # missing its metadata payload reports tagged=True.
            if fh.tell() + size > file_size:
                break
            ids.append(cid)
            fh.seek(size + (size & 1), 1)  # chunks are word-aligned in both
    return container, ids


def riff_chunks(path: str) -> list[str]:
    """Chunk IDs of a RIFF/WAVE file (back-compat; [] for non-RIFF)."""
    container, ids = container_chunks(path)
    return ids if container == "WAVE" else []


def _has_metadata_chunk(container: str | None, ids: list[str]) -> bool:
    """Whether the parsed chunks carry an embedded-metadata chunk for the format."""
    if container == "WAVE":
        return "LIST" in ids
    if container in ("AIFF", "AIFC"):
        return any(cid in _AIFF_TAG_CHUNKS for cid in ids)
    return False  # FLAC/unknown: rely on the sidecar


def verify_tags(path: str) -> dict:
    """Tag/format status of one deliverable.

    Handles WAV and AIFF embedded metadata; for any other container metadata
    detection falls back to the sidecar. A sidecar that exists but fails to parse
    is treated as NOT tagged (and flagged ``sidecar_corrupt``) — this is the QC
    gate, so a corrupt ``.tags.json`` must not pass as "tagged" just by existing.
    """
    container, ids = container_chunks(path)
    sidecar = path + ".tags.json"
    has_sidecar = os.path.exists(sidecar)
    data: dict | None = None
    sidecar_corrupt = False
    if has_sidecar:
        try:
            with open(sidecar) as fh:
                data = json.load(fh)
        except Exception:
            data = {}
            sidecar_corrupt = True
    info = sf.info(path)
    has_metadata = _has_metadata_chunk(container, ids)
    sidecar_ok = has_sidecar and not sidecar_corrupt and bool(data)
    return {"file": os.path.basename(path),
            # has_list_chunk kept for back-compat (WAV LIST); has_metadata_chunk
            # is the container-aware flag that actually drives `tagged`.
            "has_list_chunk": container == "WAVE" and "LIST" in ids,
            "has_metadata_chunk": has_metadata,
            "has_sidecar": has_sidecar, "sidecar_corrupt": sidecar_corrupt,
            "tagged": has_metadata or sidecar_ok,
            "sidecar": data, "channels": info.channels, "samplerate": info.samplerate,
            "subtype": info.subtype}


def verify_dir(directory: str) -> dict:
    """Verify every audio deliverable (WAV/AIFF/FLAC) in a directory.

    WAV metadata is the RIFF INFO ``LIST`` chunk, AIFF the text chunks; FLAC and
    other containers fall back to the ``.tags.json`` sidecar.
    """
    results = [verify_tags(os.path.join(directory, f)) for f in io.list_audio(directory)]
    untagged = [r["file"] for r in results if not r["tagged"]]
    corrupt = [r["file"] for r in results if r["sidecar_corrupt"]]
    return {"flow": "verify-tags", "dir": directory, "files": len(results),
            "all_tagged": not untagged, "untagged": untagged,
            "corrupt_sidecars": corrupt, "results": results}
