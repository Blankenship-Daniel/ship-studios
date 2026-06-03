#!/usr/bin/env python3
"""Smoke test: does Gemini Batch mode accept AUDIO at all?

A batch path (submit many critique jobs at the discounted async tier instead of
N live calls) is on the backlog, but the WHOLE optimization is GATED on one
unknown: **the Gemini Batch API is documented for text/image — it is not clearly
documented to accept audio parts.** Run this BEFORE anyone builds a batch path.
If batch mode rejects audio, the batch optimization is dead and nobody should
spend a day wiring it.

What it does (the minimal possible probe):
  1. Uploads ONE short audio file via the Files API (``client.files.upload``)
     and waits for it to become ACTIVE.
  2. Writes a one-line JSONL batch input: a single request whose ``contents``
     reference the uploaded file by ``file_uri`` (a ``Part.from_uri`` with the
     audio mime type) plus a tiny ``response_schema`` (one boolean + one string)
     so the round-trip is unmistakable.
  3. Uploads that JSONL and submits ONE ``client.batches.create`` job.
  4. Polls ``client.batches.get`` until the job leaves a running state, then
     prints whether Gemini ACCEPTED audio in batch mode (job succeeded with
     output) or REJECTED it (failed / errored), with the raw state for the log.

It does not parse or use the model's answer — the only question is *did batch
mode accept an audio part*. It writes one temp JSONL (cleaned up) and never
touches your project audio.

REQUIRES: ``GEMINI_API_KEY`` (the SDK also reads ``GOOGLE_API_KEY``) and the
``google-genai`` SDK (``pip install google-genai`` / ``uv sync``). Makes real,
billed Gemini calls. This is a one-off probe, not a pipeline step.

Usage:
    export GEMINI_API_KEY=...
    python scripts/gemini_batch_audio_smoke.py path/to/short_clip.wav
    python scripts/gemini_batch_audio_smoke.py clip.wav --model gemini-2.5-flash
    python scripts/gemini_batch_audio_smoke.py clip.wav --timeout 1800

Keep the clip SHORT (a few seconds) — batch turnaround can be minutes to the
documented 24 h SLA; this script polls up to ``--timeout`` seconds then reports
the last-seen state without failing the gate either way.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

#: Batch job states that mean "still working" — keep polling while in this set.
_RUNNING_STATES = {
    "JOB_STATE_PENDING",
    "JOB_STATE_RUNNING",
    "JOB_STATE_QUEUED",
    "JOB_STATE_UNSPECIFIED",
}
#: File states that mean the upload is still being processed.
_FILE_PENDING_STATES = {"PROCESSING", "STATE_UNSPECIFIED"}


def _state_name(obj: Any) -> str:
    """Best-effort string of a genai enum/state field (handles enum or str)."""
    state = getattr(obj, "state", None)
    if state is None:
        return "UNKNOWN"
    return getattr(state, "name", None) or str(state)


def _audio_mime(path: Path) -> str:
    """Guess an audio mime type for the Files API / Part.from_uri."""
    guessed, _ = mimetypes.guess_type(str(path))
    if guessed and guessed.startswith("audio/"):
        return guessed
    # Fall back by extension for formats mimetypes may miss.
    ext = path.suffix.lower().lstrip(".")
    return {
        "wav": "audio/wav", "aif": "audio/aiff", "aiff": "audio/aiff",
        "mp3": "audio/mpeg", "flac": "audio/flac", "ogg": "audio/ogg",
        "aac": "audio/aac", "m4a": "audio/mp4",
    }.get(ext, "audio/wav")


def _wait_file_active(client: Any, file_obj: Any, timeout: float) -> Any:
    """Poll until an uploaded file is ACTIVE (or raise on FAILED / timeout)."""
    deadline = time.monotonic() + timeout
    while True:
        state = _state_name(file_obj)
        if state == "ACTIVE":
            return file_obj
        if state == "FAILED":
            raise RuntimeError(f"Files API marked the upload FAILED: {file_obj!r}")
        if state not in _FILE_PENDING_STATES:
            # Unknown but not pending — assume usable and let batch be the judge.
            return file_obj
        if time.monotonic() > deadline:
            raise TimeoutError(f"file did not become ACTIVE within {timeout:g}s "
                               f"(last state: {state})")
        time.sleep(3)
        file_obj = client.files.get(name=file_obj.name)


def run(audio: str, model: str, timeout: float) -> int:
    from google import genai
    from google.genai import types

    audio_path = Path(audio).expanduser()
    if not audio_path.is_file():
        print(f"error: audio file not found: {audio_path}", file=sys.stderr)
        return 2
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        print("error: GEMINI_API_KEY (or GOOGLE_API_KEY) is not set.",
              file=sys.stderr)
        return 2

    client = genai.Client()
    mime = _audio_mime(audio_path)

    # 1. Upload the audio via the Files API and wait for ACTIVE.
    print(f">>> uploading {audio_path.name} ({mime}) via the Files API …",
          file=sys.stderr)
    uploaded = client.files.upload(file=str(audio_path))
    uploaded = _wait_file_active(client, uploaded, timeout=min(timeout, 120))
    print(f"    file_uri = {uploaded.uri}", file=sys.stderr)

    # A tiny schema so a successful round-trip is unambiguous and cheap.
    response_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "is_audio": {"type": "boolean"},
            "one_word": {"type": "string"},
        },
        "required": ["is_audio", "one_word"],
    }

    # 2. One JSONL line: a single request referencing the file by URI.
    request_line = {
        "key": "audio-batch-smoke-0",
        "request": {
            "contents": [
                {
                    "parts": [
                        {"file_data": {"file_uri": uploaded.uri,
                                       "mime_type": mime}},
                        {"text": "Is this audio? Reply with the schema; "
                                 "one_word = any single word you hear or 'music'."},
                    ]
                }
            ],
            "generation_config": {
                "response_mime_type": "application/json",
                "response_schema": response_schema,
            },
        },
    }

    tmp_dir = Path(tempfile.mkdtemp(prefix="gemini_batch_audio_smoke_"))
    jsonl_path = tmp_dir / "batch_input.jsonl"
    jsonl_path.write_text(json.dumps(request_line) + "\n")

    job = None
    try:
        # 3. Upload the JSONL and submit ONE batch job.
        print(">>> uploading batch JSONL + submitting client.batches.create …",
              file=sys.stderr)
        batch_input_file = client.files.upload(
            file=str(jsonl_path),
            config=types.UploadFileConfig(
                display_name="audio-batch-smoke", mime_type="application/jsonl"
            ),
        )
        job = client.batches.create(
            model=model,
            src=batch_input_file.name,
            config=types.CreateBatchJobConfig(display_name="audio-batch-smoke"),
        )
        print(f"    submitted job: {job.name}  (state {_state_name(job)})",
              file=sys.stderr)

        # 4. Poll until it leaves a running state (or we hit --timeout).
        deadline = time.monotonic() + timeout
        while _state_name(job) in _RUNNING_STATES:
            if time.monotonic() > deadline:
                print(f"\nINCONCLUSIVE: job still {_state_name(job)} after "
                      f"{timeout:g}s. Re-run `client.batches.get(name=...)` later "
                      f"for the verdict. Job: {job.name}")
                return 3
            time.sleep(10)
            job = client.batches.get(name=job.name)
            print(f"    … {_state_name(job)}", file=sys.stderr)

    finally:
        # Tidy the temp JSONL; leave the uploaded files for the 48h TTL.
        try:
            jsonl_path.unlink(missing_ok=True)
            tmp_dir.rmdir()
        except OSError:
            pass

    final = _state_name(job)
    print("\n=== BATCH AUDIO SMOKE RESULT ===")
    print(f"model      : {model}")
    print(f"final state: {final}")
    error = getattr(job, "error", None)
    if error is not None:
        print(f"error      : {error}")

    if final == "JOB_STATE_SUCCEEDED":
        print("\nVERDICT: Gemini Batch mode ACCEPTED audio (job succeeded). "
              "A batch critique path is worth building.")
        dest = getattr(job, "dest", None)
        if dest is not None:
            print(f"output     : {dest}")
        return 0

    print("\nVERDICT: Gemini Batch mode did NOT succeed on audio (state "
          f"{final}). If the error indicates audio/file parts are unsupported, "
          "the batch optimization is DEAD — do not build it. Inspect the error "
          "above to distinguish 'audio rejected' from a transient failure.")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Probe whether Gemini Batch mode accepts audio (gates the "
                    "batch backlog item). Makes real, billed calls.",
    )
    parser.add_argument("audio", help="path to a SHORT audio clip to probe with")
    parser.add_argument(
        "--model", "-m", default="gemini-2.5-flash",
        help="model to run the batch job under (default: gemini-2.5-flash)",
    )
    parser.add_argument(
        "--timeout", "-t", type=float, default=1800.0,
        help="max seconds to poll before reporting INCONCLUSIVE (default: 1800)",
    )
    args = parser.parse_args(argv)
    try:
        return run(args.audio, args.model, args.timeout)
    except ImportError as exc:  # SDK not installed
        print(f"error: google-genai SDK not available ({exc}). "
              "Install with `pip install google-genai` / `uv sync`.",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
