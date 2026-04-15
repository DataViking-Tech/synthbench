# Post-flip audit — synth-panel → synthpanel public release

Audit date: 2026-04-15
Auditor: synthbench/polecats/chrome
Tracking bead: sb-arr

## Status: GREEN

All in-scope synthbench-side fixes landed. No blockers. A handful of
follow-ups remain on the SynthPanel side and on the operator's PyPI /
GitHub admin surface — called out below.

---

## Operator follow-ups (cannot fix from a synthbench polecat)

These are visible to a founder with write access to PyPI and to the
SynthPanel repo; a synthbench polecat cannot land them from here.

1. **Verify PyPI trusted publisher is rebound to `DataViking-Tech/SynthPanel`.**
   PyPI pins trusted publishers to a specific `owner/repo` string. TestPyPI
   publishes from `main` succeeded after the rename (e.g. 2026-04-15 03:35Z),
   so dev publishing is already known-good. The last successful *production*
   publish (`Publish to PyPI` workflow) was 2026-04-11 — pre-rename — and the
   three attempts on 2026-04-12 failed for unrelated reasons. The next real
   production publish (v0.9.0 or later) is the first signal that will prove
   the prod binding. If it fails with a trusted-publisher error, update
   https://pypi.org/manage/project/synthpanel/settings/publishing/ to point
   at `DataViking-Tech/SynthPanel`.

2. **Patch stale `synth-panel` references inside the SynthPanel repo
   README.** Two occurrences that this polecat could not touch (out of
   worktree scope):
   - `README.md:34` — `pip install git+https://github.com/DataViking-Tech/synth-panel.git@main` → `.../SynthPanel.git`
   - `README.md:455` — `"synth-panel's ability to produce representative synthetic respondents..."` → `"synthpanel's ability..."`

