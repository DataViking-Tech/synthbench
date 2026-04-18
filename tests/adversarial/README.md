# Adversarial fixture suite

A known-bad acceptance gate for the SynthBench submission validator.

Every fixture in `fixtures/` is a fabricated submission that *must* be
caught by at least one detector. The suite runs in CI (via `pytest tests/`)
and is the contract that future detector tuning — threshold changes,
severity promotions, new detector additions — has to keep passing.

Introduced by bead **sb-5xfk** in response to Wang et al. 2026 (Berkeley
RDI, *How We Broke Top AI Agent Benchmarks*). See
`docs/benchmark-hardening-analysis.md` section 5 for the full threat
model and recipe catalogue.

## Layout

```
tests/adversarial/
  fixtures/                      # static JSON fabrications (checked in)
    pure_copy.json
    near_pure_copy.json
    public_copy_fake_private.json
    constant_offset.json
    impossible_bounds.json
    lied_aggregate.json
    zero_private_rows.json
    wrong_keys.json
    null_agent.json
    raw_response_desync.json
  expected.json                  # the per-fixture contract
  test_adversarial_suite.py      # harness
  _generate_fixtures.py          # deterministic generator
  README.md                      # this file
```

## What the suite asserts

For every fixture, three contract directions are checked.

* **`must_fire`** — every declared code appears on the validation report.
  Severity doesn't matter here: detector promotions from WARNING to
  ERROR (e.g. the `ANOMALY_PERFECTION` ERROR promotion in sb-oy72) leave
  this check unaffected.
* **`must_not_fire`** — every declared code is absent from the report.
  This is the anti-over-firing direction: if you tune a threshold to
  catch a new attack and it starts firing on an unrelated fixture, the
  suite fails.
* **`must_be_ok`** — when `true`, the fixture must validate cleanly (no
  errors); when `false`, it must be rejected. `null` defers the check —
  used for fixtures whose primary detector is still WARNING-tier today
  and is scheduled to graduate to ERROR in a dependent bead.

Two additional protections:

* **`future_fire`** — codes gated on a detector that hasn't landed yet.
  The check reads the dotted detector path (e.g.
  `synthbench.anomaly.check_near_copy_public`) and **skips** the
  assertion when the symbol isn't importable. The moment the upstream
  bead lands and the detector is callable, the same check goes live
  without any change to this directory.
* **`extra_assertions`** — named bespoke checks implemented in
  `test_adversarial_suite.py::TestBespokeAssertions`. Today: the
  caller-supplied canonical-hash path (`QSET_HASH_DATASET`) and the
  null-agent baseline SPS band.

## Running the suite locally

```bash
# Everything
pytest tests/adversarial/ -v

# One fixture
pytest tests/adversarial/ -v -k near_pure_copy

# Skip the suite entirely (during detector exploration)
pytest tests/ --ignore=tests/adversarial
```

The `validate-submissions` CI job already invokes `pytest tests/`, so
new fixtures are automatically picked up without any workflow change.

## Adding a new fabrication

1. **Write a recipe** in `_generate_fixtures.py`: a function that
   returns a complete submission dict. Use the `_per_question_entry`
   and `_assemble` helpers — they ensure JSD/tau are exactly the
   values scipy + the production metric functions would compute, so
   your fixture is immune to Tier-2 recompute false positives.

2. **Register the recipe** in the `FIXTURES` dict at the bottom of the
   generator.

3. **Declare the contract** in `expected.json` under the
   `fixtures` key. Required fields:
   * `description`
   * `must_fire` (may be empty for not-a-fabrication fixtures)
   * `must_not_fire`
   * `must_be_ok` — `true`, `false`, or `null`

   Optional fields: `future_fire`, `extra_assertions`.

4. **Regenerate the JSON**:

   ```bash
   python -m tests.adversarial._generate_fixtures
   ```

   The test `test_fixtures_are_deterministic` guards against
   hand-edited JSON drifting from the generator, so you *must* run
   the generator rather than editing the fixture file directly.

5. **Run the suite** and commit the new JSON:

   ```bash
   pytest tests/adversarial/ -v
   git add tests/adversarial/
   ```

## Adding a new detector

When you implement a new Tier-3 detector:

1. Wire it into `synthbench.anomaly.tier3_checks` (or wherever the
   corresponding dispatcher lives).
2. Pick the fixtures the detector *should* catch and add the new code
   under their `must_fire` list (or `future_fire` if the detector is
   gated on further work).
3. Run the full suite. All fixtures whose `must_not_fire` now includes
   your new code should still pass — that's the false-positive guard.
4. If you're tightening severity (e.g. promoting a code from WARNING
   to ERROR at a given N), consider flipping the matching fixture's
   `must_be_ok` from `null` to `false`.

## Design choices worth knowing

* **Static JSON, not generated at test time.** Keeps the suite
  deterministic, reviewable in PRs, and immune to scipy / Python
  version drift. The generator is only re-run when a recipe changes.
* **`must_fire` severity-agnostic.** A detector promoted from WARNING
  to ERROR should not force a sweeping fixture rewrite. The suite's
  job is to detect *presence*; severity is decided by the validator.
* **`future_fire` for staged rollouts.** The roadmap bead plan in
  `docs/benchmark-hardening-analysis.md` §7 lands detectors serially.
  Rather than publishing a broken suite between beads, the harness
  skips detectors that aren't yet callable. Nothing to clean up after
  a detector ships — the check automatically activates.
* **10 fixtures is the floor, not the ceiling.** Bead sb-5xfk
  mandates ≥10; add more as new attack classes surface. The intent is
  to grow the suite every time a gaming attempt is caught in the wild.
