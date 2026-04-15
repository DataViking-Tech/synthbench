import { defineConfig, devices } from "@playwright/test";

// sb-1h2 — functional test for the /run/<id> per-question text fix. Follows
// the dedicated-config pattern established by leaderboard-cost-column and
// explore-exploratory-toggle. Not part of the smoke VRT suite.
export default defineConfig({
  testDir: ".",
  testMatch: "run-question-text.spec.ts",
  outputDir: "./test-results-run-question-text",
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
