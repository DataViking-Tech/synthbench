import { expect, test } from "@playwright/test";

// sb-8o4 — verifies the static structure of the auth surface. A real OAuth
// round-trip needs a live Supabase project + GitHub/Google test identity; we
// instead cover:
//   * nav exposes a visible sign-in entry point
//   * /account renders both GitHub AND Google sign-in buttons when signed-out
//     (founder added Google alongside GitHub — both are first-class)
//   * /account/setup renders the profile capture form
//   * /auth/callback page exists and carries noindex
//   * unauthenticated users do NOT see the signed-in Account dashboard

test.describe("sb-8o4: auth UI (unauthenticated)", () => {
  test("nav shows a sign-in entry point linking to /account/", async ({ page }) => {
    await page.goto("");
    // Initial markup renders the signed-out state of the AuthButton widget.
    const signIn = page.locator('[data-auth-button] [data-auth-state="signed-out"]');
    await expect(signIn).toBeVisible();
    await expect(signIn).toHaveAttribute("href", /\/account\/$/);
  });

  test("/account renders both GitHub and Google sign-in buttons", async ({ page }) => {
    await page.goto("account/");
    await expect(page.getByRole("heading", { name: "Account" })).toBeVisible();

    const github = page.locator('[data-account-signin="github"]');
    const google = page.locator('[data-account-signin="google"]');
    await expect(github).toBeVisible();
    await expect(google).toBeVisible();
    await expect(github).toContainText(/Sign in with GitHub/i);
    await expect(google).toContainText(/Sign in with Google/i);

    // Signed-in dashboard must remain hidden until a session is established.
    const signedIn = page.locator('[data-account-state="signed-in"]');
    await expect(signedIn).toBeHidden();
  });

  test("/account carries noindex meta", async ({ page }) => {
    await page.goto("account/");
    await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", "noindex");
  });

  test("/account/setup shows the profile capture form fields", async ({ page }) => {
    await page.goto("account/setup/");
    // Hydration may redirect unauthenticated users, but the rendered HTML
    // always includes the form inputs.
    const form = page.locator("[data-profile-form]");
    await expect(form).toBeAttached();
    await expect(page.locator("#affiliation")).toBeAttached();
    await expect(page.locator("#research_purpose")).toBeAttached();
    await expect(form.locator("[data-profile-submit]")).toContainText(/Save profile/i);
  });

  test("/auth/callback page is reachable and noindex", async ({ page }) => {
    // Silence the console error `requireAuth`/callback scripts emit when no
    // Supabase config is baked in — it's expected in a preview build without
    // PUBLIC_SUPABASE_URL set.
    page.on("pageerror", () => {});
    await page.goto("auth/callback/");
    await expect(page.getByRole("heading", { name: /Signing you in/i })).toBeVisible();
    await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", "noindex");
  });
});
