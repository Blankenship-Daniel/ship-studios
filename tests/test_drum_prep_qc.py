"""verify-tags: detect missing RIFF INFO LIST chunk / sidecar on deliverables."""
from __future__ import annotations

import json
import struct

import pytest

np = pytest.importorskip("numpy")
sf = pytest.importorskip("soundfile")

from drum_prep.qc import container_chunks, riff_chunks, verify_dir, verify_tags  # noqa: E402

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


def _append_aiff_anno(p) -> None:
    """Append an ANNO (annotation) metadata chunk to a FORM/AIFF file."""
    raw = open(p, "rb").read()
    payload = b"made by drum-prep\x00"
    chunk = b"ANNO" + struct.pack(">I", len(payload)) + payload
    if len(payload) & 1:
        chunk += b"\x00"
    new = raw + chunk
    new = new[:4] + struct.pack(">I", len(new) - 8) + new[8:]  # fix FORM size (BE)
    open(p, "wb").write(new)


def test_aiff_embedded_metadata_detected(tmp_path) -> None:
    # AIFF is a first-class drum_prep output; an AIFF carrying an ANNO chunk must
    # NOT be reported untagged just because it isn't a RIFF/LIST container.
    p = tmp_path / "kit.aiff"
    sf.write(str(p), np.zeros((SR, 2), dtype=np.float32), SR, subtype="PCM_24", format="AIFF")
    r = verify_tags(str(p))
    assert r["has_list_chunk"] is False  # not a WAV
    assert r["tagged"] is False          # no metadata yet
    _append_aiff_anno(p)
    r = verify_tags(str(p))
    assert r["has_metadata_chunk"] is True
    assert r["tagged"] is True


def test_aiff_tagged_via_sidecar(tmp_path) -> None:
    p = tmp_path / "kit.aif"
    sf.write(str(p), np.zeros((SR, 2), dtype=np.float32), SR, subtype="PCM_24", format="AIFF")
    json.dump({"bpm": 90}, open(str(p) + ".tags.json", "w"))
    r = verify_tags(str(p))
    assert r["has_metadata_chunk"] is False and r["tagged"] is True


def test_truncated_chunk_header_not_counted_as_tag(tmp_path) -> None:
    # A metadata chunk header whose declared body runs PAST EOF (export aborted
    # mid-write / corrupt size) must NOT count as a tag — the payload isn't there.
    # This is the QC gate, so it must not report tagged=True for a missing body.
    p = tmp_path / "truncated.wav"
    _plain_wav(p)
    raw = open(p, "rb").read()
    bogus = b"LIST" + struct.pack("<I", 9999)   # claims 9999 bytes; none follow
    with open(p, "wb") as fh:
        fh.write(raw + bogus)
    container, ids = container_chunks(str(p))
    assert container == "WAVE"
    assert "LIST" not in ids                      # past-EOF body -> NOT recorded
    r = verify_tags(str(p))
    assert r["has_metadata_chunk"] is False and r["tagged"] is False


def test_non_ascii_chunk_id_stops_parsing(tmp_path) -> None:
    # A chunk id with bytes outside printable ASCII signals lost alignment; the
    # parser must stop rather than mis-decode it as a (non-matching) tag and crawl
    # into garbage. A real-looking LIST placed AFTER the bogus chunk must not be
    # reached.
    p = tmp_path / "corrupt.wav"
    _plain_wav(p)
    raw = open(p, "rb").read()
    bogus = b"\xff\xff\xffX" + struct.pack("<I", 0)        # non-ASCII chunk id
    listc = b"LIST" + struct.pack("<I", 4) + b"INFO"       # would otherwise tag it
    with open(p, "wb") as fh:
        fh.write(raw + bogus + listc)
    container, ids = container_chunks(str(p))
    assert container == "WAVE"
    assert "LIST" not in ids               # parsing stopped at the bogus chunk
    assert verify_tags(str(p))["has_metadata_chunk"] is False
