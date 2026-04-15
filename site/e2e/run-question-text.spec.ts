import { expect, test } from "@playwright/test";

// sb-1h2 — Question text on /run/<id> per-question rows must render in full
// (not truncated) so reviewers can read long survey prompts without expanding
// every row. The previous implementation clipped at 110 chars + ellipsis,
// which hid the back half of a majority of OpinionQA prompts.
//
// Acceptance asserts:
//   * a question >110 chars renders its full text in the summary row
//   * the rendered text never contains the truncation ellipsis ("…")
//   * the rendered text remains reachable on a 375px mobile viewport

const SAMPLE_RUN_ID = "opinionsqa_ensemble_3blend_20260412_020745";
const ROUTE = `run/${SAMPLE_RUN_ID}/`;

test.describe("run detail: per-question text is not truncated", () => {
  test("desktop — long question renders in full in the summary row", async ({ page }) => {
    await page.goto(ROUTE);

    const firstRow = page.locator("#per-question-tbody tr.pq-row").first();
    await expect(firstRow).toBeVisible({ timeout: 10000 });

    // Find a row whose underlying text is genuinely long (>110 chars). The
    // sample run is published from leaderboard-results/ and stable across
    // builds, so at least one such row is guaranteed.
    const longRow = await page.evaluate(() => {
      const cells = Array.from(
        document.querySelectorAll<HTMLElement>("#per-question-tbody tr.pq-row .pq-text"),
      );
      for (let i = 0; i < cells.length; i++) {
        const text = cells[i].textContent ?? "";
        if (text.length > 110 && !text.includes("…")) {
          return { index: i, text, length: text.length };
        }
      }
      return null;
    });

    expect(longRow, "expected at least one >110-char question without ellipsis").not.toBeNull();
    expect(longRow?.length).toBeGreaterThan(110);
    expect(longRow?.text).not.toContain("…");

    // No summary-row pq-text on the page contains the truncation glyph.
    const ellipsisCount = await page
      .locator("#per-question-tbody tr.pq-row .pq-text", { hasText: "…" })
      .count();
    expect(ellipsisCount).toBe(0);
  });

  test("mobile (375px) — long question still renders fully without ellipsis", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 800 });
    await page.goto(ROUTE);

    const firstRow = page.locator("#per-question-tbody tr.pq-row").first();
    await expect(firstRow).toBeVisible({ timeout: 10000 });

    const ellipsisCount = await page
      .locator("#per-question-tbody tr.pq-row .pq-text", { hasText: "…" })
      .count();
    expect(ellipsisCount).toBe(0);

    // Sanity: at least one summary-row text wraps to a non-zero rendered
    // height that exceeds a single line of `text-xs` (≈ 16px line-height).
    const wrappedHeight = await page.evaluate(() => {
      const cells = Array.from(
        document.querySelectorAll<HTMLElement>("#per-question-tbody tr.pq-row .pq-text"),
      );
      let maxH = 0;
      for (const c of cells) {
        const h = c.getBoundingClientRect().height;
        if (h > maxH) maxH = h;
      }
      return maxH;
    });
    expect(wrappedHeight).toBeGreaterThan(20);
  });
});
