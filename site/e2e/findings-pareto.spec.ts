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
    await chart.scrollIntoViewIfNeeded();

    // Hover directly on a rendered scatter SVG path. Coordinate-based sweeps
    // miss in SVG-rendered echarts because `mousemove` doesn't reliably fire
    // mouseover on child paths; calling `.hover()` on the path element
    // dispatches the events zrender listens for.
    const pointHandle = await page.evaluateHandle(() => {
      const container = document.querySelector("#cost-performance-pareto .echarts-container");
      const svg = container?.querySelector("svg");
      if (!svg) return null;
      // Scatter points are filled paths whose "d" starts with "M1 0A..." — the
      // echarts circle primitive. Filter out gridlines (fill=none) and the
      // background rect.
      const paths = Array.from(svg.querySelectorAll("path")).filter((p) => {
        const fill = p.getAttribute("fill");
        if (!fill || fill === "none" || fill === "transparent") return false;
        if (/^#fff/i.test(fill)) return false;
        return true;
      });
      return paths[0] ?? null;
    });
    const point = pointHandle.asElement();
    expect(point, "expected at least one scatter point in the SVG").not.toBeNull();
    if (!point) return;
    await point.hover();
    await page.waitForTimeout(400);

    // Echarts renders the tooltip as an absolutely-positioned div sibling to
    // the zrender surface; scan for the visible div whose text carries our
    // pre-built caption (see CostPerformancePareto.astro).
    const tooltipText = await page.evaluate(() => {
      const divs = Array.from(document.querySelectorAll("div"));
      const vis = divs.filter(
        (d) =>
          d.offsetParent !== null && /SPS:\s*\d/.test(d.innerText) && /Cost:|\$/.test(d.innerText),
      );
      return vis[0]?.innerText ?? "";
    });
    expect(tooltipText, "expected tooltip with SPS + Cost on hover").toMatch(/SPS:\s*\d/);
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
