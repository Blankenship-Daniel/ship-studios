"""verify-tags: detect missing RIFF INFO LIST chunk / sidecar on deliverables."""
from __future__ import annotations

import json
import struct

import pytest

np = pytest.importorskip("numpy")
sf = pytest.importorskip("soundfile")

from drum_prep.qc import riff_chunks, verify_dir, verify_tags  # noqa: E402

SR = 48000


def _plain_wav(p) -> None:
    sf.write(str(p), np.zeros((SR, 2), dtype=np.float32), SR, subtype="PCM_24")


def _append_list_chunk(p) -> None:
    raw = open(p, "rb").read()
    payload = b"INFO" + b"ICMT" + struct.pack("<I", 4) + b"hi\x00\x00"
    chunk = b"LIST" + struct.pack("<I", len(payload)) + payload
    new = raw + chunk
    new = new[:4] + struct.pack("<I", len(new) - 8) + new[8:]  # fix RIFF size
    open(p, "wb").write(new)


def test_untagged_detected(tmp_path) -> None:
    p = tmp_path / "loop.wav"
    _plain_wav(p)
    r = verify_tags(str(p))
    assert r["has_list_chunk"] is False and r["has_sidecar"] is False and r["tagged"] is False
    assert "LIST" not in riff_chunks(str(p))


def test_list_and_sidecar_detected(tmp_path) -> None:
    p = tmp_path / "loop.wav"
    _plain_wav(p)
    _append_list_chunk(p)
    assert "LIST" in riff_chunks(str(p))
    assert verify_tags(str(p))["has_list_chunk"] is True

    json.dump({"bpm": 120}, open(str(p) + ".tags.json", "w"))
    r = verify_tags(str(p))
    assert r["has_sidecar"] is True and r["sidecar"]["bpm"] == 120


def test_verify_dir_flags_untagged(tmp_path) -> None:
    _plain_wav(tmp_path / "a.wav")
    _plain_wav(tmp_path / "b.wav")
    res = verify_dir(str(tmp_path))
    assert res["files"] == 2 and res["all_tagged"] is False
    assert set(res["untagged"]) == {"a.wav", "b.wav"}
