import { expect, test } from "@playwright/test";

// Slice 6 (sb-lxt): methodology Cost computation section
// Contract: /methodology renders a "Cost computation" <h2>, the
// #cost-computation anchor scrolls into view, and the section preserves
// the page's h2 (section) → h3 (card) heading hierarchy.

test.describe("methodology: cost computation section", () => {
  test("renders h2 'Cost computation' with #cost-computation anchor", async ({ page }) => {
    await page.goto("methodology/");

    const section = page.locator("section#cost-computation");
    await expect(section).toBeVisible();

    const heading = section.getByRole("heading", {
      level: 2,
      name: "Cost computation",
    });
    await expect(heading).toBeVisible();
  });

  test("navigating to #cost-computation scrolls the section into view", async ({ page }) => {
    await page.goto("methodology/#cost-computation");

    const section = page.locator("section#cost-computation");
    await expect(section).toBeInViewport();
  });

  test("renders 6 cards, each with an h3 title and stable id", async ({ page }) => {
    await page.goto("methodology/");

    const expectedCardIds = [
      "what-we-measure",
      "what-we-derive",
      "pricing-snapshot",
      "self-hosted-policy",
      "ensemble-cost",
      "pre-tracking-rows",
    ];

    for (const id of expectedCardIds) {
      const card = page.locator(`section#cost-computation div#${id}`);
      await expect(card).toBeVisible();

      const h3 = card.locator("h3");
      await expect(h3).toBeVisible();
      await expect(h3).not.toBeEmpty();
    }
  });

  test("preserves h2 (section) → h3 (card) heading hierarchy", async ({ page }) => {
    await page.goto("methodology/");

    const section = page.locator("section#cost-computation");

    // The section headline must be exactly one h2.
    await expect(section.locator("h2")).toHaveCount(1);

    // Every card heading inside the section must be an h3 — no h4+ skips
    // and no h1/h2 mid-section. Count matches the 6 card subsections.
    await expect(section.locator("h3")).toHaveCount(6);
    await expect(section.locator("h1")).toHaveCount(0);
    await expect(section.locator("h4, h5, h6")).toHaveCount(0);
  });
});
