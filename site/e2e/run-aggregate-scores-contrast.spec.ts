import { expect, test } from "@playwright/test";

// sb-ave — Aggregate Scores metric labels (SPS, p_dist, JSD, …) on /run/<id>
// must clear WCAG AA (4.5:1) contrast against their tile background in BOTH
// light and dark themes. The original bug shipped a translucent-white tile
// background that picked up the dark page in dark mode and collided with the
// lifted `--color-muted-dark` label color, producing illegible grey-on-grey.

const SAMPLE_RUN_ID = "opinionsqa_ensemble_3blend_20260412_020745";
const ROUTE = `run/${SAMPLE_RUN_ID}/`;

// Resolve any CSS color (rgb, rgba, oklch, color-mix, …) into sRGB by asking
// the browser to paint a 1×1 canvas and reading back the rendered pixel. This
// handles `oklch()` and `color-mix(... transparent)` uniformly without us
// having to reimplement the CSS Color 4 conversion stack in JS.
async function measureContrast(page: import("@playwright/test").Page): Promise<number> {
  const firstTile = page.locator("#run-scores .score-tile").first();
  await expect(firstTile).toBeVisible({ timeout: 10000 });

  return await page.evaluate(() => {
    const tile = document.querySelector<HTMLElement>("#run-scores .score-tile");
    const label = tile?.querySelector<HTMLElement>(".score-label");
    const body = document.body;
    if (!tile || !label) throw new Error("score-tile or score-label missing");

    // Paint a single CSS color onto a 1×1 canvas atop an explicit underlay
    // and read the resulting [r,g,b,a] pixel. `paint(color)` returns the
    // color composited over solid white (no underlay); `paint(color, under)`
    // composites over `under` (which itself may be translucent — caller is
    // responsible for layering).
    const paint = (
      color: string,
      under?: [number, number, number],
    ): [number, number, number, number] => {
      const cv = document.createElement("canvas");
      cv.width = cv.height = 1;
      const ctx = cv.getContext("2d");
      if (!ctx) throw new Error("no 2d context");
      // Start with a transparent canvas so we can sample the raw color (with
      // alpha) when no underlay is provided.
      if (under) {
        ctx.fillStyle = `rgb(${under[0]}, ${under[1]}, ${under[2]})`;
        ctx.fillRect(0, 0, 1, 1);
      } else {
        ctx.clearRect(0, 0, 1, 1);
      }
      ctx.fillStyle = color;
      ctx.fillRect(0, 0, 1, 1);
      const [r, g, b, a] = ctx.getImageData(0, 0, 1, 1).data;
      return [r, g, b, a / 255];
    };

    const lumin = (r: number, g: number, b: number): number => {
      const conv = (c: number) => {
        const s = c / 255;
        return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
      };
      return 0.2126 * conv(r) + 0.7152 * conv(g) + 0.0722 * conv(b);
    };

    // Body background is opaque (Tailwind `bg-surface` / `dark:bg-surface-dark`);
    // paint with no underlay would composite over transparent and lose nothing.
    // We still resolve via canvas to handle the oklch() token.
    const bodyRgba = paint(getComputedStyle(body).backgroundColor);
    const bodyOpaque: [number, number, number] = [bodyRgba[0], bodyRgba[1], bodyRgba[2]];

    // Tile fill is `color-mix(... transparent)` → translucent. Layer it onto
    // the body background to recover the visible color the user sees.
    const tileOnBody = paint(getComputedStyle(tile).backgroundColor, bodyOpaque);
    const tileOpaque: [number, number, number] = [tileOnBody[0], tileOnBody[1], tileOnBody[2]];

    // Label color is opaque oklch but we still resolve via canvas atop the
    // tile so any future translucency is handled correctly.
    const labelOnTile = paint(getComputedStyle(label).color, tileOpaque);

    const lf = lumin(labelOnTile[0], labelOnTile[1], labelOnTile[2]);
    const lb = lumin(tileOpaque[0], tileOpaque[1], tileOpaque[2]);
    const [hi, lo] = lf >= lb ? [lf, lb] : [lb, lf];
    return (hi + 0.05) / (lo + 0.05);
  });
}

test.describe("run detail: Aggregate Scores label contrast (sb-ave)", () => {
  test("dark theme — score-label clears WCAG AA on tile background", async ({ page }) => {
    await page.emulateMedia({ colorScheme: "dark" });
    await page.goto(ROUTE);
    const ratio = await measureContrast(page);
    // WCAG AA: 4.5:1 for normal body text.
    expect(ratio).toBeGreaterThanOrEqual(4.5);
  });

  test("light theme — score-label clears WCAG AA on tile background", async ({ page }) => {
    await page.emulateMedia({ colorScheme: "light" });
    await page.goto(ROUTE);
    const ratio = await measureContrast(page);
    expect(ratio).toBeGreaterThanOrEqual(4.5);
  });
});
