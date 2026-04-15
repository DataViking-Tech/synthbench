import { expect, test } from "@playwright/test";

// cost-metrics Slice 4 (sb-xij) — functional tests for the leaderboard
// $/100Q column. Covers the acceptance criteria from the bead:
//   * column header visible on desktop
//   * sort asc/desc with — rows always last (regardless of direction)
//   * mobile viewport renders the cost cell in each card
//
// The published leaderboard.json today has null cost_per_100q for every row
// (no Slice-2 token-bearing runs landed yet). To exercise sort we patch a
// handful of rows in-DOM with synthetic values before clicking — the sort
// comparator reads from `data-entry` so this stays faithful to production.

type SortKey = "cost_per_100q";

async function seedCosts(
  page: import("@playwright/test").Page,
  values: (number | null)[],
): Promise<void> {
  await page.evaluate((costs) => {
    const rows = Array.from(
      document.querySelectorAll<HTMLTableRowElement>("#leaderboard-table tbody tr.leaderboard-row"),
    );
    const fmt = (v: number | null | undefined): string => {
      if (v == null || Number.isNaN(v)) return "—";
      if (v === 0) return "$0.00";
      if (v > 0 && v < 0.01) return "<$0.01";
      return `$${v.toFixed(2)}`;
    };
    for (let i = 0; i < rows.length; i++) {
      const row = rows[i];
      const raw = row.dataset.entry ?? "{}";
      const data = JSON.parse(raw);
      const v = i < costs.length ? costs[i] : null;
      data.cost_per_100q = v;
      row.dataset.entry = JSON.stringify(data);
      const cell = row.querySelector<HTMLElement>(".cost-cell");
      if (cell) {
        cell.dataset.costPer100q = v == null ? "" : String(v);
        cell.textContent = fmt(v);
      }
    }
  }, values);
}

async function firstVisibleCostCells(
  page: import("@playwright/test").Page,
  count: number,
): Promise<string[]> {
  const cells = page.locator("#leaderboard-table tbody tr.leaderboard-row .cost-cell");
  const texts: string[] = [];
  for (let i = 0; i < count; i++) {
    texts.push(((await cells.nth(i).innerText()) || "").trim());
  }
  return texts;
}

async function lastCostCell(page: import("@playwright/test").Page): Promise<string> {
  const cells = page.locator("#leaderboard-table tbody tr.leaderboard-row .cost-cell");
  const n = await cells.count();
  return ((await cells.nth(n - 1).innerText()) || "").trim();
}

async function clickSort(page: import("@playwright/test").Page, key: SortKey): Promise<void> {
  await page.locator(`#leaderboard-table thead button[data-sort="${key}"]`).click();
}

test.describe("leaderboard $/100Q column", () => {
  test("desktop column header renders", async ({ page }) => {
    await page.goto("leaderboard/");
    const header = page.locator('#leaderboard-table thead button[data-sort="cost_per_100q"]');
    await expect(header).toBeVisible();
    await expect(header).toContainText("$/100Q");

    const th = page.locator('#leaderboard-table thead th:has(button[data-sort="cost_per_100q"])');
    await expect(th).toHaveAttribute("aria-sort", "none");
  });

  test("desktop each row has a cost-cell (— by default)", async ({ page }) => {
    await page.goto("leaderboard/");
    const rows = page.locator("#leaderboard-table tbody tr.leaderboard-row");
    const cells = page.locator("#leaderboard-table tbody tr.leaderboard-row .cost-cell");
    expect(await cells.count()).toBe(await rows.count());
  });

  test("sort desc then asc; — rows always last", async ({ page }) => {
    await page.goto("leaderboard/");
    // Seed three priced rows and many nulls.
    await seedCosts(page, [0.05, 0.01, 0.25]);

    // First click: numeric columns default to descending. Highest priced
    // first, — always sinks to the bottom (null-last is direction-agnostic
    // so users never chase missing data).
    await clickSort(page, "cost_per_100q");
    const descTop = await firstVisibleCostCells(page, 3);
    expect(descTop).toEqual(["$0.25", "$0.05", "$0.01"]);
    expect(await lastCostCell(page)).toBe("—");

    // Second click on the same key flips direction to ascending. — still last.
    await clickSort(page, "cost_per_100q");
    const ascTop = await firstVisibleCostCells(page, 3);
    expect(ascTop).toEqual(["$0.01", "$0.05", "$0.25"]);
    expect(await lastCostCell(page)).toBe("—");
  });

  test("mobile viewport surfaces $/100Q label in every card", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("leaderboard/");
    const mobileList = page.locator("ul.md\\:hidden");
    await expect(mobileList).toBeVisible();
    // Each card has a $/100Q label + a cost cell. Use the cell class we added.
    const firstCard = mobileList.locator("li").first();
    await expect(firstCard).toContainText("$/100Q");
    await expect(firstCard.locator(".cost-cell")).toHaveCount(1);
  });
});