3. **Public-launch polish on the SynthPanel repo (GitHub admin surface).**
   Current state: description set, MIT license present, default branch `main`.
   Missing: repository topics (empty), homepage URL (empty), README badges.
   Suggested topics: `synthetic-respondents`, `llm-evaluation`,
   `persona-simulation`, `survey-research`, `python`, `mcp`.
   Suggested homepage: the synthbench leaderboard
   (https://dataviking-tech.github.io/synthbench/). Suggested badge set:
   PyPI version, CI status, MIT license, Python versions.

4. **Update git remotes in sister worktrees.** GitHub redirects the old URL
   forever, so nothing is broken — this is hygiene. Locations still pointing
   at `https://github.com/DataViking-Tech/synth-panel.git`:
   - `/Users/openclaw/gastown-dev/synthpanel/` (rig root)
   - `/Users/openclaw/gastown-dev/synthpanel/polecats/{capable,dag,slit,toast}/synthpanel/`
   - `/Users/openclaw/gastown-dev/synth-panel/` (stale pre-rename checkout — see #5)

   One-liner for each: `git remote set-url origin https://github.com/DataViking-Tech/SynthPanel.git`.

5. **Remove or archive the orphan `/Users/openclaw/gastown-dev/synth-panel/`
   directory.** Last modified 2026-04-07 (pre-rename), still has the old
   remote, and is now shadowed by the live `/synthpanel/` worktree. It is a
   trap for future polecats who may `cd` into the wrong tree. Candidate for
   `rm -rf` by operator once verified to contain no uncommitted work.

6. **Version bump to v0.9.0 explicitly deferred.** Per the bead notes, the
   next operator action is a separate v0.9.0 release; this audit did not bump
   versions.

---

## Verified working

- **Repo rename complete.** `gh repo view DataViking-Tech/SynthPanel`
  returns `{"name": "SynthPanel", "visibility": "PUBLIC"}`. MIT license
  present; `LICENSE` renders on the GitHub UI.
- **PyPI `synthpanel` 0.8.0 installable.** Both wheel
  (`synthpanel-0.8.0-py3-none-any.whl`) and sdist (`synthpanel-0.8.0.tar.gz`)
  are published with `requires_python = ">=3.10"`. The distribution name
  was always `synthpanel` (no hyphen) even when the repo was
  `synth-panel`, so `pip install -e .` against synthbench still resolves
  `synthpanel>=0.2.0` from `pyproject.toml` unchanged.
- **Python import path `synth_panel.*` intact.** The Python import name
  (with underscore) differs from the PyPI distribution name (without), and
  the rename does not touch either. `from synth_panel.cost import
  lookup_pricing_by_provider` in `src/synthbench/publish.py` and
  `from synth_panel.llm.client import LLMClient` in
  `src/synthbench/providers/synthpanel.py` continue to work.
- **Synthbench CI green on main.** Most-recent runs of `CI` and
  `Deploy Pages` on `main` both succeeded on 2026-04-15.
- **SynthPanel CI green on main.** Most-recent runs of `CI`, `Auto Semver
  Tag`, and `Publish Dev to TestPyPI` on `main` all succeeded on 2026-04-15.
  TestPyPI trusted publishing is confirmed working post-rename.
- **No workflow YAML in SynthPanel hardcodes the old `synth-panel`
  slug.** `publish.yml`, `publish-test.yml`, `auto-tag.yml`, and `ci.yml`
  all reference `synthpanel` (lowercase distribution name) in user-facing
  summary lines only; GitHub URLs there use relative references and work
  post-rename.
- **No open synthbench beads mention `synth-panel`** other than the audit
  bead itself (`sb-arr`). The only other hit (`sb-0kc`) is a closed
  historical slice and was left alone. Eight SynthPanel beads mention
  `synth-panel` but are all closed historical records and were left alone.

## Fixed in this PR

All replacements are for the display / project-name use of `synth-panel`
(with hyphen). GitHub URLs went to the new Pascal-case canonical form
(`DataViking-Tech/SynthPanel`). Python import names (`synth_panel`, with
underscore) are untouched — they are a separate name axis that the rename
did not affect.

- `README.md` — intro blurb: display text `synth-panel` → `synthpanel`,
  URL → `SynthPanel`.
- `src/synthbench/stats.py` — vendor-source comment at file head.
- `tests/test_publish_cost.py` — explanatory comment on the
  `synth_panel.cost` import-skip.
- `tests/test_stats_golden.py` — module docstring plus one class docstring
  referencing the source-of-truth stats package.
- `site/src/components/home/CTASection.astro` — "Try SynthPanel" CTA href.
- `METHODOLOGY.md` — seven display references: provider listing, example
  provider name, adapter table row, CLI example, JSON example, score card
  header, and leaderboard table row.
- `site/src/components/methodology/CostMethodology.astro` — three
  display references in the published methodology page copy.

Zero hyphenated `synth-panel` strings remain in the synthbench worktree
after these edits (verified by repo-wide grep).

## Future-proofing recommendations

- **CI guard against regressions.** Add a lightweight step to `ci.yml`
  that `grep -rn "synth-panel"` across the repo and fails on any match.
  Keeps the canonical naming from drifting back in via new contributions.
  Deliberately lightweight — no tool dependency, just `grep -r`.
- **Consider flipping synthbench visibility to PUBLIC.** SynthPanel is now
  public; the synthbench leaderboard references synth-panel openly. The
  synthbench repo itself is still PRIVATE (`gh repo view` confirms). If the
  operator intends the leaderboard to cite a public benchmark harness, the
  harness repo needs to be public too. Deferred — not in scope for this
  bead.
- **Add LICENSE + topics to synthbench for parity when it does go
  public.** Current `synthbench` repo has no license and no topics; a
  public flip would want MIT (matching SynthPanel) and topics like
  `benchmark`, `llm-evaluation`, `synthetic-respondents`, `opinions-qa`.
- **Document the two-name axis in one place.** The
  `synthpanel` (PyPI distribution) vs `synth_panel` (Python import) vs
  `SynthPanel` (GitHub repo casing) distinction tripped this auditor
  briefly and will trip future contributors. A short note in
  `CONTRIBUTING.md` (or the SynthPanel README) would save cycles.
