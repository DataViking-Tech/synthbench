import { defineConfig, devices } from "@playwright/test";

// sb-djv — functional test for the explore page exploratory-runs toggle +
// s/n chips. Follows the dedicated-config pattern established by
// leaderboard-cost-column.config.ts. Not part of the smoke VRT suite.
export default defineConfig({
  testDir: ".",
  testMatch: "explore-exploratory-toggle.spec.ts",
  outputDir: "./test-results-explore-toggle",
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
