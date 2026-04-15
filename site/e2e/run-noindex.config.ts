import { defineConfig, devices } from "@playwright/test";

// sb-44f — functional test for noindex meta on detail pages and for the
// deployed robots.txt. Follows the dedicated-config pattern established by
// run-question-text. Not part of the smoke VRT suite.
export default defineConfig({
  testDir: ".",
  testMatch: "run-noindex.spec.ts",
  outputDir: "./test-results-run-noindex",
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
