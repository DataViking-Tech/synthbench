import { defineConfig } from "astro/config";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  site: "https://dataviking-tech.github.io",
  base: "/synthbench/next",
  vite: {
    plugins: [tailwindcss()],
  },
});
