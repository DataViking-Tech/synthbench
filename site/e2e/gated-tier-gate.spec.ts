import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test } from "@playwright/test";

// sb-sj6 — verifies that gated-tier per-question pages render either real
// data (when the static build had local payload) or a sign-in gate (when the
// payload lives behind the Worker proxy). The test uses the
// ``gated-routes.json`` manifest to find a real (dataset, key) pair so the
// shell route exists in the build under test.

const gatedRoutesPath = resolve(__dirname, "../public/data/gated-routes.json");

interface GatedRoutesManifest {
  datasets: Record<string, string[]>;
}

function pickGatedSample(): { dataset: string; key: string } | null {
  if (!existsSync(gatedRoutesPath)) return null;
  const manifest = JSON.parse(readFileSync(gatedRoutesPath, "utf-8")) as GatedRoutesManifest;
  for (const [dataset, keys] of Object.entries(manifest.datasets ?? {})) {
    if (keys.length > 0) {
      return { dataset, key: keys[0] };
    }
  }
  return null;
}

test.describe("sb-sj6: gated-tier sign-in gate", () => {
  test("shell page exists and surfaces sign-in CTA when fetch fails", async ({ page }) => {
    const sample = pickGatedSample();
    if (sample == null) {
      test.skip();
      return;
    }

    // Force every gated fetch (api.synthbench.org/data/...) to a 401 so the
    // page swaps to the sign-in gate without needing a real Worker.
    await page.route(/.*\/data\/question\/.*\.json$/, (route) =>
      route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ error: "unauthenticated" }),
      }),
    );

    await page.goto(
      `question/${encodeURIComponent(sample.dataset)}/${encodeURIComponent(sample.key)}/`,
    );

    // Either the static page already has the data inlined (older builds with
    // the payload local) — in which case the gate UI never appears — or the
    // hydration script swapped in the sign-in gate.
    const gate = page.getByRole("link", { name: /Sign in/i });
    await expect(gate.first()).toBeVisible({ timeout: 5000 });
  });

  test("methodology page documents all four tiers", async ({ page }) => {
    await page.goto("methodology/");
    const policyTable = page.locator("#dataset-policies");
    await expect(policyTable).toBeVisible();
    // Tier rationale paragraphs should call out each tier name.
    await expect(policyTable).toContainText("full");
    await expect(policyTable).toContainText("gated");
    await expect(policyTable).toContainText("aggregates_only");
    await expect(policyTable).toContainText("citation_only");
  });
});
