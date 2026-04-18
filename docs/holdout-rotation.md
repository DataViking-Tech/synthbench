# Private-holdout salt rotation

This document specifies the operational calendar, notice procedure, and
rollback plan for the salt-based quarterly rotation of the private-holdout
partition defined in `src/synthbench/private_holdout.py`.

Background on *why* we rotate is in
[`docs/benchmark-hardening-analysis.md`](./benchmark-hardening-analysis.md)
§4.3. This file is the operational runbook.

## 1. Salt semantics

The partition hash is

    sha256(HOLDOUT_SALT + ":" + base_dataset_name + ":" + key)

when `HOLDOUT_SALT` is a non-empty string, and

    sha256(base_dataset_name + ":" + key)

when `HOLDOUT_SALT` is `None` (legacy pre-rotation scheme). Helpers accept
an optional keyword `salt=` argument that overrides the module-level
`HOLDOUT_SALT` — this is how the validator re-scores historical
submissions under an old salt.

Two module constants pin the rotation state:

| Constant                | Meaning                                          |
|-------------------------|--------------------------------------------------|
| `HOLDOUT_SALT`          | Active salt (the one new submissions are scored under). `None` = pre-rotation. |
| `HOLDOUT_SALT_PREVIOUS` | Previous salt, retained for one rotation cycle.  |

The env var `SYNTHBENCH_HOLDOUT_SALT` overrides `HOLDOUT_SALT` at import
time. Setting it to the empty string explicitly selects the legacy
unsalted scheme (useful for rollback).

## 2. Rotation calendar

| Salt value | Active window          | Notice posted | Rollback deadline |
|------------|------------------------|---------------|-------------------|
| `None` (legacy) | through 2026-06-30 | —             | —                 |
| `"2026Q3"` | 2026-07-01 → 2026-09-30 | 2026-06-01    | 2026-07-31        |
| `"2026Q4"` | 2026-10-01 → 2026-12-31 | 2026-09-01    | 2026-10-31        |
| `"2027Q1"` | 2027-01-01 → 2027-03-31 | 2026-12-01    | 2027-01-31        |

The calendar extends quarterly thereafter. Rotation day is the first
calendar day of the quarter (UTC). Submitters get 30 days' advance notice
on the leaderboard announcement feed and in the CHANGELOG.

## 3. Rotation procedure

On notice day (T−30):

1. Open a rotation bead referencing this runbook.
2. Announce the upcoming salt on the leaderboard feed and in CHANGELOG.
3. Regenerate adversarial fixtures that depend on the partition
   (`tests/adversarial/_generate_fixtures.py`, `tests/adversarial/build_fixtures.py`)
   under the new salt and hold the diff on a branch — do **not** merge
   until cutover day.

On cutover day (T):

1. Land the bump in `src/synthbench/private_holdout.py`:
   - Promote `HOLDOUT_SALT` from the prior value into `HOLDOUT_SALT_PREVIOUS`.
   - Set `HOLDOUT_SALT` to the new quarter's string.
2. Merge the regenerated fixtures from step 3 above.
3. Republish the public leaderboard artifacts: every key that just moved
   from private → public has its `human_distribution` written back into
   the published per-question rows. Every key that moved public → private
   has its `human_distribution` redacted from the published artifact.
4. Tag the benchmark version bump (`schema_version`).

Between T and T+30 (one-cycle overlap window):

- The validator continues accepting submissions scored under the
  previous salt. Callers pass `salt=HOLDOUT_SALT_PREVIOUS` to the
  helpers; the public CLI exposes this via the `--holdout-salt=` flag.
- Submitters are encouraged to re-score under the new salt during this
  window so that post-T+30 comparisons stay apples-to-apples.

On T+30:

- `HOLDOUT_SALT_PREVIOUS` is cleared (set to `None` if the previous was
  non-legacy, otherwise left as `None`). Submissions still pinned to the
  old salt are archived as `schema_version < N`.

## 4. Rollback plan

A rotation can be rolled back if — **within the 30-day overlap window** —
we discover a critical bug in the new partition (e.g. a dataset adapter
shipped a broken key suffix that shifted classification on hundreds of
keys, or the fixture regen produced inconsistent public/private labels).

### 4.1 Emergency rollback (same-day or within 72h)

1. Revert the PR that bumped `HOLDOUT_SALT` (and its fixture companion).
2. Publish a rollback notice on the leaderboard feed and CHANGELOG
   referencing the original rotation bead.
3. Set `SYNTHBENCH_HOLDOUT_SALT=""` in the production validator
   environment as a belt-and-suspenders override until the revert
   propagates.
4. Leave `HOLDOUT_SALT_PREVIOUS` pointing at its previous value — we're
   conceptually *un-rotating*, so the previous previous becomes active.

### 4.2 Delayed rollback (within 30d overlap)

If the bug is detected later in the window but before T+30:

1. Do **not** revert — submissions have already been scored under the new
   salt and those records must remain interpretable.
2. Instead, land a hotfix that corrects the specific partition bug
   without bumping the salt. Keys that were misclassified move atomically
   under the same salt, and the regression is logged in
   `docs/benchmark-hardening-analysis.md`.
3. If the bug is structural and a hotfix is infeasible, schedule an
   **emergency mid-quarter rotation** to a new salt (e.g. `"2026Q3b"`),
   following the standard rotation procedure with compressed notice
   (72h instead of 30d). Announce the emergency on all feeds.

### 4.3 Post-window rollback

After T+30 the old salt is retired and rollback is no longer available.
Detected bugs that far out are handled by a fresh rotation cycle — the
next quarterly bump — and an entry in the hardening analysis
post-mortem section.

## 5. Operational invariants

These invariants hold at every point in the rotation lifecycle:

1. The active salt (`HOLDOUT_SALT`) is either `None` or a short ASCII
   string. The string format is the calendar quarter (`YYYYQn`) plus an
   optional disambiguator (`YYYYQnb`) for emergency rotations.
2. `HOLDOUT_SALT_PREVIOUS` is `None` or a value that was previously
   `HOLDOUT_SALT`. It is never set to a salt that was never active.
3. Partition functions return the same answer for the same
   `(dataset, key, salt)` triple across machines, Python versions, and
   time. Any change must be treated as an ABI break.
4. `HOLDOUT_ENABLED_DATASETS` is independent of the salt — adding or
   removing a dataset is **not** a rotation and follows its own
   deprecation path.

## 6. References

- [§4.3 of the hardening analysis](./benchmark-hardening-analysis.md)
  for motivation and the adversary model.
- `src/synthbench/private_holdout.py` for the implementation.
- `tests/test_private_holdout.py` covers the salt parameter semantics,
  env-var override, and determinism across rotations.
