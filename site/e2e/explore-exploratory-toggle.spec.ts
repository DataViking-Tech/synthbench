import { expect, test } from "@playwright/test";

// sb-djv — Explore page: surface config differentiators + hide exploratory
// runs by default. Asserts the acceptance criteria from the bead:
//   * rows expose `s=<samples>` and `n=<questions>` chips so configs that
//     look identical at a glance are visually distinguishable
//   * the "Show exploratory runs" toggle defaults to OFF, hiding rows with
//     n_questions < 50 OR samples_per_question <= 10
//   * toggling reveals the hidden rows and the top-of-list counter surfaces
//     the hidden count while they are suppressed
//
// These tests run against the production build served by `npm run preview`
// (wired through playwright.config.ts). The runs-index.json is committed
// under site/public/data/ so the fixture is stable across runs.

test.describe("explore: exploratory runs toggle", () => {
  test("defaults to hiding exploratory runs and announces hidden count", async ({ page }) => {
    await page.goto("explore/");

    // Wait for the tree to populate (initial render clears the "Loading…" text).
    const firstRow = page.locator("#explore-tree [data-focus-key^='pick::']").first();
    await expect(firstRow).toBeVisible({ timeout: 10000 });

    // Toggle exists and defaults OFF (hide exploratory).
    const toggle = page.locator("#filter-exploratory");
    await expect(toggle).toBeVisible();
    await expect(toggle).not.toBeChecked();

    // Summary line surfaces hidden count with actionable hint when > 0.
    const summary = page.locator("#explore-summary");
    const hiddenText = await summary.textContent();
    expect(hiddenText ?? "").toMatch(/hidden — show exploratory/);
  });

  test("toggling ON reveals hidden rows; OFF hides them again", async ({ page }) => {
    await page.goto("explore/");
    const firstRow = page.locator("#explore-tree [data-focus-key^='pick::']").first();
    await expect(firstRow).toBeVisible({ timeout: 10000 });

    const rows = page.locator("#explore-tree [data-focus-key^='pick::']");
    const hiddenCount = await rows.count();

    const toggle = page.locator("#filter-exploratory");
    await toggle.check();
    const shownCount = await rows.count();
    expect(shownCount).toBeGreaterThan(hiddenCount);

    // Summary drops the hidden-count suffix once everything is visible.
    const summary = page.locator("#explore-summary");
    await expect(summary).not.toContainText("hidden — show exploratory");

    await toggle.uncheck();
    const hiddenAgain = await rows.count();
    expect(hiddenAgain).toBe(hiddenCount);
  });

  test("rows expose s= and n= chips for configs that report them", async ({ page }) => {
    await page.goto("explore/");
    const firstRow = page.locator("#explore-tree [data-focus-key^='pick::']").first();
    await expect(firstRow).toBeVisible({ timeout: 10000 });

    // Expand everything so we can reliably find a row with samples_per_question.
    await page.locator("#filter-exploratory").check();

    // At least one row must carry each chip — full coverage across all rows is
    // asserted implicitly by the render path (chips render whenever the data
    // is non-null / present in schema).
    const anyS = page.locator("#explore-tree >> text=/^s=\\d+$/").first();
    const anyN = page.locator("#explore-tree >> text=/^n=\\d+$/").first();
    await expect(anyS).toBeVisible();
    await expect(anyN).toBeVisible();
  });
});
