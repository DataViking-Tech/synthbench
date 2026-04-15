import { defineConfig, devices } from "@playwright/test";

// sb-ave — functional test for /run/<id> Aggregate Scores label contrast in
// dark mode. Follows the dedicated-config pattern (one config per spec, not
// part of the smoke VRT suite).
export default defineConfig({
  testDir: ".",
  testMatch: "run-aggregate-scores-contrast.spec.ts",
  outputDir: "./test-results-run-aggregate-scores-contrast",
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
      // Default to dark; each test calls page.emulateMedia() to set its own
      // color-scheme so dark-only and light-only assertions live in one project.
      use: { ...devices["Desktop Chrome"], colorScheme: "dark" },
    },
  ],
  webServer: {
    command: "npm run preview",
    port: 4321,
    reuseExistingServer: !process.env.CI,
    cwd: "..",
  },
});
