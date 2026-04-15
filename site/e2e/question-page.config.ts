import { defineConfig, devices } from "@playwright/test";

// sb-eiv — functional test for the new /question/[dataset]/[key] page and
// the cross-link added to /run/[id] per-question detail rows. Follows the
// dedicated-config pattern (explore-exploratory-toggle, leaderboard-cost-
// column). Not part of the smoke VRT suite.
export default defineConfig({
  testDir: ".",
  testMatch: "question-page.spec.ts",
  outputDir: "./test-results-question-page",
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://localhost:4321/synthbench/",
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
