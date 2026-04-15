import { defineConfig, devices } from "@playwright/test";

// sb-8o4 — functional test for the auth UI (sign-in buttons, callback page,
// account page, setup page). Follows the dedicated-config pattern used by the
// other non-VRT specs. Does not exercise a real OAuth round-trip — that would
// require a live Supabase project plus a GitHub/Google test identity; instead
// we verify the unauthenticated UI and static structure of the auth routes.
export default defineConfig({
  testDir: ".",
  testMatch: "auth-ui.spec.ts",
  outputDir: "./test-results-auth-ui",
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
