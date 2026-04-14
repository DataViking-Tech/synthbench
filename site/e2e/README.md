# Site End-to-End Tests

This directory holds Playwright suites for the SynthBench site:

- `visual/smoke.visual.spec.ts` — smoke VRT (3 snapshots) over the three
  golden-path routes in dark theme, desktop viewport.
- `mobile-audit.spec.ts` / `mobile-audit.config.ts` — accessibility and layout
  checks at mobile viewports (not a VRT suite).

This README covers the **smoke VRT** workflow introduced by sb-o3b. The
previous full route-matrix suite (sb-va6, 36 snapshots × macOS baselines) was
retired because cross-platform font rendering produced false positives the
team could not sustainably investigate.

## What the smoke VRT covers

Three routes, one theme (dark), one viewport (Desktop Chrome 1280×800):

| Route | Purpose |
|-------|---------|
| `/` | Hero, key findings, summary leaderboard |
| `/leaderboard/` | Full leaderboard + charts |
| `/run/<representative-id>/` | Representative run detail page |

All baselines are produced in the **Ubuntu CI runner** (the Playwright
official Linux container) and committed to
`site/e2e/visual/__screenshots__/`. **Do not commit baselines generated on
macOS dev machines** — they will diverge on CI and mask real regressions.

### Masked dynamic content

Any element in the markup tagged `data-vrt-mask` is masked during compare.
Today that covers:

- Hero version string and generated date (home)
- Nav version badge (all routes)
- Footer copyright year (all routes)
- Run-detail timestamp (run-detail)

If you introduce new dynamic content that would move on every data regen
(timestamps, counts that drift, version strings), add `data-vrt-mask` to the
element so VRT stays stable.

## Running locally

```bash
# From site/
npm run build
npx playwright install chromium
npx playwright test --config=e2e/playwright.config.ts smoke.visual
```

Because baselines live under `desktop-chromium/` only (no platform split),
running locally on macOS will **diff against Linux baselines** and very
likely fail on font rasterization. Treat local runs as "did I break the
page structure" signal, not a green-light for merge.

To generate a report after a failed run:

```bash
npx playwright show-report playwright-report
```

## Updating baselines (CI-driven)

When an intentional visual change lands (new section, restyle, etc.), the
baselines need to be regenerated. **Do this via CI, not locally.**

1. Push your branch and open a PR.
2. Add the `vrt-baseline-update` label to the PR.
3. The `visual` job runs Playwright with `--update-snapshots`, commits the
   new baselines to your PR branch as `github-actions[bot]`, then re-runs
   VRT in compare mode to verify stability.
4. Remove the label (optional — it's a no-op once baselines match).
5. Because the update commit is a new commit on the PR branch, a **second
   reviewer approval** is conventionally required before merge. This catches
   accidental visual regressions hidden behind a baseline bump.

Notes:

- Cross-repo PRs from forks cannot commit baselines back (the CI
  `GITHUB_TOKEN` is not writable to forks). Maintainers: push to a
  same-repo branch and re-label, or run the update on a maintainer branch
  and cherry-pick.
- The update step writes to
  `site/e2e/visual/__screenshots__/smoke.visual.spec.ts/desktop-chromium/`.
- `GITHUB_TOKEN` pushes do not re-trigger CI (this is a GitHub restriction),
  which is why the workflow re-runs VRT inline within the same job rather
  than relying on a second push-triggered run.

## CI gate status

VRT is currently **advisory** — the `merge-ready` job does not require the
`visual` job to succeed. The rationale: during stabilization we want visual
diffs to surface as a signal reviewers investigate, not a hard blocker that
spams the merge queue.

After 3–5 PRs of green VRT with no investigation churn, we will flip VRT to
a **required** gate in the `dvinfra` branch protection (tracked as a
follow-up bead). The gate flip is a branch-protection change only; no code
change is required in this repo.

## Why only 3 snapshots

The previous suite (sb-va6) ran 9 routes × 2 themes × 2 devices = 36
snapshots. In practice every PR that touched shared CSS diffed on macOS vs
Linux in subtle ways (antialiasing, font hinting, emoji metrics) and the
team spent more time investigating baseline noise than catching real
regressions. The smoke suite trades breadth for reliability: if the home
page, leaderboard, and run-detail all render correctly in dark theme, the
rest of the site almost certainly does too. When coverage gaps bite, add a
targeted spec rather than re-expanding the matrix.
