import { expect, test } from "@playwright/test";

// sb-91t — Cost vs SPS Pareto chart on /findings.
// The chart only renders interactive content once leaderboard.json has
// real cost_usd values (Slice 3 derives them at publish time, but pre-cost
// runs still emit null). The spec covers both states:
//   - chart present  → exercises figure a11y, hover tooltip, expandable data table
//   - empty-state    → asserts the section + placeholder copy still mount
// The point is to catch regressions of either path, not gate on data shape.

const SECTION = "#cost-performance-pareto";

test.describe("/findings — Cost vs SPS Pareto", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("findings/", { waitUntil: "networkidle" });
    await page.waitForSelector(SECTION);
  });

  test("section is present with heading", async ({ page }) => {
    const section = page.locator(SECTION);
    await expect(section).toBeVisible();
    await expect(section.locator("h2")).toHaveText(/Cost vs Performance Pareto/i);
  });

  test("figure exposes accessible name (or empty-state message)", async ({ page }) => {
    const figure = page.locator(`${SECTION} figure.chart-figure`);
    if ((await figure.count()) === 0) {
      // No cost data yet — empty-state path. Acceptance: copy is shown.
      await expect(page.locator(`${SECTION}`)).toContainText(/Cost data not yet available/i);
      return;
    }
    await expect(figure).toBeVisible();
    const chartImg = figure.locator('[role="img"]');
    await expect(chartImg).toHaveAttribute("aria-labelledby", /chart-/);
    await expect(chartImg).toHaveAccessibleName(/Cost vs SPS Pareto frontier/i);
  });

  test("tooltip surfaces on scatter-point hover", async ({ page }) => {
    const chart = page.locator(`${SECTION} .echarts-container`).first();
    if ((await chart.count()) === 0) {
      test.skip(true, "No cost data — chart not rendered, hover N/A.");
      return;
    }
    await chart.locator("svg, canvas").first().waitFor({ timeout: 10000 });

    const box = await chart.boundingBox();
    if (!box) throw new Error("chart container has no bounding box");

    // Echarts paints points at data-driven coordinates; sweep a small grid
    // until a tooltip appears so the test stays robust to data shifts.
    let tooltipText = "";
    outer: for (let row = 1; row <= 6; row++) {
      for (let col = 1; col <= 6; col++) {
        const x = box.x + (box.width * col) / 7;
        const y = box.y + (box.height * row) / 7;
        await page.mouse.move(x, y, { steps: 4 });
        await page.waitForTimeout(120);
        const tip = page
          .locator("div")
          .filter({ hasText: /SPS:\s*\d/ })
          .first();
        if ((await tip.count()) && (await tip.isVisible())) {
          tooltipText = (await tip.innerText()).trim();
          if (tooltipText.includes("SPS:")) break outer;
        }
      }
    }
    expect(tooltipText, "expected echarts tooltip with SPS row").toMatch(/SPS:\s*\d/);
    expect(tooltipText).toMatch(/Cost:|\$/);
  });

  test("data table <details> is keyboard-expandable and lists rows", async ({ page }) => {
    const details = page.locator(`${SECTION} details.chart-data-table`);
    if ((await details.count()) === 0) {
      test.skip(true, "No cost data — data table not rendered.");
      return;
    }
    await expect(details).toBeVisible();
    await expect(details).not.toHaveAttribute("open", /.*/);

    await details.locator("summary").click();
    await expect(details).toHaveAttribute("open", "");

    const headers = details.locator("thead th");
    await expect(headers).toHaveCount(4);
    await expect(headers.nth(0)).toHaveText(/Configuration/i);
    await expect(headers.nth(2)).toHaveText(/SPS/i);

    const rowCount = await details.locator("tbody tr").count();
    expect(rowCount).toBeGreaterThan(0);
  });
});
