import { expect, test } from "@playwright/test";

// sb-eiv — /question/[dataset]/[key] page + /run drill-down.
// Acceptance checks:
//   * Page renders with question text, options, and human baseline bar
//   * Trendslop indicators (cross-model JSD, consensus, refusal spread) visible
//   * At least one model row linking back to /run/[id]
//   * /run/[id] per-question detail exposes "Compare across models" link to
//     the corresponding question page
//
// Fixture key is stable across publishes: GOQA_0_adeba4f8 is derived from
// question text content and survives leaderboard-results regeneration.
const FIXTURE_DATASET = "globalopinionqa";
const FIXTURE_KEY = "GOQA_0_adeba4f8";
const FIXTURE_RUN_ID = "globalopinionqa_openrouter_anthropic_claude-haiku-4-5_20260411_234610";

test.describe("question: cross-model explorer page", () => {
  test("renders question context + trendslop indicators", async ({ page }) => {
    await page.goto(`question/${FIXTURE_DATASET}/${FIXTURE_KEY}/`);

    await expect(page.locator("h1")).toHaveText("Question detail");

    // The dataset badge and key are present (breadcrumb + header).
    await expect(page.getByText(FIXTURE_DATASET, { exact: true }).first()).toBeVisible();
    await expect(page.getByText(FIXTURE_KEY, { exact: true }).first()).toBeVisible();

    // Trendslop indicators section surfaces the cross-model divergence row.
    const indicators = page.locator("section[aria-labelledby='trendslop-heading']");
    await expect(indicators).toBeVisible();
    await expect(indicators).toContainText("Cross-model JSD (mean)");
    await expect(indicators).toContainText("Cross-model JSD (max)");
    await expect(indicators).toContainText("Refusal-rate spread");

    // Human baseline bar is rendered (role=img with Distribution aria-label).
    const humanBar = page.getByRole("img", { name: /^Distribution: / }).first();
    await expect(humanBar).toBeVisible();

    // At least one model row in the table.
    const rows = page.locator("#per-model-table tbody tr");
    expect(await rows.count()).toBeGreaterThan(0);
  });

  test("model row links to its /run page", async ({ page }) => {
    await page.goto(`question/${FIXTURE_DATASET}/${FIXTURE_KEY}/`);

    const viewLinks = page.locator("#per-model-table tbody a[aria-label^='View full run']");
    const firstLink = viewLinks.first();
    await expect(firstLink).toBeVisible();
    const href = await firstLink.getAttribute("href");
    expect(href).toBeTruthy();
    expect(href).toMatch(/\/run\//);

    await firstLink.click();
    await expect(page).toHaveURL(/\/run\//);
    // Arrived on the run detail page — header should have the run id in monospace.
    await expect(page.locator(".run-detail")).toBeVisible();
  });
});

test.describe("question page: full text is not truncated (sb-x2k)", () => {
  // GOQA_32_76dc5592 is the GlobalOpinionQA row whose full text is 205 chars
  // after registry rehydration — historical data-side truncation would show
  // this as a 120-char clip. Stable across publishes because the key is
  // derived from a content hash.
  const LONG_DATASET = "globalopinionqa";
  const LONG_KEY = "GOQA_32_76dc5592";

  test("long question renders its full text in the header paragraph", async ({ page }) => {
    await page.goto(`question/${LONG_DATASET}/${LONG_KEY}/`);

    // The header renders the question as the first non-monospace paragraph
    // inside <header>. Grab it by its text-base + leading-relaxed signature
    // so we don't depend on element ordering.
    const questionP = page
      .locator("header p.text-base.leading-relaxed, header p.max-w-3xl")
      .first();
    await expect(questionP).toBeVisible();

    const rendered = (await questionP.textContent()) ?? "";
    expect(rendered).not.toContain("…");
    expect(
      rendered.length,
      "expected question to render >120 chars (guards against historical truncation)",
    ).toBeGreaterThan(120);
  });

  test("/run page rendered from /question link also carries full text", async ({ page }) => {
    // Catches the other half of the bug — if publish_runs emitted rehydrated
    // text but publish_questions forgot to, the two pages would disagree on
    // how long the same prompt is. We cross-check by navigating through the
    // "View full run" link and asserting at least one >120-char row renders
    // on the destination.
    await page.goto(`question/${LONG_DATASET}/${LONG_KEY}/`);
    const viewLink = page.locator("#per-model-table tbody a[aria-label^='View full run']").first();
    const runHref = await viewLink.getAttribute("href");
    expect(runHref).toBeTruthy();
    await page.goto(runHref as string);

    await page.locator("#per-question-tbody tr.pq-row").first().waitFor({ timeout: 10000 });
    const maxLen = await page.evaluate(() => {
      const cells = Array.from(
        document.querySelectorAll<HTMLElement>("#per-question-tbody tr.pq-row .pq-text"),
      );
      let m = 0;
      for (const c of cells) {
        const n = (c.textContent ?? "").length;
        if (n > m) m = n;
      }
      return m;
    });
    expect(
      maxLen,
      "expected destination /run page to also carry at least one >120-char question row",
    ).toBeGreaterThan(120);
  });
});

test.describe("run drill-down → question page", () => {
  test("per-question detail row exposes Compare-across-models link", async ({ page }) => {
    await page.goto(`run/${FIXTURE_RUN_ID}/`);

    // Wait for per-question rows to render (client-side fetch).
    const firstRow = page.locator("#per-question-tbody tr.pq-row").first();
    await expect(firstRow).toBeVisible({ timeout: 10000 });

    // Expand the first row's detail so the Compare link becomes visible.
    const firstExpand = page.locator("#per-question-tbody button.pq-expand").first();
    await firstExpand.click();

    const compareLink = page.locator("a.pq-compare").first();
    await expect(compareLink).toBeVisible();
    const href = await compareLink.getAttribute("href");
    expect(href).toBeTruthy();
    expect(href).toMatch(/\/question\/globalopinionqa\//);

    await compareLink.click();
    await expect(page).toHaveURL(/\/question\/globalopinionqa\//);
    await expect(page.locator("h1")).toHaveText("Question detail");
  });
});
