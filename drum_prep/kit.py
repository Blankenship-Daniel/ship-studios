"""Kit model: map drum-mic files to roles, overlay an optional manifest, and
expose the topology the flows consume.

Resolution order: filename auto-detect (:mod:`drum_prep.roles`) -> overlay
``kit.json`` (manifest wins, additive) -> validate. In ``strict`` mode an
unresolved kit fails loud with an actionable message; ``strict=False`` downgrades
problems to warnings and aligns unknowns broadband to the overheads.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from drum_prep.roles import Role, _norm, detect_role

AUDIO_EXTS = (".wav", ".aif", ".aiff", ".flac")
_KICK_ANCHOR_ROLES = (Role.KICK_IN, Role.KICK_OUT, Role.KICK_SUB)
_OH_ROLES = (Role.OVERHEAD, Role.OVERHEAD_L, Role.OVERHEAD_R)
_SINGLETON_ROLES = (Role.OVERHEAD, Role.SNARE_TOP, Role.SNARE_BOTTOM,
                    Role.KICK_IN, Role.KICK_BEATER)


class KitError(Exception):
    """Raised when a kit cannot be resolved unambiguously (strict mode)."""


@dataclass
class KitStem:
    name: str                          # basename, e.g. "kick in.aif"
    role: Role
    label: str | None = None           # human tag, e.g. "floor" for a tom
    partner: str | None = None         # basename of the anchor this aligns to
    lowpass_hz: float | None = None    # per-mic LP for the OH correlation (kick)
    ambience: bool = False             # room: polarity-only, keep timing
    polarity_lock: int | None = None   # force +1/-1, skip polarity auto-detect
    confidence: float = 1.0            # detection confidence (manifest = 1.0)


@dataclass
class Kit:
    src_dir: str
    stems: list[KitStem]
    overhead_mode: str = "stereo"      # "stereo" (pre-merged) or "lr_pair"
    sr: int | None = None
    reference: str | None = None       # optional reference path from manifest
    warnings: list[str] = field(default_factory=list)

    def by_name(self, name: str | None) -> KitStem | None:
        return next((s for s in self.stems if s.name == name), None) if name else None

    def by_role(self, role: Role) -> list[KitStem]:
        return [s for s in self.stems if s.role == role]

    def path(self, stem: KitStem | str) -> str:
        name = stem.name if isinstance(stem, KitStem) else stem
        return os.path.join(self.src_dir, name)

    def to_dict(self) -> dict:
        return {
            "version": 1,
            "src_dir": ".",
            "overhead_mode": self.overhead_mode,
            "reference": self.reference,
            "stems": [
                {k: v for k, v in {
                    "file": s.name, "role": s.role.value, "label": s.label,
                    "partner": s.partner, "lowpass_hz": s.lowpass_hz,
                    "ambience": s.ambience or None, "polarity_lock": s.polarity_lock,
                    "confidence": round(s.confidence, 2),
                }.items() if v is not None}
                for s in self.stems
            ],
        }


# --------------------------------------------------------------------------- #
# detection + resolution
# --------------------------------------------------------------------------- #
def _list_audio(src_dir: str) -> list[str]:
    return sorted(
        f for f in os.listdir(src_dir)
        if not f.startswith(".") and os.path.splitext(f)[1].lower() in AUDIO_EXTS
        and os.path.isfile(os.path.join(src_dir, f))
    )


def _try_samplerate(src_dir: str, stems: list[KitStem]) -> int | None:
    """Best-effort sample rate from the first readable stem (None if none read)."""
    from drum_prep import io

    for s in stems:
        try:
            return io.info(os.path.join(src_dir, s.name))[1]
        except Exception:
            continue  # try the next stem rather than giving up on the first failure
    return None


def _wire_partners(stems: list[KitStem]) -> None:
    """Fill partner anchors (snare_bottom -> snare_top, kick_beater -> a kick
    anchor) for stems that don't already name one. Runs again after a manifest
    overlay so a role correction re-wires the partner. Explicit partners kept."""
    snare_top = next((s for s in stems if s.role == Role.SNARE_TOP), None)
    kick_anchor = next((s for s in stems if s.role in _KICK_ANCHOR_ROLES), None)
    for s in stems:
        if s.partner is not None:
            continue
        if s.role == Role.SNARE_BOTTOM and snare_top:
            s.partner = snare_top.name
        elif s.role == Role.KICK_BEATER and kick_anchor:
            s.partner = kick_anchor.name


def _compute_overhead_mode(stems: list[KitStem]) -> str:
    has_oh = any(s.role == Role.OVERHEAD for s in stems)
    has_lr = (any(s.role == Role.OVERHEAD_L for s in stems)
              and any(s.role == Role.OVERHEAD_R for s in stems))
    return "lr_pair" if (has_lr and not has_oh) else "stereo"


def detect_kit(src_dir: str, exclude: tuple[str, ...] | set[str] = ()) -> Kit:
    """Pure filename auto-detect — no manifest, no validation.

    ``exclude`` basenames are skipped (e.g. a reference file sitting in src_dir).
    """
    excl = set(exclude)
    stems: list[KitStem] = []
    for name in _list_audio(src_dir):
        if name in excl:
            continue
        role, conf = detect_role(name)
        ks = KitStem(name=name, role=role, confidence=conf)
        # kick OH-correlation low-pass is applied by the phase-align flow
        # (--kick-lowpass, default 180 Hz); leave lowpass_hz unset unless a
        # manifest pins a per-mic value.
        if role == Role.ROOM:
            ks.ambience = True
        if role == Role.TOM:
            ks.label = _norm(name).replace("tom", "").strip() or None
        stems.append(ks)

    _wire_partners(stems)
    return Kit(src_dir=src_dir, stems=stems,
               overhead_mode=_compute_overhead_mode(stems),
               sr=_try_samplerate(src_dir, stems))


def load_manifest(path: str) -> dict:
    with open(path) as fh:
        return json.load(fh)


def save_manifest(kit: Kit, path: str) -> None:
    with open(path, "w") as fh:
        json.dump(kit.to_dict(), fh, indent=2)


def _apply_manifest(kit: Kit, path: str) -> dict:
    data = load_manifest(path)
    if "overhead_mode" in data:
        kit.overhead_mode = data["overhead_mode"]
    if "reference" in data:
        kit.reference = data["reference"]
    on_disk = set(_list_audio(kit.src_dir))
    for entry in data.get("stems", []):
        if "file" not in entry:
            raise KitError(f"manifest stem entry missing required 'file' key: {entry!r}")
        name = entry["file"]
        if name not in on_disk:
            raise KitError(f"manifest references a file that is not in {kit.src_dir!r}: {name!r}")
        ks = kit.by_name(name)
        if "role" in entry:
            try:
                role = Role(entry["role"])
            except ValueError:
                valid = [r.value for r in Role]
                raise KitError(
                    f"{name!r}: unknown role {entry['role']!r} (valid: {valid})"
                ) from None
        else:
            role = ks.role if ks else Role.UNKNOWN
        if ks is None:
            ks = KitStem(name=name, role=role)
            kit.stems.append(ks)
        else:
            ks.role = role
        ks.confidence = 1.0
        # validate optional field types so a malformed manifest fails loud here
        # (KitError -> clean CLI message) rather than blowing up deep in the DSP.
        # NB: bool is a subclass of int/float in Python, so each numeric/int check
        # excludes bool explicitly (and the bool field excludes int).
        lp = entry.get("lowpass_hz")
        if lp is not None and (isinstance(lp, bool) or not isinstance(lp, (int, float))):
            raise KitError(f"{name!r}: lowpass_hz must be a number or null, got {lp!r}")
        pol = entry.get("polarity_lock")
        if pol is not None and (not isinstance(pol, int) or isinstance(pol, bool)
                                or pol not in (1, -1)):
            raise KitError(f"{name!r}: polarity_lock must be 1, -1, or null, got {pol!r}")
        amb = entry.get("ambience")
        if amb is not None and not isinstance(amb, bool):
            raise KitError(f"{name!r}: ambience must be true, false, or null, got {amb!r}")
        for fld in ("label", "partner", "lowpass_hz", "ambience", "polarity_lock"):
            if fld in entry:
                setattr(ks, fld, entry[fld])
    return data


def _validate(kit: Kit, strict: bool) -> None:
    problems: list[str] = []
    has_oh = any(s.role == Role.OVERHEAD for s in kit.stems)
    has_lr = (any(s.role == Role.OVERHEAD_L for s in kit.stems)
              and any(s.role == Role.OVERHEAD_R for s in kit.stems))
    if not (has_oh or has_lr):
        problems.append("no overheads found (need role 'overhead', or both "
                        "'overhead_l' and 'overhead_r') — the topology is OH-referenced")
    for role in _SINGLETON_ROLES:
        dup = [s.name for s in kit.stems if s.role == role]
        if len(dup) > 1:
            problems.append(f"multiple stems resolved to {role.value}: {dup} — disambiguate in kit.json")
    valid = [r.value for r in Role if r != Role.UNKNOWN]
    for s in kit.stems:
        if s.role == Role.UNKNOWN:
            problems.append(f"could not detect a role for {s.name!r} — set it in kit.json (roles: {valid})")
        if s.partner and kit.by_name(s.partner) is None:
            problems.append(f"{s.name!r} names partner {s.partner!r}, which is not in the kit")
        if s.partner and (s.ambience or s.role == Role.ROOM):
            problems.append(f"{s.name!r} is ambience/room but names a partner "
                            f"{s.partner!r} — room mics are polarity-only and must not be partnered")
    if problems:
        if strict:
            raise KitError("kit resolution problems:\n  - " + "\n  - ".join(problems))
        kit.warnings = problems


def resolve_kit(src_dir: str, manifest_path: str | None = None, strict: bool = True,
                exclude: tuple[str, ...] | set[str] = ()) -> Kit:
    """Auto-detect, overlay ``kit.json`` (explicit ``manifest_path`` or one found
    in ``src_dir``), then validate. ``exclude`` basenames are ignored (e.g. a
    reference file living in ``src_dir``). See module docstring for strict semantics."""
    kit = detect_kit(src_dir, exclude=exclude)
    mpath = manifest_path or os.path.join(src_dir, "kit.json")
    if manifest_path or os.path.exists(mpath):
        if not os.path.exists(mpath):
            raise KitError(f"manifest not found: {mpath}")
        data = _apply_manifest(kit, mpath)
        _wire_partners(kit.stems)  # re-wire partners after any role corrections
        if "overhead_mode" not in data:
            kit.overhead_mode = _compute_overhead_mode(kit.stems)
    _validate(kit, strict)
    return kit


# --------------------------------------------------------------------------- #
# topology queries (consumed by the flows)
# --------------------------------------------------------------------------- #
def overhead_reference(kit: Kit) -> KitStem | None:
    """The pre-merged stereo OH stem, if present (None for an lr_pair kit)."""
    return next((s for s in kit.stems if s.role == Role.OVERHEAD), None)


def overhead_lr(kit: Kit) -> tuple[KitStem | None, KitStem | None]:
    left = next((s for s in kit.stems if s.role == Role.OVERHEAD_L), None)
    right = next((s for s in kit.stems if s.role == Role.OVERHEAD_R), None)
    return left, right


def ambience_stems(kit: Kit) -> list[KitStem]:
    return [s for s in kit.stems if s.ambience or s.role == Role.ROOM]


def partner_pairs(kit: Kit) -> list[tuple[KitStem, KitStem]]:
    """(partner, anchor) pairs — partner aligns to anchor, then composes onto OH.

    Ambience/room stems are skipped even if mis-tagged with a ``partner``: they
    are polarity-only (timing kept), so partnering them would both apply an
    alignment delay AND get them re-processed by the ambience pass (double write,
    wrong recorded delay). ``_validate`` flags the misconfiguration separately.
    """
    out = []
    for s in kit.stems:
        if s.ambience or s.role == Role.ROOM:
            continue
        anchor = kit.by_name(s.partner)
        if anchor is not None:
            out.append((s, anchor))
    return out


def anchored_to_oh(kit: Kit) -> list[KitStem]:
    """Close mics that align directly to the overheads (no partner, not OH/room/FX).
    Includes UNKNOWN stems in non-strict mode (treated as broadband close mics)."""
    return [s for s in kit.stems
            if s.role not in _OH_ROLES
            and not (s.ambience or s.role == Role.ROOM)
            and s.role != Role.FX
            and s.partner is None]


def fx_stems(kit: Kit) -> list[KitStem]:
    """Effect returns / auxes (plate, reverb, send) — excluded from alignment;
    handled only at the mix stage as returns."""
    return [s for s in kit.stems if s.role == Role.FX]
