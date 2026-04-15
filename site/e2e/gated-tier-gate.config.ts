import { defineConfig, devices } from "@playwright/test";

// sb-sj6 — verifies the user-visible gate UI on gated-tier pages
// (subpop / wvs / etc.). Anonymous users hitting a per-question / run /
// config page for a gated dataset must see a "Sign in" CTA, not the raw
// per-question distribution. The full OAuth round-trip is covered by the
// sb-8o4 auth-ui spec; this spec focuses on the gate side of the wall.
export default defineConfig({
  testDir: ".",
  testMatch: "gated-tier-gate.spec.ts",
  outputDir: "./test-results-gated-tier-gate",
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
