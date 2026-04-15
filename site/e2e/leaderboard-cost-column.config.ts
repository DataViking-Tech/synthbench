import { defineConfig, devices } from "@playwright/test";

// cost-metrics Slice 4 (sb-xij) — functional test for the $/100Q column.
// Follows the mobile-audit.config.ts pattern: dedicated config, dedicated
// testMatch, single project. Not part of the smoke VRT suite.
export default defineConfig({
  testDir: ".",
  testMatch: "leaderboard-cost-column.spec.ts",
  outputDir: "./test-results-cost-column",
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
