import { expect, test } from "@playwright/test";

// Pass 2.2 smoke VRT (sb-o3b) — replaces the 36-snapshot route+theme+device
// matrix from sb-va6 with a 3-snapshot smoke suite. One theme (dark), one
// device (desktop), three golden-path routes. Baselines are produced in
// Ubuntu CI via the `vrt-baseline-update` label workflow — do NOT commit
// baselines generated on macOS.
//
// Baselines last refreshed: 2026-04-15 (sb-l879) — catch-up after gated-tier
// UI (sb-sj6), OpinionsQA tier promotion (sb-dek), and shared CF/R2 creds
// migration (sb-vkz) landed cumulative pixel drift across all three snapshots.
//
// Representative run id is chosen to be stable across rebuilds: it lives in
// leaderboard-results/ and survives publish-runs regeneration.
const SAMPLE_RUN_ID = "opinionsqa_ensemble_3blend_20260412_020745";

type Route = {
  label: string;
  path: string;
  /** presence selector that gates the screenshot */
  readySelector?: string;
  /** extra settle time for chart paint after ready selector resolves */
  settleMs?: number;
  /** `fullPage` (default) or `viewport` for tall data-heavy pages */
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
    label: "run-detail",
    path: `run/${SAMPLE_RUN_ID}/`,
    readySelector: "#per-question-tbody tr.pq-row",
    settleMs: 2000,
    capture: "viewport",
  },
];

for (const route of ROUTES) {
  test(`${route.label} — dark`, async ({ page }) => {
    test.setTimeout(60000);
    await page.emulateMedia({ colorScheme: "dark" });
    await page.goto(route.path, { waitUntil: "networkidle" });
    if (route.readySelector) {
      await page.waitForSelector(route.readySelector, { timeout: 10000 });
    }
    if (route.settleMs) {
      await page.waitForTimeout(route.settleMs);
    }
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForLoadState("networkidle");

    const fullPage = (route.capture ?? "fullPage") === "fullPage";
    // Dynamic content is flagged in markup with `data-vrt-mask`:
    //   - Hero version + generated date (home)
    //   - Nav version badge (all routes)
    //   - Footer copyright year (all routes)
    //   - Run-detail timestamp (run-detail)
    // Masking hides these regions during compare without deleting them from
    // the page, so they remain functional for real users.
    await expect(page).toHaveScreenshot(`${route.label}-dark.png`, {
      fullPage,
      mask: [page.locator("[data-vrt-mask]")],
      timeout: 20000,
    });
  });
}
