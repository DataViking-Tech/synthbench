import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "astro/config";

export default defineConfig({
  site: "https://dataviking-tech.github.io",
  base: "/synthbench",
  vite: {
    plugins: [tailwindcss()],
  },
});
