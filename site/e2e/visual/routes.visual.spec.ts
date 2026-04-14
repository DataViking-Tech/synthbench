import { expect, test } from "@playwright/test";

// Pass 2.1 route-level VRT (sb-va6) — full-page visual coverage for all 9 routes
// at Desktop Chrome (1280x800) + Pixel 5, in light and dark themes.
//
// Representative config/run IDs are chosen to be stable across rebuilds:
//   - ensemble/3-model-blend on opinionsqa (the headline "best" config)
//   - raw Haiku 4.5 on opinionsqa         (the headline "best single model")
// They live in leaderboard-results/ and survive publish-runs regeneration.

const SAMPLE_CONFIG_A = "ensemble--3-model-blend--tdefault--tplcurrent--1bef3e62"; // opinionsqa ensemble
const SAMPLE_CONFIG_B = "openrouter--claude-haiku-4-5--tdefault--tplcurrent--f09861bc"; // opinionsqa raw haiku
const SAMPLE_RUN_ID = "opinionsqa_ensemble_3blend_20260412_020745";

type Route = {
  label: string;
  path: string;
  /** selector to wait for before screenshotting (presence, not visibility) */
  readySelector?: string;
  /** extra settle time for chart paint after ready selector resolves */
  settleMs?: number;
  /**
   * Capture strategy. `fullPage` (default) captures the entire scroll height;
   * `viewport` only captures the first 1280x800 (desktop) / 393x851 (mobile)
   * — used for data-heavy pages (run-detail, config-detail) whose tables
   * grow to 150k+ pixels and would produce multi-MB PNGs per baseline.
   */
  capture?: "fullPage" | "viewport";
};

const ROUTES: Route[] = [
  {
    label: "home",
    path: "",
    readySelector: ".echarts-container canvas, .echarts-container svg",
    settleMs: 1000,
  },
  {
    label: "leaderboard",
    path: "leaderboard/",
    readySelector: "#leaderboard",
    settleMs: 500,
  },
  {
    label: "findings",
    path: "findings/",
    settleMs: 300,
  },
  {
    label: "methodology",
    path: "methodology/",
    settleMs: 300,
  },
  {
    label: "submit",
    path: "submit/",
    settleMs: 300,
  },
  {
    label: "explore",
    path: "explore/",
    readySelector: "#explore-summary",
    settleMs: 500,
  },
  {
    label: "config-detail",
    path: `config/${SAMPLE_CONFIG_A}/`,
    // Title populates after JSON fetch — waiting for non-Loading state
    // ensures the SPS numbers and replicates table are rendered.
    readySelector: "#config-title:not(:has(.text-muted))",
    settleMs: 2000,
    capture: "viewport",
  },
  {
    label: "run-detail",
    path: `run/${SAMPLE_RUN_ID}/`,
    // Wait for at least one per-question row to render (replaces the
    // "Loading per-question detail…" skeleton).
    readySelector: "#per-question-tbody tr.pq-row",
    settleMs: 2000,
    capture: "viewport",
  },
  {
    label: "compare",
    path: `compare/?a=${SAMPLE_CONFIG_A}&b=${SAMPLE_CONFIG_B}&mode=config`,
    readySelector: "#compare-root",
    settleMs: 1000,
  },
];

const THEMES = [
  { label: "light", colorScheme: "light" as const },
  { label: "dark", colorScheme: "dark" as const },
];

for (const route of ROUTES) {
  for (const theme of THEMES) {
    test(`${route.label} — ${theme.label}`, async ({ page }) => {
      // Tall pages + stability re-compare + networkidle wait can push past
      // the default 30s test timeout; give full-page VRT enough runway.
      test.setTimeout(60000);
      await page.emulateMedia({ colorScheme: theme.colorScheme });
      await page.goto(route.path, { waitUntil: "networkidle" });
      if (route.readySelector) {
        await page.waitForSelector(route.readySelector, { timeout: 10000 });
      }
      if (route.settleMs) {
        await page.waitForTimeout(route.settleMs);
      }
      // Pin viewport scroll to top — fullPage capture is independent, but
      // layout of sticky nav depends on scroll position.
      await page.evaluate(() => window.scrollTo(0, 0));
      // Wait for any pending network activity to settle (second fetch waves,
      // lazy font loading, etc.) so the stability-compare doesn't see diffs.
      await page.waitForLoadState("networkidle");
      const fullPage = (route.capture ?? "fullPage") === "fullPage";
      await expect(page).toHaveScreenshot(`${route.label}-${theme.label}.png`, {
        fullPage,
        // Tall pages (run-detail has ~dozens of expanded table rows) need
        // extra headroom for Playwright's internal stability re-compare.
        timeout: 20000,
      });
    });
  }
}
