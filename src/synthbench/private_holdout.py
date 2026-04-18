"""Private holdout split for the synthbench public leaderboard.

Each holdout-enabled dataset is deterministically partitioned 80/20 into a
public subset (keys whose ``human_distribution`` stays visible in published
artifacts) and a private subset (keys whose ``human_distribution`` is
suppressed — we score submissions against our hidden copy).

The split serves two purposes:

* **Anti-fabrication.** Once public per-question human distributions are
  visible, a submitter could fabricate a model-run JSON that matches them
  perfectly. The private answer key gives us a cheat detector: a cheater who
  copied public distributions has no signal for the private keys, so their
  public-vs-private SPS must diverge.
* **Anti-contamination.** Future LLMs may be trained on synthbench itself;
  holding out 20% prevents that recursion from consuming the whole benchmark.

The split is computed by hashing ``salt + ":" + base_dataset_name + ":" + key``
(or ``base_dataset_name + ":" + key`` when no salt is in effect). That gives
us these properties:

1. **Deterministic** — the same question under the same salt is always in the
   same partition, so ground-truth lookups on the private answer key are
   stable across runs.
2. **Dataset-scoped** — shared keys across datasets (e.g. ``Q_001``) partition
   independently, so a leak on one dataset doesn't leak them all.
3. **Adapter-free** — the publish step and validation pipeline can classify
   any ``(dataset, key)`` pair without the dataset adapter being loaded.
4. **Rotatable** — the salt component lets us bump the partition on a
   published schedule, re-exposing some previously-private keys and pushing
   previously-public keys into the private set. This forces any cached
   answer key to go stale on rotation day.

Only datasets in :data:`HOLDOUT_ENABLED_DATASETS` are split. Other datasets
resolve to public (``is_private_holdout`` → ``False``) so they are unchanged
by holdout enforcement. Tightening that set is a policy decision — see the
bead for the current rationale.

Salt rotation
-------------

The active salt is :data:`HOLDOUT_SALT`. It may be overridden at import time
via the ``SYNTHBENCH_HOLDOUT_SALT`` environment variable. ``None`` means the
legacy unsalted hash scheme is in effect (no rotation yet applied).

Rotation cadence is quarterly, with a 30-day submitter notice posted before
each rotation. See ``docs/holdout-rotation.md`` for the published calendar,
the notice procedure, and the rollback plan.

For one rotation cycle after a bump, callers may explicitly pass the
previous salt (``salt=HOLDOUT_SALT_PREVIOUS``) to re-score submissions under
the pre-rotation partition.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Iterable
from typing import Any

# Datasets we apply the 80/20 split to. Pewtech is excluded because it ships
# without per-question redistribution rights (citation_only) — the entire
# human distribution is already suppressed, so a holdout split adds nothing.
HOLDOUT_ENABLED_DATASETS: frozenset[str] = frozenset(
    {
        "eurobarometer",
        "globalopinionqa",
        "gss",
        "michigan",
        "ntia",
        "opinionsqa",
        "subpop",
        "wvs",
    }
)

# 20% private, 80% public. Kept as two constants (instead of a single float)
# so the split is integer-modulo-based and the boundary is unambiguous.
HOLDOUT_FRACTION = 20
HOLDOUT_MOD = 100

# SPS delta above which a submission's public/private divergence is flagged.
# Calibrated loosely — typical honest-submission delta is <0.02 on the runs
# we've analysed, so 0.05 catches fabrication without flagging normal noise.
SPS_DIVERGENCE_THRESHOLD = 0.05


def _resolve_env_salt() -> str | None:
    """Read ``SYNTHBENCH_HOLDOUT_SALT`` from the environment at import time.

    An empty string resolves to ``None`` (legacy unsalted mode) so that
    ``SYNTHBENCH_HOLDOUT_SALT=""`` can be used as an explicit rollback
    knob without having to unset the variable.
    """
    raw = os.environ.get("SYNTHBENCH_HOLDOUT_SALT")
    if raw is None or raw == "":
        return None
    return raw


# Active salt. ``None`` means the pre-rotation legacy hash is in effect
# (``sha256(base + ":" + key)``). When the rotation calendar bumps this to
# a real salt, prior submissions can still be re-scored for one cycle by
# passing ``salt=HOLDOUT_SALT_PREVIOUS`` to the helpers below.
HOLDOUT_SALT: str | None = _resolve_env_salt()

# Previous active salt, retained for one rotation cycle so submitters and
# validators can re-score historical runs under the pre-rotation partition.
# ``None`` means "the pre-rotation scheme was unsalted" (current state:
# no rotation has happened yet). When we rotate to "2026Q3" this flips to
# ``None``; when we rotate to "2026Q4" it flips to ``"2026Q3"``; etc.
HOLDOUT_SALT_PREVIOUS: str | None = None


# Sentinel used to distinguish "caller omitted salt argument, use the active
# :data:`HOLDOUT_SALT`" from "caller passed ``salt=None``, use the legacy
# unsalted hash". ``None`` is a valid salt value meaning "unsalted".
_USE_ACTIVE_SALT: Any = object()


def _base_dataset_name(dataset: str) -> str:
    """Strip the ``(filter)`` suffix from names like ``gss (2018)``.

    Filtered adapter variants share the same question set at the adapter
    level, so they share the same holdout partition.
    """
    return dataset.split(" ", 1)[0].strip()


def _hash_payload(salt: str | None, base: str, key: str) -> str:
    """Hash the ``(salt, base, key)`` triple to a hex digest.

    When ``salt`` is ``None`` the legacy unsalted payload (``base:key``)
    is hashed so that pre-rotation submissions retain a stable partition.
    When ``salt`` is a string the salted payload (``salt:base:key``) is
    hashed — the salt is prefixed so a keyspace collision with the legacy
    scheme is impossible (legacy payloads never begin with ``:``).
    """
    if salt is None:
        payload = f"{base}:{key}"
    else:
        payload = f"{salt}:{base}:{key}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def is_holdout_enabled(dataset: str) -> bool:
    """True iff the dataset participates in the 80/20 split."""
    return _base_dataset_name(dataset) in HOLDOUT_ENABLED_DATASETS


def is_private_holdout(
    dataset: str, key: str, *, salt: str | None = _USE_ACTIVE_SALT
) -> bool:
    """Return ``True`` when ``(dataset, key)`` belongs to the private 20%.

    Hash-based and stable: the same ``(dataset, key)`` pair under the same
    salt always lands in the same partition across runs, machines, and
    Python versions (the hash is SHA-256 on a fixed ASCII encoding).

    ``salt`` defaults to the module-level :data:`HOLDOUT_SALT`. Passing an
    explicit ``salt=None`` forces the pre-rotation legacy partition;
    passing ``salt=HOLDOUT_SALT_PREVIOUS`` re-scores under the previous
    rotation. This is the one-cycle old-salt evaluation path.

    Datasets outside :data:`HOLDOUT_ENABLED_DATASETS` always return ``False``.
    """
    base = _base_dataset_name(dataset)
    if base not in HOLDOUT_ENABLED_DATASETS:
        return False
    active_salt = HOLDOUT_SALT if salt is _USE_ACTIVE_SALT else salt
    digest = _hash_payload(active_salt, base, key)
    bucket = int(digest[:8], 16) % HOLDOUT_MOD
    return bucket < HOLDOUT_FRACTION


def holdout_keys(
    dataset: str, keys: Iterable[str], *, salt: str | None = _USE_ACTIVE_SALT
) -> set[str]:
    """Return the subset of ``keys`` that belong to the private partition."""
    base = _base_dataset_name(dataset)
    if base not in HOLDOUT_ENABLED_DATASETS:
        return set()
    return {k for k in keys if is_private_holdout(base, k, salt=salt)}


def split_keys(
    dataset: str, keys: Iterable[str], *, salt: str | None = _USE_ACTIVE_SALT
) -> tuple[list[str], list[str]]:
    """Return ``(public_keys, private_keys)`` preserving iteration order."""
    base = _base_dataset_name(dataset)
    public: list[str] = []
    private: list[str] = []
    if base not in HOLDOUT_ENABLED_DATASETS:
        return list(keys), []
    for key in keys:
        if is_private_holdout(base, key, salt=salt):
            private.append(key)
        else:
            public.append(key)
    return public, private


def _partition_rows(
    dataset: str,
    per_question: Iterable[dict],
    *,
    salt: str | None = _USE_ACTIVE_SALT,
) -> tuple[list[dict], list[dict]]:
    """Split per-question dicts into (public, private) lists.

    Rows missing a ``key`` or keyed off a non-holdout dataset flow into the
    public list; callers treat those as not-split.
    """
    if not is_holdout_enabled(dataset):
        return list(per_question), []
    public: list[dict] = []
    private: list[dict] = []
    base = _base_dataset_name(dataset)
    for row in per_question:
        key = row.get("key") if isinstance(row, dict) else None
        if isinstance(key, str) and is_private_holdout(base, key, salt=salt):
            private.append(row)
        else:
            public.append(row)
    return public, private


def _subset_sps(rows: list[dict]) -> float | None:
    """Recompute SPS over a subset of per-question rows.

    Mirrors the two-component parity blend used by
    :func:`synthbench.metrics.composite.parity_score` (``0.5 * (1 - JSD) +
    0.5 * (1 + tau) / 2``). Refusal calibration is intentionally excluded so
    the split-SPS is computable from the same fields every submission must
    provide — this is a cheating detector, not a full-fidelity rerun.

    Returns ``None`` when the subset is empty or has no numeric metrics.
    """
    jsd_vals: list[float] = []
    tau_vals: list[float] = []
    for row in rows:
        jsd = row.get("jsd")
        tau = row.get("kendall_tau")
        if isinstance(jsd, (int, float)) and isinstance(tau, (int, float)):
            jsd_vals.append(float(jsd))
            tau_vals.append(float(tau))
    if not jsd_vals:
        return None
    mean_jsd = sum(jsd_vals) / len(jsd_vals)
    mean_tau = sum(tau_vals) / len(tau_vals)
    p_dist = 1.0 - max(0.0, min(1.0, mean_jsd))
    p_rank = (max(-1.0, min(1.0, mean_tau)) + 1.0) / 2.0
    return 0.5 * p_dist + 0.5 * p_rank


def compute_split_sps(
    dataset: str,
    per_question: Iterable[dict],
    *,
    salt: str | None = _USE_ACTIVE_SALT,
) -> dict[str, float | int | None]:
    """Compute public/private SPS pair + divergence + per-subset counts.

    Returned keys are always present; numeric fields are ``None`` whenever
    the subset is empty or lacks numeric metrics. Callers surface them as
    ``sps_public`` / ``sps_private`` on the submission record and flag rows
    whose ``delta`` exceeds :data:`SPS_DIVERGENCE_THRESHOLD`.
    """
    public_rows, private_rows = _partition_rows(dataset, per_question, salt=salt)
    sps_public = _subset_sps(public_rows)
    sps_private = _subset_sps(private_rows)
    delta: float | None
    if sps_public is None or sps_private is None:
        delta = None
    else:
        delta = abs(sps_public - sps_private)
    return {
        "sps_public": sps_public,
        "sps_private": sps_private,
        "delta": delta,
        "n_public": len(public_rows),
        "n_private": len(private_rows),
        "flagged": (delta is not None and delta > SPS_DIVERGENCE_THRESHOLD),
    }


__all__ = [
    "HOLDOUT_ENABLED_DATASETS",
    "HOLDOUT_FRACTION",
    "HOLDOUT_MOD",
    "HOLDOUT_SALT",
    "HOLDOUT_SALT_PREVIOUS",
    "SPS_DIVERGENCE_THRESHOLD",
    "compute_split_sps",
    "holdout_keys",
    "is_holdout_enabled",
    "is_private_holdout",
    "split_keys",
]
