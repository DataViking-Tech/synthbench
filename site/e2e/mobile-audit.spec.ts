import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Mobile responsive audit — Pass 1.3 (sb-ye3)
// Checks all 9 routes at 375/390/414px for horizontal overflow and layout breaks.

const VIEWPORTS = [
  { label: "375-iphone-se", width: 375, height: 667 },
  { label: "390-iphone-14", width: 390, height: 844 },
  { label: "414-iphone-plus", width: 414, height: 896 },
];

// Sample IDs from public/data/runs-index.json
const SAMPLE_CONFIG_ID = "ensemble--3-model-blend--tdefault--tplcurrent--3ba7cfb3";
const SAMPLE_RUN_ID = "globalopinionqa_ensemble_3blend_20260412_021343";

const ROUTES = [
  { path: "", label: "home" },
  { path: "leaderboard/", label: "leaderboard" },
  { path: "explore/", label: "explore" },
  { path: "findings/", label: "findings" },
  { path: "methodology/", label: "methodology" },
  { path: "submit/", label: "submit" },
  { path: "compare/", label: "compare" },
  { path: `config/${SAMPLE_CONFIG_ID}/`, label: "config-detail" },
  { path: `run/${SAMPLE_RUN_ID}/`, label: "run-detail" },
];

const OUT_DIR = path.join(__dirname, "mobile-audit-out");
fs.mkdirSync(OUT_DIR, { recursive: true });

const findings: Array<{
  route: string;
  viewport: string;
  issues: string[];
}> = [];

test.afterAll(async () => {
  fs.writeFileSync(path.join(OUT_DIR, "findings.json"), JSON.stringify(findings, null, 2));
});

for (const vp of VIEWPORTS) {
  for (const route of ROUTES) {
    test(`${route.label} @ ${vp.label}`, async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      const url = `http://localhost:4321/synthbench/${route.path}`;
      await page.goto(url, { waitUntil: "networkidle" });
      await page.waitForTimeout(400);

      const issues: string[] = [];

      // Horizontal overflow detection
      const scrollX = await page.evaluate(() => ({
        documentWidth: document.documentElement.scrollWidth,
        innerWidth: window.innerWidth,
        bodyWidth: document.body.scrollWidth,
      }));
      if (scrollX.documentWidth > scrollX.innerWidth + 1) {
        issues.push(
          `horizontal overflow: doc ${scrollX.documentWidth}px > viewport ${scrollX.innerWidth}px`,
        );
      }

      // Find elements wider than viewport (common overflow cause)
      const wideEls = await page.evaluate((vw) => {
        const out: Array<{ tag: string; cls: string; w: number; id: string }> = [];
        const all = document.querySelectorAll("*");
        for (const el of all) {
          const r = el.getBoundingClientRect();
          if (r.width > vw + 2 && r.width < 10000) {
            out.push({
              tag: el.tagName.toLowerCase(),
              cls: (el.getAttribute("class") || "").slice(0, 80),
              w: Math.round(r.width),
              id: el.id || "",
            });
          }
        }
        return out.slice(0, 8);
      }, vp.width);
      if (wideEls.length > 0) {
        issues.push(`wide elements: ${JSON.stringify(wideEls)}`);
      }

      // Small tap targets (interactive elements < 44px)
      const smallTargets = await page.evaluate(() => {
        const out: Array<{ tag: string; text: string; w: number; h: number }> = [];
        const sel = "a, button, input, select, textarea, [role=button]";
        for (const el of document.querySelectorAll(sel)) {
          const r = (el as HTMLElement).getBoundingClientRect();
          if (r.width === 0 || r.height === 0) continue;
          if (r.width < 40 || r.height < 40) {
            out.push({
              tag: el.tagName.toLowerCase(),
              text: (el.textContent || "").trim().slice(0, 30),
              w: Math.round(r.width),
              h: Math.round(r.height),
            });
          }
        }
        return out.slice(0, 10);
      });
      if (smallTargets.length > 0) {
        issues.push(`small tap targets (<40px): ${JSON.stringify(smallTargets)}`);
      }

      // Screenshot
      const shotPath = path.join(OUT_DIR, `${route.label}-${vp.label}.png`);
      await page.screenshot({ path: shotPath, fullPage: true });

      findings.push({
        route: route.label,
        viewport: vp.label,
        issues,
      });

      // Hard-fail only on horizontal overflow; tap targets reported but non-fatal
      expect(
        scrollX.documentWidth,
        `${route.label} at ${vp.label} has horizontal overflow`,
      ).toBeLessThanOrEqual(scrollX.innerWidth + 1);
    });
  }
}
