import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "astro/config";

// Defaults preserve GH Pages behavior so existing builds keep working.
// CF Pages overrides via build env: SITE_URL=https://synthbench.org BASE_PATH=/
const site = process.env.SITE_URL || "https://dataviking-tech.github.io";
const base = process.env.BASE_PATH || "/synthbench";

export default defineConfig({
  site,
  base,
  vite: {
    plugins: [tailwindcss()],
  },
});
