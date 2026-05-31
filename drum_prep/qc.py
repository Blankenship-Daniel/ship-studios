"""Deliverable tag/format verification — the QC piece no MCP tool covers.

The stemmy/gemini tools check loudness, true-peak, clipping and streaming targets;
nothing verifies that exported deliverables actually carry their metadata. This
catches the silent failures hit in practice: ``export-deliverables tag=true``
dropping the RIFF INFO ``LIST`` chunk, and missing ``.tags.json`` sidecars. Parse
RIFF chunk headers only (cheap, no full read) and confirm the LIST chunk + sidecar.
"""
from __future__ import annotations

import json
import os
import struct

import soundfile as sf

from drum_prep import io


def riff_chunks(path: str) -> list[str]:
    """Chunk IDs of a RIFF/WAVE file, reading headers only (seeks past data)."""
    ids: list[str] = []
    with open(path, "rb") as fh:
        if fh.read(4) != b"RIFF":
            return ids
        fh.read(8)  # riff size + 'WAVE'
        while True:
            head = fh.read(8)
            if len(head) < 8:
                break
            cid = head[:4].decode("latin1").strip()
            size = struct.unpack("<I", head[4:8])[0]
            ids.append(cid)
            fh.seek(size + (size & 1), 1)
    return ids


def verify_tags(path: str) -> dict:
    """Tag/format status of one deliverable WAV."""
    ids = riff_chunks(path)
    sidecar = path + ".tags.json"
    data = None
    if os.path.exists(sidecar):
        try:
            with open(sidecar) as fh:
                data = json.load(fh)
        except Exception:
            data = {}
    info = sf.info(path)
    has_list = "LIST" in ids
    has_sidecar = os.path.exists(sidecar)
    return {"file": os.path.basename(path), "has_list_chunk": has_list,
            "has_sidecar": has_sidecar, "tagged": has_list or has_sidecar,
            "sidecar": data, "channels": info.channels, "samplerate": info.samplerate,
            "subtype": info.subtype}


def verify_dir(directory: str) -> dict:
    """Verify every WAV in a deliverables directory."""
    results = [verify_tags(os.path.join(directory, f)) for f in io.list_audio(directory)]
    untagged = [r["file"] for r in results if not r["tagged"]]
    return {"flow": "verify-tags", "dir": directory, "files": len(results),
            "all_tagged": not untagged, "untagged": untagged, "results": results}
