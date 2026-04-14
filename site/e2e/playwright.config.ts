import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./visual",
  outputDir: "./test-results",
  // Smoke VRT (sb-o3b) is intentionally single-platform: baselines are
  // generated in Ubuntu CI (Playwright official Linux runner) and committed
  // from CI, not from macOS dev machines. Dropping {platform} from the
  // template keeps a single baseline set under linux/.
  snapshotPathTemplate: "{testDir}/__screenshots__/{testFilePath}/{projectName}/{arg}{ext}",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "html",
  use: {
    baseURL: "http://localhost:4321/synthbench/",
    screenshot: "only-on-failure",
  },
  expect: {
    toHaveScreenshot: {
      animations: "disabled",
      maxDiffPixelRatio: 0.01,
    },
  },
  projects: [
    {
      name: "desktop-chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "npm run preview",
    port: 4321,
    reuseExistingServer: !process.env.CI,
    cwd: "..",
  },
});
