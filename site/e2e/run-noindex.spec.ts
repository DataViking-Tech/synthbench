import { expect, test } from "@playwright/test";

// sb-44f — defense-in-depth crawl hygiene:
//   * robots.txt is served at /synthbench/robots.txt with Disallow rules for
//     the per-detail JSON paths under /data/.
//   * Detail pages (/run/<id>, /question/<dataset>/<key>, /config/<id>) carry
//     <meta name="robots" content="noindex">.
//   * Top-level indexable pages (home, leaderboard) do NOT carry noindex.

const SAMPLE_RUN_ID = "opinionsqa_ensemble_3blend_20260412_020745";

test.describe("sb-44f: noindex on detail pages + robots.txt", () => {
  test("robots.txt is served with expected Disallow rules", async ({ request }) => {
    const res = await request.get("robots.txt");
    expect(res.status()).toBe(200);
    const body = await res.text();
    expect(body).toMatch(/^User-agent:\s*\*/m);
    expect(body).toMatch(/^Disallow:\s*\/data\/run\//m);
    expect(body).toMatch(/^Disallow:\s*\/data\/question\//m);
    expect(body).toMatch(/^Disallow:\s*\/data\/config\//m);
    expect(body).toMatch(/^Disallow:\s*\/data\/runs-index\.json/m);
  });

  test("/run/<id> carries noindex meta", async ({ page }) => {
    await page.goto(`run/${SAMPLE_RUN_ID}/`);
    await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", "noindex");
  });

  test("top-level leaderboard does NOT carry noindex", async ({ page }) => {
    await page.goto("leaderboard/");
    // Either no robots meta at all, or a robots meta that does not contain noindex.
    const count = await page.locator('meta[name="robots"]').count();
    if (count > 0) {
      const content = (await page.locator('meta[name="robots"]').getAttribute("content")) ?? "";
      expect(content.toLowerCase()).not.toContain("noindex");
    }
  });
});
