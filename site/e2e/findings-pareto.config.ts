import { defineConfig, devices } from "@playwright/test";

// Functional spec for the cost-vs-SPS Pareto chart on /findings (sb-91t).
// Separate config (per mobile-audit precedent) so the visual VRT config
// stays scoped to ./visual/ snapshot tests.
export default defineConfig({
  testDir: ".",
  testMatch: "findings-pareto.spec.ts",
  outputDir: "./test-results-findings-pareto",
  fullyParallel: false,
  retries: process.env.CI ? 2 : 0,
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
